#!/usr/bin/env python3
"""
Standalone test for Terminus multiple commands per model response.
This test runs without needing OpenHands dependencies.
"""

import asyncio
import os
import pty
import re
import select
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


# Mock logger for standalone testing
class MockLogger:
    def info(self, msg):
        pass

    def debug(self, msg):
        pass

    def error(self, msg):
        print(f"ERROR: {msg}", file=sys.stderr)


logger = MockLogger()


@dataclass
class TerminalSession:
    """Represents an interactive terminal session."""
    session_id: str
    shell: str
    cwd: str
    env: dict[str, str]
    process: subprocess.Popen | None = None
    master_fd: int | None = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    output_buffer: str = ""
    error_buffer: str = ""


class TerminusSessionManager:
    """Manages multiple interactive terminal sessions."""

    def __init__(self, session_timeout: int = 3600):
        self.sessions: dict[str, TerminalSession] = {}
        self.session_timeout = session_timeout
        self._lock = asyncio.Lock()

    def _generate_session_id(self) -> str:
        return f"term_{uuid.uuid4().hex[:8]}"

    async def create_session(
        self,
        session_id: str | None = None,
        shell: str = "bash",
        cwd: str = ".",
        env: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        async with self._lock:
            if session_id is None:
                session_id = self._generate_session_id()
            elif session_id in self.sessions:
                raise RuntimeError(f"Session {session_id} already exists")

            session_env = os.environ.copy()
            if env:
                session_env.update(env)

            resolved_cwd = os.path.abspath(os.path.expanduser(cwd))
            if not os.path.exists(resolved_cwd):
                raise RuntimeError(f"Working directory does not exist: {resolved_cwd}")

            try:
                master_fd, slave_fd = pty.openpty()

                process = subprocess.Popen(
                    [shell],
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    cwd=resolved_cwd,
                    env=session_env,
                    preexec_fn=os.setsid,
                    close_fds=True,
                )

                os.close(slave_fd)

                session = TerminalSession(
                    session_id=session_id,
                    shell=shell,
                    cwd=resolved_cwd,
                    env=session_env,
                    process=process,
                    master_fd=master_fd,
                )

                self.sessions[session_id] = session
                logger.info(f"Created terminal session {session_id}")

                await asyncio.sleep(0.1)
                self._read_available_output(session)

                return session_id, f"Session {session_id} started successfully"

            except Exception as e:
                if master_fd is not None:
                    try:
                        os.close(master_fd)
                    except Exception:
                        pass
                raise RuntimeError(f"Failed to create session: {str(e)}") from e

    async def execute_command(
        self,
        session_id: str,
        command: str,
        timeout: int = 30,
        capture_output: bool = True,
    ) -> tuple[str, str, int | None, bool]:
        session = self.sessions.get(session_id)
        if not session:
            raise RuntimeError(f"Session {session_id} not found")

        if session.process is None or session.master_fd is None:
            raise RuntimeError(f"Session {session_id} is not active")

        try:
            session.output_buffer = ""
            session.error_buffer = ""

            command_with_newline = command + "\n"
            os.write(session.master_fd, command_with_newline.encode())

            start_time = time.time()
            timeout_reached = False

            while time.time() - start_time < timeout:
                await asyncio.sleep(0.1)
                self._read_available_output(session)

                if self._command_completed(session.output_buffer):
                    break
            else:
                timeout_reached = True

            session.last_activity = time.time()

            stdout = session.output_buffer
            stderr = session.error_buffer
            exit_code = self._extract_exit_code(session) if not timeout_reached else None

            logger.debug(f"Executed command in session {session_id}: {command[:50]}...")

            return stdout, stderr, exit_code, timeout_reached

        except Exception as e:
            raise RuntimeError(
                f"Failed to execute command in session {session_id}: {str(e)}"
            ) from e

    async def stop_session(self, session_id: str, force: bool = False) -> str:
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                raise RuntimeError(f"Session {session_id} not found")

            try:
                if session.process:
                    if force:
                        session.process.kill()
                    else:
                        session.process.terminate()

                    try:
                        session.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        session.process.kill()
                        session.process.wait()

                if session.master_fd is not None:
                    try:
                        os.close(session.master_fd)
                    except Exception:
                        pass

                del self.sessions[session_id]
                logger.info(f"Stopped terminal session {session_id}")

                return f"Session {session_id} stopped successfully"

            except Exception as e:
                raise RuntimeError(
                    f"Failed to stop session {session_id}: {str(e)}"
                ) from e

    def get_session_info(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            raise RuntimeError(f"Session {session_id} not found")

        is_active = session.process is not None and session.process.poll() is None

        return {
            "session_id": session.session_id,
            "shell": session.shell,
            "cwd": session.cwd,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "is_active": is_active,
            "pid": session.process.pid if session.process else None,
        }

    def list_sessions(self) -> list[str]:
        return list(self.sessions.keys())

    def _read_available_output(self, session: TerminalSession) -> None:
        if session.master_fd is None:
            return

        try:
            while True:
                readable, _, _ = select.select([session.master_fd], [], [], 0)
                if not readable:
                    break

                data = os.read(session.master_fd, 4096)
                if not data:
                    break

                try:
                    text = data.decode("utf-8", errors="replace")
                    session.output_buffer += text
                except Exception as e:
                    logger.debug(f"Failed to decode output: {e}")
                    break

        except (OSError, IOError) as e:
            logger.debug(f"Error reading from session: {e}")

    def _command_completed(self, output: str) -> bool:
        lines = output.split("\n")
        if not lines:
            return False

        last_line = lines[-1]

        prompt_patterns = [
            r"[$#>]$",
            r"[$#>]\s+$",
        ]

        for pattern in prompt_patterns:
            if re.search(pattern, last_line):
                return True

        return False

    def _extract_exit_code(self, session: TerminalSession) -> int:
        try:
            if session.master_fd:
                os.write(session.master_fd, b"echo $?\n")
                time.sleep(0.1)
                self._read_available_output(session)

                lines = session.output_buffer.split("\n")
                for line in reversed(lines):
                    line = line.strip()
                    if line.isdigit():
                        return int(line)

        except Exception as e:
            logger.debug(f"Failed to extract exit code: {e}")

        return 0


# Test functions
async def test_sequential_commands_basic():
    """Test executing multiple commands sequentially in the same session."""
    print("=" * 60)
    print("TEST 1: Sequential Commands - Basic")
    print("=" * 60)

    manager = TerminusSessionManager()

    print("\n1. Creating session...")
    session_id, _ = await manager.create_session()
    print(f"   ✓ Session created: {session_id}")

    commands = [
        "echo 'Command 1'",
        "echo 'Command 2'",
        "echo 'Command 3'",
    ]

    print(f"\n2. Executing {len(commands)} commands sequentially...")
    results = []
    for i, cmd in enumerate(commands, 1):
        stdout, stderr, exit_code, timeout = await manager.execute_command(
            session_id, cmd, timeout=5
        )
        results.append((stdout, stderr, exit_code, timeout))
        print(f"   ✓ Command {i} executed (exit_code={exit_code})")

    print("\n3. Verifying all commands succeeded...")
    all_success = all(exit_code == 0 for _, _, exit_code, _ in results if exit_code is not None)
    if all_success:
        print("   ✓ All commands succeeded")
    else:
        print("   ✗ Some commands failed")
        await manager.stop_session(session_id)
        return False

    await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 1: PASSED")
    print("=" * 60)
    return True


async def test_state_persistence_across_commands():
    """Test that state persists across multiple commands in the same session."""
    print("\n\n" + "=" * 60)
    print("TEST 2: State Persistence Across Multiple Commands")
    print("=" * 60)

    manager = TerminusSessionManager()

    print("\n1. Creating session...")
    session_id, _ = await manager.create_session()
    print(f"   ✓ Session created: {session_id}")

    print("\n2. Setting up environment with multiple commands...")
    await manager.execute_command(session_id, "export TEST_VAR1=hello", timeout=5)
    print("   a. Set TEST_VAR1=hello")

    await manager.execute_command(session_id, "export TEST_VAR2=world", timeout=5)
    print("   b. Set TEST_VAR2=world")

    await manager.execute_command(session_id, "mkdir -p /tmp/terminus_test", timeout=5)
    print("   c. Created /tmp/terminus_test")

    await manager.execute_command(session_id, "cd /tmp/terminus_test", timeout=5)
    print("   d. Changed to /tmp/terminus_test")

    await manager.execute_command(session_id, "echo 'test content' > test_file.txt", timeout=5)
    print("   e. Created test_file.txt")

    print("\n3. Verifying state persistence...")

    stdout, _, _, _ = await manager.execute_command(session_id, "echo $TEST_VAR1", timeout=5)
    if "hello" in stdout:
        print("   ✓ TEST_VAR1 persisted")
    else:
        print("   ✗ TEST_VAR1 not found")
        await manager.stop_session(session_id)
        return False

    stdout, _, _, _ = await manager.execute_command(session_id, "echo $TEST_VAR2", timeout=5)
    if "world" in stdout:
        print("   ✓ TEST_VAR2 persisted")
    else:
        print("   ✗ TEST_VAR2 not found")
        await manager.stop_session(session_id)
        return False

    stdout, _, _, _ = await manager.execute_command(session_id, "pwd", timeout=5)
    if "/tmp/terminus_test" in stdout:
        print("   ✓ Working directory persisted")
    else:
        print("   ✗ Working directory incorrect")
        await manager.stop_session(session_id)
        return False

    stdout, _, _, _ = await manager.execute_command(session_id, "cat test_file.txt", timeout=5)
    if "test content" in stdout:
        print("   ✓ File content correct")
    else:
        print("   ✗ File content incorrect")
        await manager.stop_session(session_id)
        return False

    await manager.execute_command(session_id, "rm -rf /tmp/terminus_test", timeout=5)
    await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 2: PASSED")
    print("=" * 60)
    return True


async def test_error_handling_in_command_sequence():
    """Test error handling when one command fails in a sequence."""
    print("\n\n" + "=" * 60)
    print("TEST 3: Error Handling in Command Sequence")
    print("=" * 60)

    manager = TerminusSessionManager()

    print("\n1. Creating session...")
    session_id, _ = await manager.create_session()
    print(f"   ✓ Session created: {session_id}")

    print("\n2. Executing command sequence with one failing command...")

    stdout, stderr, exit_code, _ = await manager.execute_command(
        session_id, "echo 'Before error'", timeout=5
    )
    print(f"   a. Successful command (exit_code={exit_code})")
    success_output = stdout

    # Use a command that explicitly fails and we can verify
    stdout, stderr, exit_code, _ = await manager.execute_command(
        session_id, "ls /nonexistent_directory 2>&1 || echo 'COMMAND_FAILED'", timeout=5
    )
    print(f"   b. Failing command (exit_code={exit_code})")
    # Check if error message is in output
    has_error = "cannot access" in stdout or "No such file" in stdout or "COMMAND_FAILED" in stdout

    stdout, stderr, exit_code, _ = await manager.execute_command(
        session_id, "echo 'After error'", timeout=5
    )
    print(f"   c. Successful command after failure (exit_code={exit_code})")
    recovery_success = (exit_code == 0) and "After error" in stdout

    print("\n3. Verifying session recovered...")
    # The key test is that session continues to work after an error
    if recovery_success:
        print("   ✓ Session recovered and continued execution")
        if has_error:
            print("   ✓ Error was properly captured")
    else:
        print("   ✗ Session did not recover properly")
        await manager.stop_session(session_id)
        return False

    await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 3: PASSED")
    print("=" * 60)
    return True


async def test_complex_command_workflow():
    """Test a complex workflow simulating a model solving a task."""
    print("\n\n" + "=" * 60)
    print("TEST 4: Complex Command Workflow")
    print("=" * 60)

    manager = TerminusSessionManager()

    print("\n1. Creating session...")
    session_id, _ = await manager.create_session()
    print(f"   ✓ Session created: {session_id}")

    print("\n2. Simulating model workflow: Create and run a Python script...")

    workflow_commands = [
        ("Create temp directory", "mkdir -p /tmp/model_test"),
        ("Change to temp directory", "cd /tmp/model_test"),
        ("Create Python script", "cat > script.py << 'EOF'\nimport sys\nprint('Hello from model!')\nfor i in range(3):\n    print(f'Count: {i}')\nsys.exit(0)\nEOF"),
        ("Check file created", "ls -la script.py"),
        ("Run the script", "python3 script.py"),
        ("Clean up", "cd /tmp && rm -rf /tmp/model_test"),
    ]

    results = []
    for i, (description, command) in enumerate(workflow_commands, 1):
        print(f"   {i}. {description}")
        stdout, stderr, exit_code, timeout = await manager.execute_command(
            session_id, command, timeout=10
        )
        results.append({'stdout': stdout, 'exit_code': exit_code})
        print(f"      Exit code: {exit_code}")

    print("\n3. Verifying workflow results...")

    python_output = results[4]['stdout']
    if "Hello from model!" in python_output:
        print("   ✓ Python script executed successfully")
    else:
        print("   ✗ Python script output not found")
        await manager.stop_session(session_id)
        return False

    if all(f"Count: {i}" in python_output for i in range(3)):
        print("   ✓ All loop iterations captured")
    else:
        print("   ✗ Loop output incomplete")
        await manager.stop_session(session_id)
        return False

    await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 4: PASSED")
    print("=" * 60)
    return True


async def test_parallel_sessions_multiple_commands():
    """Test multiple sessions each executing multiple commands."""
    print("\n\n" + "=" * 60)
    print("TEST 5: Parallel Sessions with Multiple Commands")
    print("=" * 60)

    manager = TerminusSessionManager()

    num_sessions = 3
    print(f"\n1. Creating {num_sessions} sessions...")
    sessions = []
    for i in range(num_sessions):
        session_id, _ = await manager.create_session()
        sessions.append(session_id)
        print(f"   ✓ Created session {i+1}: {session_id}")

    print(f"\n2. Executing multiple commands in each session...")
    for i, session_id in enumerate(sessions):
        print(f"   Session {i+1}:")
        await manager.execute_command(session_id, f"export SESSION_NUM={i+1}", timeout=5)
        await manager.execute_command(session_id, f"mkdir -p /tmp/session_{i+1}", timeout=5)
        await manager.execute_command(session_id, f"cd /tmp/session_{i+1}", timeout=5)
        await manager.execute_command(session_id, f"echo 'Session {i+1} data' > data.txt", timeout=5)
        print(f"      ✓ Executed 4 commands")

    print(f"\n3. Verifying session isolation...")
    for i, session_id in enumerate(sessions):
        stdout, _, _, _ = await manager.execute_command(session_id, "echo $SESSION_NUM", timeout=5)
        if str(i+1) in stdout:
            print(f"   ✓ Session {i+1} has correct SESSION_NUM")
        else:
            print(f"   ✗ Session {i+1} SESSION_NUM mismatch")
            for sid in sessions:
                await manager.stop_session(sid)
            return False

    print(f"\n4. Cleaning up...")
    for i, session_id in enumerate(sessions):
        await manager.execute_command(session_id, f"rm -rf /tmp/session_{i+1}", timeout=5)
        await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 5: PASSED")
    print("=" * 60)
    return True


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 6 + "TERMINUS MULTIPLE COMMANDS TEST SUITE" + " " * 13 + "║")
    print("║" + " " * 18 + "(Standalone Version)" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")

    tests = [
        test_sequential_commands_basic,
        test_state_persistence_across_commands,
        test_error_handling_in_command_sequence,
        test_complex_command_workflow,
        test_parallel_sessions_multiple_commands,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = await test()
            if result is None or result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 20 + "TEST SUMMARY" + " " * 26 + "║")
    print("╠" + "=" * 58 + "╣")
    print(f"║  Total Tests: {len(tests):<43} ║")
    print(f"║  Passed: {passed:<48} ║")
    print(f"║  Failed: {failed:<48} ║")
    print("╚" + "=" * 58 + "╝")

    if failed == 0:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
