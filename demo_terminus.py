#!/usr/bin/env python3
"""
Simple demo script showing Terminus usage.

This demonstrates the basic workflow of using Terminus for
interactive terminal sessions.
"""

import asyncio

# Direct import to avoid dependency issues in agenthub/__init__.py
from openhands.agenthub.terminus_agent.terminus_impl import get_session_manager


async def demo():
    """Simple demonstration of Terminus functionality."""
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "TERMINUS DEMO" + " " * 30 + "║")
    print("╚" + "=" * 58 + "╝\n")

    # Get the session manager
    manager = get_session_manager()

    # 1. Create a session
    print("📝 Creating a new terminal session...")
    session_id, msg = await manager.create_session(shell="bash", cwd="/workspace/nv-OpenHands")
    print(f"   {msg}\n")

    # 2. Execute some commands
    print("📝 Executing commands in the session...\n")

    commands = [
        "pwd",
        "echo 'Hello from Terminus!'",
        "export MY_VAR='test123'",
        "echo $MY_VAR",
        "ls -la | head -5",
    ]

    for cmd in commands:
        print(f"   $ {cmd}")
        stdout, stderr, exit_code, _ = await manager.execute_command(
            session_id, cmd, timeout=5
        )

        if stdout:
            for line in stdout.strip().split('\n')[:5]:  # Limit output
                if line.strip():
                    print(f"     {line}")

        if exit_code is not None and exit_code != 0:
            print(f"     ⚠️  Exit code: {exit_code}")
        print()

    # 3. Show session info
    print("📝 Session information:")
    info = manager.get_session_info(session_id)
    print(f"   Session ID: {info['session_id']}")
    print(f"   Shell: {info['shell']}")
    print(f"   Working Dir: {info['cwd']}")
    print(f"   Active: {info['is_active']}")
    print(f"   PID: {info['pid']}\n")

    # 4. Interactive demo with Python
    print("📝 Starting Python REPL for interactive demo...")
    await manager.execute_command(session_id, "python3", timeout=1)

    print("   >>> 2 + 2")
    stdout, _ = await manager.send_input(session_id, "2 + 2")
    if stdout:
        print(f"   {stdout.strip()}")

    print("   >>> print('Terminus is working!')")
    stdout, _ = await manager.send_input(session_id, "print('Terminus is working!')")
    if stdout:
        print(f"   {stdout.strip()}")

    print("   >>> exit()")
    await manager.send_input(session_id, "exit()")
    print()

    # 5. Stop the session
    print("📝 Stopping the session...")
    msg = await manager.stop_session(session_id)
    print(f"   {msg}\n")

    print("✅ Demo complete!")
    print("\nTer minus provides:")
    print("  • Persistent terminal sessions")
    print("  • Environment variable persistence")
    print("  • Interactive process support")
    print("  • Multi-session management")
    print("  • Timeout handling")


if __name__ == "__main__":
    asyncio.run(demo())
