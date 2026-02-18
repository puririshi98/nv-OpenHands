from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from openhands.llm.tool_names import TERMINUS_START_TOOL_NAME

_TERMINUS_START_DESCRIPTION = """Starts a persistent interactive terminal session.

This creates a new terminal session that maintains state (environment variables, working directory, etc.)
across multiple commands. Use this when you need to:
- Run multiple related commands in the same environment
- Work with interactive processes (e.g., REPLs, debuggers)
- Maintain shell state between operations

Each session gets a unique session_id that you'll use for subsequent operations."""

TerminusStartTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name=TERMINUS_START_TOOL_NAME,
        description=_TERMINUS_START_DESCRIPTION,
        parameters={
            'type': 'object',
            'required': [],
            'properties': {
                'session_id': {
                    'type': 'string',
                    'description': 'Optional unique identifier for the session. Auto-generated if not provided.',
                },
                'shell': {
                    'type': 'string',
                    'description': 'Shell to use (e.g., "bash", "sh", "zsh"). Defaults to "bash".',
                },
                'cwd': {
                    'type': 'string',
                    'description': 'Working directory for the session. Defaults to current directory.',
                },
                'env': {
                    'type': 'object',
                    'description': 'Environment variables to set for the session.',
                    'additionalProperties': {'type': 'string'},
                },
            },
            'additionalProperties': False,
        },
    ),
)
