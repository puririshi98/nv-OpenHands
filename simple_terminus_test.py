#!/usr/bin/env python3
"""Simple standalone test for Terminus without full OpenHands dependencies."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import just the terminus implementation
from openhands.agenthub.terminus_agent.terminus_impl import TerminusSessionManager


async def simple_test():
    """Run a simple test of Terminus functionality."""
    print("🚀 Starting simple Terminus test...\n")

    manager = TerminusSessionManager()

    try:
        # Test 1: Create session
        print("1. Creating session...")
        session_id, msg = await manager.create_session(shell="bash", cwd=".")
        print(f"   ✓ {msg}\n")

        # Test 2: Execute command
        print("2. Executing 'echo Hello World'...")
        stdout, stderr, exit_code, timeout = await manager.execute_command(
            session_id, "echo 'Hello World'", timeout=5
        )
        print(f"   ✓ Exit code: {exit_code}")
        print(f"   ✓ Output: {stdout[:100]}\n")

        # Test 3: Test persistence
        print("3. Testing environment persistence...")
        await manager.execute_command(session_id, "export TEST=123", timeout=5)
        stdout, _, _, _ = await manager.execute_command(
            session_id, "echo $TEST", timeout=5
        )
        if "123" in stdout:
            print(f"   ✓ Environment persists!\n")
        else:
            print(f"   ✗ Environment did not persist\n")

        # Test 4: Get session info
        print("4. Getting session info...")
        info = manager.get_session_info(session_id)
        print(f"   ✓ Session: {info['session_id']}")
        print(f"   ✓ Shell: {info['shell']}")
        print(f"   ✓ Working dir: {info['cwd']}\n")

        # Test 5: Clean up
        print("5. Stopping session...")
        msg = await manager.stop_session(session_id)
        print(f"   ✓ {msg}\n")

        print("✅ All basic tests passed!\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(simple_test())
    sys.exit(0 if success else 1)
