# Terminus: Interactive Terminal Sessions for OpenHands

Terminus provides persistent interactive terminal session management for OpenHands agents, enabling sophisticated command execution with state preservation, interactive process handling, and multi-session support.

## Features

- **Persistent Sessions**: Terminal sessions maintain environment variables, working directory, and shell state across multiple commands
- **Interactive Process Support**: Send input to running processes (REPLs, debuggers, interactive CLIs)
- **Multi-Session Management**: Run multiple isolated terminal sessions concurrently
- **Control Sequences**: Support for sending control sequences (Ctrl+C, Ctrl+D, etc.)
- **Timeout Handling**: Configurable timeouts for command execution
- **Session Isolation**: Each session has its own environment and state
- **Automatic Cleanup**: Sessions can be automatically cleaned up after idle timeout

## Architecture

### Components

1. **Action Classes** (`openhands/events/action/terminus.py`):
   - `TerminusStartAction`: Create a new terminal session
   - `TerminusExecuteAction`: Execute command in a session
   - `TerminusInputAction`: Send input to running process
   - `TerminusStopAction`: Stop and cleanup a session

2. **Observation Classes** (`openhands/events/observation/terminus.py`):
   - `TerminusOutputObservation`: Command output and exit codes
   - `TerminusErrorObservation`: Error information
   - `TerminusSessionObservation`: Session status and metadata

3. **Implementation** (`terminus_impl.py`):
   - `TerminusSessionManager`: Core session management
   - `TerminalSession`: Session state representation
   - PTY-based interactive terminal emulation

4. **LLM Tools** (`tools/*.py`):
   - Tool definitions for LLM function calling
   - Integrated with OpenHands agent framework

## Usage

### Basic Example

```python
from openhands.agenthub.terminus_agent.terminus_impl import get_session_manager

async def example():
    manager = get_session_manager()

    # Create a session
    session_id, msg = await manager.create_session(
        shell="bash",
        cwd="/workspace"
    )

    # Execute commands
    stdout, stderr, exit_code, timeout = await manager.execute_command(
        session_id,
        "echo 'Hello World'",
        timeout=5
    )

    # Stop session
    await manager.stop_session(session_id)
```

### Environment Persistence

```python
# Set environment variable
await manager.execute_command(session_id, "export MY_VAR=value", timeout=5)

# Variable persists in same session
stdout, _, _, _ = await manager.execute_command(session_id, "echo $MY_VAR", timeout=5)
# Output: value
```

### Interactive Processes

```python
# Start Python REPL
await manager.execute_command(session_id, "python3", timeout=2)

# Send input to REPL
stdout, stderr = await manager.send_input(session_id, "2 + 2")

# Send control sequence to exit
await manager.send_input(session_id, "C-d", is_control=True)
```

### Multiple Sessions

```python
# Create multiple isolated sessions
session1, _ = await manager.create_session()
session2, _ = await manager.create_session()

# Each session has independent state
await manager.execute_command(session1, "export VAR=A", timeout=5)
await manager.execute_command(session2, "export VAR=B", timeout=5)

# Session 1: VAR=A
# Session 2: VAR=B
```

## Action and Observation Schema

### TerminusStartAction

```python
{
    "action": "terminus_start",
    "session_id": "optional_custom_id",  # Auto-generated if omitted
    "shell": "bash",                      # Default: "bash"
    "cwd": ".",                          # Default: current directory
    "env": {"KEY": "value"}              # Optional environment vars
}
```

### TerminusExecuteAction

```python
{
    "action": "terminus_execute",
    "session_id": "term_abc123",         # Required
    "command": "ls -la",                 # Required
    "timeout": 30,                       # Seconds, default: 30
    "capture_output": true               # Default: true
}
```

### TerminusInputAction

```python
{
    "action": "terminus_input",
    "session_id": "term_abc123",         # Required
    "input_text": "some input",          # Empty string to just retrieve output
    "is_control": false                  # true for control sequences like "C-c"
}
```

### TerminusStopAction

```python
{
    "action": "terminus_stop",
    "session_id": "term_abc123",         # Required
    "force": false                       # Force kill if true
}
```

### TerminusOutputObservation

```python
{
    "observation": "terminus_output",
    "session_id": "term_abc123",
    "stdout": "command output...",
    "stderr": "error output...",
    "exit_code": 0,                      # None if still running
    "command": "original command",
    "timeout_reached": false
}
```

## Integration with TerminalBench

Terminus is designed to work seamlessly with TerminalBench evaluation tasks:

1. **Persistent State**: Commands maintain environment and working directory
2. **Interactive Tools**: Support for tools requiring user input
3. **Long-running Processes**: Proper timeout handling for long operations
4. **Process Control**: Ability to send signals and control sequences

### TerminalBench Usage

```bash
# Install terminal-bench
pip install terminal-bench

# Run evaluation with OpenHands + Terminus
tb run \
    --dataset-name terminal-bench-core \
    --dataset-version 0.1.1 \
    --agent openhands \
    --model gpt-4 \
    --cleanup
```

## Testing

### Run Tests

```bash
# Standalone test (no dependencies)
python3 standalone_terminus_test.py

# Full test suite (requires OpenHands dependencies)
python3 test_terminus.py

# Simple demo
python3 demo_terminus.py
```

### Test Coverage

- Basic session creation and execution
- Environment variable persistence
- Interactive process handling
- Multiple concurrent sessions
- Timeout handling
- Error handling and edge cases

## Implementation Notes

### PTY (Pseudo-Terminal) Usage

Terminus uses PTY (pseudo-terminal) to create truly interactive terminal sessions. This provides:
- Full terminal emulation (colors, control sequences, etc.)
- Interactive stdin/stdout/stderr
- Process group management
- Proper signal handling

### Command Completion Detection

The implementation uses heuristics to detect when commands complete:
- Looking for shell prompts (`$`, `#`, `>`)
- Timeout-based completion
- Process termination detection

This can be improved with more sophisticated prompt detection or explicit markers.

### Session Cleanup

Sessions are automatically cleaned up:
- When explicitly stopped with `TerminusStopAction`
- After idle timeout (default: 1 hour)
- On process termination
- During manager shutdown

## Known Limitations

1. **Prompt Detection**: Current heuristic may not work with custom prompts
2. **Exit Code Extraction**: Requires running `echo $?` which may not always be reliable
3. **Terminal Size**: Fixed terminal size, may affect some TUI applications
4. **Binary Output**: Binary data in output may cause encoding issues

## Future Enhancements

- [ ] Configurable prompt detection patterns
- [ ] Terminal size negotiation (SIGWINCH)
- [ ] Session persistence across runtime restarts
- [ ] Enhanced error recovery
- [ ] Performance optimizations for high-frequency commands
- [ ] Support for terminal multiplexers (tmux, screen)
- [ ] Recording and replay of terminal sessions

## Contributing

When extending Terminus:

1. Maintain backward compatibility with existing sessions
2. Add comprehensive tests for new features
3. Update this documentation
4. Consider TerminalBench compatibility
5. Handle edge cases and error conditions

## License

Part of the OpenHands project. See main repository for license information.
