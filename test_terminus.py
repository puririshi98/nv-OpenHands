#!/usr/bin/env python3
"""
Test script for Terminus interactive terminal functionality.

This script demonstrates and tests the Terminus session management,
command execution, and interactive I/O capabilities.
"""

import asyncio
import sys

# Direct import to avoid dependency issues in agenthub/__init__.py
from openhands.agenthub.terminus_agent.terminus_impl import get_session_manager


async def test_basic_session():
    """Test basic session creation and command execution."""
    print("=" * 60)
    print("TEST 1: Basic Session Creation and Command Execution")
    print("=" * 60)

    manager = get_session_manager()

    # Create a new session
    print("\n1. Creating new terminal session...")
    session_id, msg = await manager.create_session(shell="bash", cwd=".")
    print(f"   ✓ {msg}")
    print(f"   Session ID: {session_id}")

    # Execute a simple command
    print("\n2. Executing 'pwd' command...")
    stdout, stderr, exit_code, timeout = await manager.execute_command(
        session_id, "pwd", timeout=5
    )
    print(f"   ✓ Exit code: {exit_code}")
    print(f"   Output: {stdout.strip()}")

    # Execute another command in the same session
    print("\n3. Executing 'echo $SHELL' command...")
    stdout, stderr, exit_code, timeout = await manager.execute_command(
        session_id, "echo $SHELL", timeout=5
    )
    print(f"   ✓ Exit code: {exit_code}")
    print(f"   Output: {stdout.strip()}")

    # Get session info
    print("\n4. Getting session information...")
    info = manager.get_session_info(session_id)
    print(f"   ✓ Session info:")
    for key, value in info.items():
        print(f"     - {key}: {value}")

    # Stop the session
    print("\n5. Stopping session...")
    msg = await manager.stop_session(session_id)
    print(f"   ✓ {msg}")

    print("\n" + "=" * 60)
    print("TEST 1: PASSED")
    print("=" * 60)


async def test_environment_persistence():
    """Test that environment variables persist across commands."""
    print("\n\n" + "=" * 60)
    print("TEST 2: Environment Variable Persistence")
    print("=" * 60)

    manager = get_session_manager()

    # Create session
    print("\n1. Creating session...")
    session_id, _ = await manager.create_session()
    print(f"   ✓ Session created: {session_id}")

    # Set an environment variable
    print("\n2. Setting TEST_VAR=hello...")
    await manager.execute_command(session_id, "export TEST_VAR=hello", timeout=5)
    print("   ✓ Variable set")

    # Verify it persists
    print("\n3. Checking if TEST_VAR persists...")
    stdout, _, _, _ = await manager.execute_command(
        session_id, "echo $TEST_VAR", timeout=5
    )
    result = stdout.strip()
    if "hello" in result:
        print(f"   ✓ Variable persisted! Output: {result}")
    else:
        print(f"   ✗ Variable did not persist. Output: {result}")
        return False

    # Change directory
    print("\n4. Changing directory to /tmp...")
    await manager.execute_command(session_id, "cd /tmp", timeout=5)
    print("   ✓ Changed directory")

    # Verify directory persists
    print("\n5. Checking current directory...")
    stdout, _, _, _ = await manager.execute_command(session_id, "pwd", timeout=5)
    result = stdout.strip()
    if "/tmp" in result:
        print(f"   ✓ Directory persisted! Output: {result}")
    else:
        print(f"   ✗ Directory did not persist. Output: {result}")
        return False

    # Cleanup
    await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 2: PASSED")
    print("=" * 60)
    return True


async def test_interactive_process():
    """Test interactive process handling."""
    print("\n\n" + "=" * 60)
    print("TEST 3: Interactive Process Handling")
    print("=" * 60)

    manager = get_session_manager()

    # Create session
    print("\n1. Creating session...")
    session_id, _ = await manager.create_session()
    print(f"   ✓ Session created: {session_id}")

    # Start Python REPL
    print("\n2. Starting Python REPL...")
    stdout, _, _, _ = await manager.execute_command(
        session_id, "python3", timeout=2
    )
    print(f"   ✓ Python started")

    # Send input to REPL
    print("\n3. Sending '2 + 2' to Python...")
    stdout, stderr = await manager.send_input(session_id, "2 + 2")
    print(f"   ✓ Input sent")
    if stdout:
        print(f"   Output: {stdout[:100]}")

    # Send another command
    print("\n4. Sending 'print(\"Hello from Terminus!\")' to Python...")
    stdout, stderr = await manager.send_input(session_id, 'print("Hello from Terminus!")')
    print(f"   ✓ Input sent")
    if stdout:
        print(f"   Output: {stdout[:100]}")

    # Exit Python with Ctrl+D
    print("\n5. Sending Ctrl+D to exit Python...")
    stdout, stderr = await manager.send_input(session_id, "C-d", is_control=True)
    print(f"   ✓ Control sequence sent")

    # Cleanup
    await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 3: PASSED")
    print("=" * 60)


async def test_multiple_sessions():
    """Test managing multiple concurrent sessions."""
    print("\n\n" + "=" * 60)
    print("TEST 4: Multiple Concurrent Sessions")
    print("=" * 60)

    manager = get_session_manager()

    # Create multiple sessions
    print("\n1. Creating 3 sessions...")
    sessions = []
    for i in range(3):
        session_id, _ = await manager.create_session()
        sessions.append(session_id)
        print(f"   ✓ Created session {i+1}: {session_id}")

    # Execute commands in each session
    print("\n2. Executing commands in each session...")
    for i, session_id in enumerate(sessions):
        await manager.execute_command(
            session_id, f"export SESSION_NUM={i+1}", timeout=5
        )
        print(f"   ✓ Set SESSION_NUM={i+1} in session {session_id}")

    # Verify each session has its own environment
    print("\n3. Verifying session isolation...")
    for i, session_id in enumerate(sessions):
        stdout, _, _, _ = await manager.execute_command(
            session_id, "echo $SESSION_NUM", timeout=5
        )
        result = stdout.strip()
        if str(i+1) in result:
            print(f"   ✓ Session {session_id} has SESSION_NUM={i+1}")
        else:
            print(f"   ✗ Session {session_id} isolation failed: {result}")
            return False

    # List all sessions
    print("\n4. Listing all active sessions...")
    active_sessions = manager.list_sessions()
    print(f"   ✓ Found {len(active_sessions)} active sessions")
    for sid in active_sessions:
        print(f"     - {sid}")

    # Cleanup all sessions
    print("\n5. Cleaning up all sessions...")
    for session_id in sessions:
        await manager.stop_session(session_id)
        print(f"   ✓ Stopped session {session_id}")

    print("\n" + "=" * 60)
    print("TEST 4: PASSED")
    print("=" * 60)
    return True


async def test_timeout_handling():
    """Test command timeout handling."""
    print("\n\n" + "=" * 60)
    print("TEST 5: Timeout Handling")
    print("=" * 60)

    manager = get_session_manager()

    # Create session
    print("\n1. Creating session...")
    session_id, _ = await manager.create_session()
    print(f"   ✓ Session created: {session_id}")

    # Execute a long-running command with short timeout
    print("\n2. Executing 'sleep 10' with 2 second timeout...")
    stdout, stderr, exit_code, timeout_reached = await manager.execute_command(
        session_id, "sleep 10", timeout=2
    )

    if timeout_reached:
        print(f"   ✓ Timeout reached as expected")
        print(f"   Exit code: {exit_code} (None indicates still running)")
    else:
        print(f"   ✗ Command completed unexpectedly")
        return False

    # Stop the session (will kill the sleeping process)
    print("\n3. Stopping session...")
    await manager.stop_session(session_id, force=True)
    print(f"   ✓ Session stopped (forced)")

    print("\n" + "=" * 60)
    print("TEST 5: PASSED")
    print("=" * 60)
    return True


async def test_error_handling():
    """Test error handling for invalid operations."""
    print("\n\n" + "=" * 60)
    print("TEST 6: Error Handling")
    print("=" * 60)

    manager = get_session_manager()

    # Test: Execute command in non-existent session
    print("\n1. Testing command in non-existent session...")
    try:
        await manager.execute_command("nonexistent", "echo test", timeout=5)
        print("   ✗ Should have raised RuntimeError")
        return False
    except RuntimeError as e:
        print(f"   ✓ Correctly raised RuntimeError: {e}")

    # Test: Get info for non-existent session
    print("\n2. Testing get_session_info for non-existent session...")
    try:
        manager.get_session_info("nonexistent")
        print("   ✗ Should have raised RuntimeError")
        return False
    except RuntimeError as e:
        print(f"   ✓ Correctly raised RuntimeError: {e}")

    # Test: Create session in non-existent directory
    print("\n3. Testing session creation in non-existent directory...")
    try:
        await manager.create_session(cwd="/nonexistent/directory")
        print("   ✗ Should have raised RuntimeError")
        return False
    except RuntimeError as e:
        print(f"   ✓ Correctly raised RuntimeError: {e}")

    # Test: Invalid control sequence
    print("\n4. Testing invalid control sequence...")
    session_id, _ = await manager.create_session()
    try:
        await manager.send_input(session_id, "INVALID-SEQ", is_control=True)
        print("   ✗ Should have raised ValueError")
        await manager.stop_session(session_id)
        return False
    except (RuntimeError, ValueError) as e:
        print(f"   ✓ Correctly raised error: {type(e).__name__}")

    await manager.stop_session(session_id)

    print("\n" + "=" * 60)
    print("TEST 6: PASSED")
    print("=" * 60)
    return True


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "TERMINUS INTERACTIVE TERMINAL TEST SUITE" + " " * 8 + "║")
    print("╚" + "=" * 58 + "╝")

    tests = [
        test_basic_session,
        test_environment_persistence,
        test_interactive_process,
        test_multiple_sessions,
        test_timeout_handling,
        test_error_handling,
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

    # Summary
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
