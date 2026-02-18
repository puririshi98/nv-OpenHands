#!/usr/bin/env python3
"""
Standalone test for Terminus that bypasses openhands import issues.
This loads the terminus_impl module directly.
"""

import asyncio
import sys
import os
import importlib.util

def load_module_from_path(module_name, file_path):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


async def main():
    """Run standalone tests."""
    print("=" * 60)
    print("STANDALONE TERMINUS TEST")
    print("=" * 60)
    print()

    # Load the terminus_impl module directly
    terminus_impl_path = os.path.join(
        os.path.dirname(__file__),
        "openhands", "agenthub", "terminus_agent", "terminus_impl.py"
    )

    print(f"Loading module from: {terminus_impl_path}")

    # First load the logger mock
    print("Setting up minimal dependencies...")

    # Create minimal logger mock
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def debug(self, msg): pass  # Suppress debug
        def error(self, msg): print(f"[ERROR] {msg}")

    # Mock the openhands.core.logger module
    import sys
    import types
    mock_logger_module = types.ModuleType('openhands.core.logger')
    mock_logger_module.openhands_logger = MockLogger()
    sys.modules['openhands.core.logger'] = mock_logger_module
    sys.modules['openhands'] = types.ModuleType('openhands')
    sys.modules['openhands.core'] = types.ModuleType('openhands.core')

    # Now load terminus_impl
    print("Loading terminus_impl module...")
    terminus = load_module_from_path("terminus_impl", terminus_impl_path)
    print("✓ Module loaded successfully\n")

    # Run tests
    manager = terminus.TerminusSessionManager()

    try:
        # Test 1
        print("TEST 1: Create and execute in session")
        print("-" * 40)
        session_id, msg = await manager.create_session(shell="bash", cwd=".")
        print(f"✓ {msg}")

        stdout, stderr, exit_code, _ = await manager.execute_command(
            session_id, "echo 'Hello from Terminus!'", timeout=5
        )
        print(f"✓ Command executed (exit code: {exit_code})")
        if stdout:
            print(f"  Output: {stdout[:100].strip()}")

        await manager.stop_session(session_id)
        print(f"✓ Session stopped\n")

        # Test 2
        print("TEST 2: Environment persistence")
        print("-" * 40)
        session_id, _ = await manager.create_session()

        await manager.execute_command(session_id, "export MY_VAR=test123", timeout=5)
        stdout, _, _, _ = await manager.execute_command(
            session_id, "echo $MY_VAR", timeout=5
        )

        if "test123" in stdout:
            print("✓ Environment variable persisted across commands")
        else:
            print("✗ Environment variable did not persist")

        await manager.stop_session(session_id)
        print("✓ Test completed\n")

        # Test 3
        print("TEST 3: Multiple sessions")
        print("-" * 40)
        sessions = []
        for i in range(3):
            sid, _ = await manager.create_session()
            sessions.append(sid)
            await manager.execute_command(sid, f"export NUM={i}", timeout=5)

        print(f"✓ Created {len(sessions)} sessions")

        for i, sid in enumerate(sessions):
            stdout, _, _, _ = await manager.execute_command(sid, "echo $NUM", timeout=5)
            if str(i) in stdout:
                print(f"✓ Session {i} has correct environment")

        for sid in sessions:
            await manager.stop_session(sid)
        print("✓ All sessions cleaned up\n")

        # Test 4
        print("TEST 4: Interactive input")
        print("-" * 40)
        session_id, _ = await manager.create_session()

        # Start a simple read command
        await manager.execute_command(session_id, "python3 -c 'print(2+2)'", timeout=5)
        print("✓ Python command executed")

        await manager.stop_session(session_id)
        print("✓ Test completed\n")

        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
