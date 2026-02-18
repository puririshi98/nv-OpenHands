# Terminus Quick Start Guide

## Running the Tests

### Standalone Test (Recommended - No Dependencies)

```bash
cd /workspace/nv-OpenHands
python3 standalone_terminus_test.py
```

This runs a comprehensive test suite without requiring full OpenHands dependencies. You should see:

```
✅ ALL TESTS PASSED
```

### Demo Script

```bash
python3 demo_terminus.py
```

This shows a simple demonstration of Terminus capabilities including:
- Session creation
- Command execution
- Environment persistence
- Interactive Python REPL

## Basic Usage

### 1. Import and Create Manager

```python
from openhands.agenthub.terminus_agent.terminus_impl import get_session_manager
import asyncio

manager = get_session_manager()
```

### 2. Create a Session

```python
session_id, msg = await manager.create_session(
    shell="bash",          # Optional: defaults to "bash"
    cwd="/workspace",      # Optional: defaults to current directory
    env={"MY_VAR": "val"}  # Optional: additional environment variables
)
print(f"Created: {session_id}")
```

### 3. Execute Commands

```python
stdout, stderr, exit_code, timeout_reached = await manager.execute_command(
    session_id,
    "echo 'Hello World'",
    timeout=5  # seconds
)

print(f"Output: {stdout}")
print(f"Exit code: {exit_code}")
```

### 4. Interactive Input

```python
# Start an interactive process (e.g., Python REPL)
await manager.execute_command(session_id, "python3", timeout=2)

# Send input to the running process
stdout, stderr = await manager.send_input(session_id, "2 + 2")
print(stdout)  # Should show Python evaluating the expression

# Send control sequence to exit
await manager.send_input(session_id, "C-d", is_control=True)
```

### 5. Stop Session

```python
msg = await manager.stop_session(session_id, force=False)
print(msg)  # "Session term_xxx stopped successfully"
```

## Common Patterns

### Pattern 1: Run Multiple Commands in Same Environment

```python
async def multi_command_session():
    manager = get_session_manager()
    session_id, _ = await manager.create_session()

    # Commands execute in same environment
    await manager.execute_command(session_id, "export API_KEY=secret123", timeout=5)
    await manager.execute_command(session_id, "cd /tmp", timeout=5)

    # Environment and directory persist
    stdout, _, _, _ = await manager.execute_command(session_id, "pwd", timeout=5)
    print(stdout)  # /tmp

    stdout, _, _, _ = await manager.execute_command(session_id, "echo $API_KEY", timeout=5)
    print(stdout)  # secret123

    await manager.stop_session(session_id)
```

### Pattern 2: Handle Long-Running Commands

```python
async def long_running_command():
    manager = get_session_manager()
    session_id, _ = await manager.create_session()

    # Run command with appropriate timeout
    stdout, stderr, exit_code, timeout_reached = await manager.execute_command(
        session_id,
        "sleep 10",
        timeout=15  # Longer than command duration
    )

    if timeout_reached:
        print("Command timed out, process may still be running")
        # Can send Ctrl+C to interrupt
        await manager.send_input(session_id, "C-c", is_control=True)

    await manager.stop_session(session_id)
```

### Pattern 3: Multiple Isolated Sessions

```python
async def multiple_sessions():
    manager = get_session_manager()

    # Create multiple sessions
    session1, _ = await manager.create_session()
    session2, _ = await manager.create_session()

    # Each has independent state
    await manager.execute_command(session1, "export ENV=dev", timeout=5)
    await manager.execute_command(session2, "export ENV=prod", timeout=5)

    # Verify isolation
    stdout1, _, _, _ = await manager.execute_command(session1, "echo $ENV", timeout=5)
    stdout2, _, _, _ = await manager.execute_command(session2, "echo $ENV", timeout=5)

    print(f"Session 1: {stdout1.strip()}")  # dev
    print(f"Session 2: {stdout2.strip()}")  # prod

    # Cleanup
    await manager.stop_session(session1)
    await manager.stop_session(session2)
```

### Pattern 4: Interactive REPL Session

```python
async def repl_session():
    manager = get_session_manager()
    session_id, _ = await manager.create_session()

    # Start Python REPL
    await manager.execute_command(session_id, "python3", timeout=1)

    # Execute Python code
    commands = [
        "x = 10",
        "y = 20",
        "print(x + y)",
        "exit()"
    ]

    for cmd in commands:
        stdout, _ = await manager.send_input(session_id, cmd)
        print(f">>> {cmd}")
        if stdout:
            print(stdout)

    await manager.stop_session(session_id)
```

## Control Sequences

Supported control sequences (use with `is_control=True`):

- `C-c` - Ctrl+C (SIGINT - interrupt)
- `C-d` - Ctrl+D (EOF - end of input)
- `C-z` - Ctrl+Z (SIGTSTP - suspend)
- `C-u` - Ctrl+U (clear line)
- `C-l` - Ctrl+L (clear screen)
- And more... (see `terminus_impl.py` for full list)

## Session Information

```python
# Get detailed session info
info = manager.get_session_info(session_id)
print(f"Session ID: {info['session_id']}")
print(f"Shell: {info['shell']}")
print(f"Working Dir: {info['cwd']}")
print(f"Active: {info['is_active']}")
print(f"PID: {info['pid']}")

# List all active sessions
sessions = manager.list_sessions()
print(f"Active sessions: {sessions}")
```

## Error Handling

```python
async def with_error_handling():
    manager = get_session_manager()

    try:
        # This will raise RuntimeError if directory doesn't exist
        session_id, _ = await manager.create_session(cwd="/nonexistent")
    except RuntimeError as e:
        print(f"Failed to create session: {e}")

    try:
        # This will raise RuntimeError if session doesn't exist
        await manager.execute_command("invalid_session", "echo test", timeout=5)
    except RuntimeError as e:
        print(f"Failed to execute: {e}")
```

## Complete Example

```python
import asyncio
from openhands.agenthub.terminus_agent.terminus_impl import get_session_manager

async def complete_example():
    """Complete workflow example."""
    manager = get_session_manager()

    print("Creating session...")
    session_id, msg = await manager.create_session(
        shell="bash",
        cwd="/workspace"
    )
    print(f"✓ {msg}")

    print("\nSetting up environment...")
    await manager.execute_command(
        session_id,
        "export PROJECT=myapp && export ENV=development",
        timeout=5
    )

    print("\nRunning commands...")
    commands = [
        "echo $PROJECT",
        "echo $ENV",
        "pwd",
        "ls -la | head -5"
    ]

    for cmd in commands:
        stdout, stderr, exit_code, _ = await manager.execute_command(
            session_id, cmd, timeout=5
        )
        print(f"\n$ {cmd}")
        if stdout:
            print(stdout.strip())
        if exit_code != 0:
            print(f"Error (exit code: {exit_code}): {stderr}")

    print("\nStarting Python REPL...")
    await manager.execute_command(session_id, "python3", timeout=1)

    python_commands = ["print('Hello from Terminus!')", "2 + 2", "exit()"]
    for cmd in python_commands:
        stdout, _ = await manager.send_input(session_id, cmd)
        print(f">>> {cmd}")
        if stdout:
            print(stdout.strip())

    print("\nCleaning up...")
    msg = await manager.stop_session(session_id)
    print(f"✓ {msg}")

if __name__ == "__main__":
    asyncio.run(complete_example())
```

## Next Steps

1. **Run the tests**: `python3 standalone_terminus_test.py`
2. **Read the full documentation**: `openhands/agenthub/terminus_agent/README.md`
3. **Review implementation details**: `TERMINUS_IMPLEMENTATION.md`
4. **Integrate with your agent**: See Runtime Integration section in implementation doc

## Troubleshooting

### Import Error

If you get `ModuleNotFoundError` when importing:

```python
# Use direct import instead:
from openhands.agenthub.terminus_agent.terminus_impl import TerminusSessionManager
manager = TerminusSessionManager()
```

### Session Hangs

If a session appears to hang:

```python
# Stop it forcefully
await manager.stop_session(session_id, force=True)
```

### Commands Don't Complete

If commands don't seem to complete within the timeout:

1. Increase the timeout value
2. Check if the command is interactive (use `send_input` instead)
3. Verify the command actually completes (some may run indefinitely)

## Support

For more information:
- Full documentation: `openhands/agenthub/terminus_agent/README.md`
- Implementation details: `TERMINUS_IMPLEMENTATION.md`
- Test examples: `standalone_terminus_test.py`, `test_terminus.py`, `demo_terminus.py`
