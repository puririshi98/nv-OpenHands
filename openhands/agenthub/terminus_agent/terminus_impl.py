"""Core implementation for Terminus interactive terminal sessions.

This module provides session management, command execution, and interactive I/O
for persistent terminal sessions with state preservation across commands.
"""

import asyncio
import os
import pty
import re
import select
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from openhands.core.logger import openhands_logger as logger


@dataclass
class TerminalSession:
    """Represents an interactive terminal session.

    Attributes:
        session_id: Unique identifier for this session
        shell: Shell command to use
        cwd: Current working directory
        env: Environment variables
        process: The subprocess instance
        master_fd: Master file descriptor for PTY
        created_at: Timestamp when session was created
        last_activity: Timestamp of last activity
    """

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
    """Manages multiple interactive terminal sessions.

    This class handles:
    - Creating and destroying terminal sessions
    - Executing commands in sessions
    - Sending input to running processes
    - Capturing output from sessions
    - Session cleanup and timeout handling
    """

    def __init__(self, session_timeout: int = 3600):
        """Initialize the session manager.

        Args:
            session_timeout: Maximum idle time for a session in seconds (default: 1 hour)
        """
        self.sessions: dict[str, TerminalSession] = {}
        self.session_timeout = session_timeout
        self._lock = asyncio.Lock()

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"term_{uuid.uuid4().hex[:8]}"

    async def create_session(
        self,
        session_id: str | None = None,
        shell: str = "bash",
        cwd: str = ".",
        env: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """Create a new terminal session.

        Args:
            session_id: Optional session ID (auto-generated if not provided)
            shell: Shell to use (default: bash)
            cwd: Working directory (default: current directory)
            env: Environment variables (default: inherit from parent)

        Returns:
            Tuple of (session_id, status_message)

        Raises:
            RuntimeError: If session creation fails
        """
        async with self._lock:
            if session_id is None:
                session_id = self._generate_session_id()
            elif session_id in self.sessions:
                raise RuntimeError(f"Session {session_id} already exists")

            # Prepare environment
            session_env = os.environ.copy()
            if env:
                session_env.update(env)

            # Resolve working directory
            resolved_cwd = os.path.abspath(os.path.expanduser(cwd))
            if not os.path.exists(resolved_cwd):
                raise RuntimeError(f"Working directory does not exist: {resolved_cwd}")

            try:
                # Create PTY for interactive session
                master_fd, slave_fd = pty.openpty()

                # Start the shell process
                process = subprocess.Popen(
                    [shell],
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    cwd=resolved_cwd,
                    env=session_env,
                    preexec_fn=os.setsid,  # Create new session
                    close_fds=True,
                )

                # Close slave end in parent process
                os.close(slave_fd)

                # Create session object
                session = TerminalSession(
                    session_id=session_id,
                    shell=shell,
                    cwd=resolved_cwd,
                    env=session_env,
                    process=process,
                    master_fd=master_fd,
                )

                self.sessions[session_id] = session

                logger.info(
                    f"Created terminal session {session_id} (shell={shell}, cwd={resolved_cwd})"
                )

                # Read initial output (shell prompt, etc.)
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
        """Execute a command in an existing session.

        Args:
            session_id: ID of the session to use
            command: Command to execute
            timeout: Maximum execution time in seconds
            capture_output: Whether to capture output

        Returns:
            Tuple of (stdout, stderr, exit_code, timeout_reached)

        Raises:
            RuntimeError: If session not found or execution fails
        """
        session = self.sessions.get(session_id)
        if not session:
            raise RuntimeError(f"Session {session_id} not found")

        if session.process is None or session.master_fd is None:
            raise RuntimeError(f"Session {session_id} is not active")

        try:
            # Clear buffers
            session.output_buffer = ""
            session.error_buffer = ""

            # Send command
            command_with_newline = command + "\n"
            os.write(session.master_fd, command_with_newline.encode())

            # Wait for command to complete
            start_time = time.time()
            timeout_reached = False

            while time.time() - start_time < timeout:
                await asyncio.sleep(0.1)
                self._read_available_output(session)

                # Check if command completed by looking for prompt
                # This is a simple heuristic - could be improved
                if self._command_completed(session.output_buffer):
                    break
            else:
                timeout_reached = True

            # Update last activity
            session.last_activity = time.time()

            # Parse output and exit code
            stdout = session.output_buffer
            stderr = session.error_buffer
            exit_code = self._extract_exit_code(session) if not timeout_reached else None

            logger.debug(
                f"Executed command in session {session_id}: {command[:50]}... "
                f"(exit_code={exit_code}, timeout={timeout_reached})"
            )

            return stdout, stderr, exit_code, timeout_reached

        except Exception as e:
            raise RuntimeError(
                f"Failed to execute command in session {session_id}: {str(e)}"
            ) from e

    async def send_input(
        self, session_id: str, input_text: str = "", is_control: bool = False
    ) -> tuple[str, str]:
        """Send input to a running process in the session.

        Args:
            session_id: ID of the session
            input_text: Text to send (or empty to just retrieve output)
            is_control: Whether input is a control sequence (e.g., 'C-c')

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            RuntimeError: If session not found
        """
        session = self.sessions.get(session_id)
        if not session:
            raise RuntimeError(f"Session {session_id} not found")

        if session.process is None or session.master_fd is None:
            raise RuntimeError(f"Session {session_id} is not active")

        try:
            # Clear buffers
            session.output_buffer = ""
            session.error_buffer = ""

            # Send input if provided
            if input_text:
                if is_control:
                    # Handle control sequences
                    input_bytes = self._parse_control_sequence(input_text)
                else:
                    # Send regular text with newline
                    input_bytes = (input_text + "\n").encode()

                os.write(session.master_fd, input_bytes)

            # Wait a bit for output
            await asyncio.sleep(0.2)
            self._read_available_output(session)

            # Update last activity
            session.last_activity = time.time()

            return session.output_buffer, session.error_buffer

        except Exception as e:
            raise RuntimeError(
                f"Failed to send input to session {session_id}: {str(e)}"
            ) from e

    async def stop_session(self, session_id: str, force: bool = False) -> str:
        """Stop and clean up a terminal session.

        Args:
            session_id: ID of the session to stop
            force: Whether to force kill the process

        Returns:
            Status message

        Raises:
            RuntimeError: If session not found
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                raise RuntimeError(f"Session {session_id} not found")

            try:
                # Terminate the process
                if session.process:
                    if force:
                        # Force kill
                        session.process.kill()
                    else:
                        # Graceful termination
                        session.process.terminate()

                    # Wait for process to exit
                    try:
                        session.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        session.process.kill()
                        session.process.wait()

                # Close file descriptor
                if session.master_fd is not None:
                    try:
                        os.close(session.master_fd)
                    except Exception:
                        pass

                # Remove session
                del self.sessions[session_id]

                logger.info(f"Stopped terminal session {session_id}")

                return f"Session {session_id} stopped successfully"

            except Exception as e:
                raise RuntimeError(
                    f"Failed to stop session {session_id}: {str(e)}"
                ) from e

    def get_session_info(self, session_id: str) -> dict[str, Any]:
        """Get information about a session.

        Args:
            session_id: ID of the session

        Returns:
            Dictionary with session information

        Raises:
            RuntimeError: If session not found
        """
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
        """Get list of active session IDs."""
        return list(self.sessions.keys())

    async def cleanup_idle_sessions(self) -> list[str]:
        """Clean up sessions that have been idle too long.

        Returns:
            List of cleaned up session IDs
        """
        now = time.time()
        to_cleanup = []

        for session_id, session in list(self.sessions.items()):
            if now - session.last_activity > self.session_timeout:
                to_cleanup.append(session_id)

        for session_id in to_cleanup:
            try:
                await self.stop_session(session_id, force=True)
            except Exception as e:
                logger.error(f"Failed to cleanup session {session_id}: {e}")

        return to_cleanup

    def _read_available_output(self, session: TerminalSession) -> None:
        """Read any available output from the session."""
        if session.master_fd is None:
            return

        try:
            while True:
                # Check if data is available
                readable, _, _ = select.select([session.master_fd], [], [], 0)
                if not readable:
                    break

                # Read data
                data = os.read(session.master_fd, 4096)
                if not data:
                    break

                # Decode and append to buffer
                try:
                    text = data.decode("utf-8", errors="replace")
                    session.output_buffer += text
                except Exception as e:
                    logger.debug(f"Failed to decode output: {e}")
                    break

        except (OSError, IOError) as e:
            # EOF or other read error
            logger.debug(f"Error reading from session: {e}")

    def _command_completed(self, output: str) -> bool:
        """Heuristic to detect if command has completed.

        This looks for common shell prompts. Could be improved with more
        sophisticated detection.
        """
        # Look for common prompt patterns
        lines = output.split("\n")
        if not lines:
            return False

        last_line = lines[-1]

        # Common prompt indicators
        prompt_patterns = [
            r"[$#>]$",  # Ends with $, #, or >
            r"[$#>]\s+$",  # Ends with $, #, or > followed by whitespace
        ]

        for pattern in prompt_patterns:
            if re.search(pattern, last_line):
                return True

        return False

    def _extract_exit_code(self, session: TerminalSession) -> int:
        """Extract exit code from last command.

        Returns 0 if exit code cannot be determined.
        """
        try:
            # Send command to get last exit code
            if session.master_fd:
                os.write(session.master_fd, b"echo $?\n")
                time.sleep(0.1)
                self._read_available_output(session)

                # Parse exit code from output
                lines = session.output_buffer.split("\n")
                for line in reversed(lines):
                    line = line.strip()
                    if line.isdigit():
                        return int(line)

        except Exception as e:
            logger.debug(f"Failed to extract exit code: {e}")

        return 0

    def _parse_control_sequence(self, control: str) -> bytes:
        """Parse control sequence string to bytes.

        Args:
            control: Control sequence like 'C-c', 'C-d', 'C-z'

        Returns:
            Bytes to send

        Raises:
            ValueError: If control sequence is invalid
        """
        control = control.strip().upper()

        # Map of control sequences
        control_map = {
            "C-A": b"\x01",
            "C-B": b"\x02",
            "C-C": b"\x03",
            "C-D": b"\x04",
            "C-E": b"\x05",
            "C-F": b"\x06",
            "C-G": b"\x07",
            "C-H": b"\x08",
            "C-I": b"\x09",
            "C-J": b"\x0a",
            "C-K": b"\x0b",
            "C-L": b"\x0c",
            "C-M": b"\x0d",
            "C-N": b"\x0e",
            "C-O": b"\x0f",
            "C-P": b"\x10",
            "C-Q": b"\x11",
            "C-R": b"\x12",
            "C-S": b"\x13",
            "C-T": b"\x14",
            "C-U": b"\x15",
            "C-V": b"\x16",
            "C-W": b"\x17",
            "C-X": b"\x18",
            "C-Y": b"\x19",
            "C-Z": b"\x1a",
        }

        if control in control_map:
            return control_map[control]

        raise ValueError(f"Invalid control sequence: {control}")


# Global session manager instance
_session_manager: TerminusSessionManager | None = None


def get_session_manager() -> TerminusSessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = TerminusSessionManager()
    return _session_manager
