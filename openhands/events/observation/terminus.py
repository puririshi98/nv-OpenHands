"""Terminus observation classes for interactive terminal session results."""

from dataclasses import dataclass, field

from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation


@dataclass
class TerminusOutputObservation(Observation):
    """Result of a terminal command execution or process output.

    Contains the output (stdout/stderr), exit code, and timing information
    from executing a command or retrieving output from a running process.

    Attributes:
        session_id: ID of the terminal session that produced this output.
        stdout: Standard output from the command/process.
        stderr: Standard error from the command/process.
        exit_code: Exit code of the command. None if process still running.
        command: The command that was executed (for reference).
        timeout_reached: Whether the command hit a timeout.
    """

    session_id: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    command: str = ""
    timeout_reached: bool = False
    observation: str = ObservationType.TERMINUS_OUTPUT

    @property
    def message(self) -> str:
        """Returns a formatted message with command output."""
        lines = []

        if self.command:
            lines.append(f"[Session {self.session_id}] Executed: {self.command}")

        if self.stdout:
            lines.append("stdout:")
            lines.append(self.stdout)

        if self.stderr:
            lines.append("stderr:")
            lines.append(self.stderr)

        if self.exit_code is not None:
            lines.append(f"Exit code: {self.exit_code}")
        elif self.timeout_reached:
            lines.append("Status: Timeout reached (process still running)")
        else:
            lines.append("Status: Process running")

        return "\n".join(lines)

    @property
    def error(self) -> bool:
        """Returns True if the command failed (non-zero exit code)."""
        return self.exit_code is not None and self.exit_code != 0


@dataclass
class TerminusErrorObservation(Observation):
    """Error from a terminal session operation.

    Represents errors that occur during session management or command execution,
    such as session not found, permission denied, or other runtime errors.

    Attributes:
        session_id: ID of the terminal session where the error occurred.
        error_message: Descriptive error message.
        error_type: Type/category of the error (e.g., 'SessionNotFound', 'PermissionDenied').
    """

    session_id: str = ""
    error_message: str = ""
    error_type: str = "UnknownError"
    observation: str = ObservationType.TERMINUS_ERROR

    @property
    def message(self) -> str:
        """Returns a formatted error message."""
        if self.session_id:
            return f"[Session {self.session_id}] Error ({self.error_type}): {self.error_message}"
        return f"Error ({self.error_type}): {self.error_message}"

    @property
    def error(self) -> bool:
        """Always returns True as this is an error observation."""
        return True


@dataclass
class TerminusSessionObservation(Observation):
    """Status information about a terminal session.

    Provides information about session state, such as creation confirmation,
    active processes, current working directory, and environment.

    Attributes:
        session_id: ID of the terminal session.
        status: Session status (e.g., 'started', 'running', 'stopped').
        cwd: Current working directory in the session.
        shell: Shell being used in the session.
        env_vars: Important environment variables in the session.
        active_process: Whether a process is currently running in the session.
        process_info: Information about the running process (if any).
    """

    session_id: str = ""
    status: str = "unknown"
    cwd: str = ""
    shell: str = ""
    env_vars: dict[str, str] = field(default_factory=dict)
    active_process: bool = False
    process_info: str = ""
    observation: str = ObservationType.TERMINUS_SESSION

    @property
    def message(self) -> str:
        """Returns a formatted status message."""
        lines = [f"Session {self.session_id}: {self.status}"]

        if self.shell:
            lines.append(f"Shell: {self.shell}")

        if self.cwd:
            lines.append(f"Working directory: {self.cwd}")

        if self.active_process:
            lines.append(f"Active process: {self.process_info or 'running'}")

        if self.env_vars:
            lines.append(f"Environment: {len(self.env_vars)} variables set")

        return "\n".join(lines)

    @property
    def error(self) -> bool:
        """Returns False as this is a status observation, not an error."""
        return False
