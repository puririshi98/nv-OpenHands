"""Terminus action classes for interactive terminal operations.

These actions provide persistent interactive terminal session functionality with:
- Session-based command execution
- Interactive process handling (stdin/stdout/stderr)
- Process state management
- Timeout handling
- Multi-session support
"""

from dataclasses import dataclass
from typing import ClassVar

from openhands.core.schema import ActionType
from openhands.events.action.action import Action, ActionSecurityRisk


@dataclass
class TerminusStartAction(Action):
    """Starts a persistent interactive terminal session.

    Features:
    - Creates a new terminal session with unique session ID
    - Maintains environment variables and working directory between commands
    - Supports custom shell configuration
    - Automatic cleanup on session end

    Attributes:
        session_id: Optional unique identifier for the session. Auto-generated if not provided.
        shell: Shell to use (e.g., 'bash', 'sh', 'zsh'). Defaults to 'bash'.
        cwd: Working directory for the session. Defaults to current directory.
        env: Environment variables to set for the session.
    """

    session_id: str = ""
    shell: str = "bash"
    cwd: str = "."
    env: dict[str, str] | None = None
    thought: str = ""
    action: str = ActionType.TERMINUS_START
    runnable: ClassVar[bool] = True
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN

    @property
    def message(self) -> str:
        if self.session_id:
            return f"Starting terminal session: {self.session_id}"
        return "Starting new terminal session"


@dataclass
class TerminusExecuteAction(Action):
    """Executes a command in an existing terminal session.

    Features:
    - Executes commands in persistent shell environment
    - Captures stdout, stderr, and exit code
    - Supports command timeout
    - Handles interactive processes

    Attributes:
        session_id: ID of the session to execute the command in. Required.
        command: The command to execute in the terminal session.
        timeout: Command timeout in seconds. Defaults to 30.
        capture_output: Whether to capture and return output. Defaults to True.
    """

    session_id: str
    command: str
    timeout: int = 30
    capture_output: bool = True
    thought: str = ""
    action: str = ActionType.TERMINUS_EXECUTE
    runnable: ClassVar[bool] = True
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN

    @property
    def message(self) -> str:
        cmd_preview = self.command[:50] + "..." if len(self.command) > 50 else self.command
        return f"Executing in session {self.session_id}: {cmd_preview}"


@dataclass
class TerminusInputAction(Action):
    """Sends input to a running process in the terminal session.

    Features:
    - Send text input to process stdin
    - Send control sequences (Ctrl+C, Ctrl+D, etc.)
    - Retrieve additional output from running processes
    - Non-blocking input operations

    Attributes:
        session_id: ID of the session with the running process. Required.
        input_text: Text to send to the process stdin. Empty string retrieves output without sending input.
        is_control: Whether the input is a control sequence (e.g., 'C-c', 'C-d'). Defaults to False.
    """

    session_id: str
    input_text: str = ""
    is_control: bool = False
    thought: str = ""
    action: str = ActionType.TERMINUS_INPUT
    runnable: ClassVar[bool] = True
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN

    @property
    def message(self) -> str:
        if self.is_control:
            return f"Sending control sequence to session {self.session_id}: {self.input_text}"
        elif self.input_text:
            preview = self.input_text[:30] + "..." if len(self.input_text) > 30 else self.input_text
            return f"Sending input to session {self.session_id}: {preview}"
        return f"Retrieving output from session {self.session_id}"


@dataclass
class TerminusStopAction(Action):
    """Stops and cleans up a terminal session.

    Features:
    - Gracefully terminates running processes
    - Cleans up session resources
    - Optional force kill for stuck processes

    Attributes:
        session_id: ID of the session to stop. Required.
        force: Whether to force kill the session. Defaults to False.
    """

    session_id: str
    force: bool = False
    thought: str = ""
    action: str = ActionType.TERMINUS_STOP
    runnable: ClassVar[bool] = True
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN

    @property
    def message(self) -> str:
        force_text = " (forced)" if self.force else ""
        return f"Stopping terminal session: {self.session_id}{force_text}"
