from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from openhands.llm.tool_names import TERMINUS_EXECUTE_TOOL_NAME

_TERMINUS_EXECUTE_DESCRIPTION = """Executes a command in an existing terminal session.

The command runs in the session's persistent environment, maintaining:
- Environment variables from previous commands
- Current working directory
- Shell state and history

For long-running commands, the command will timeout after the specified duration.
For interactive processes, use terminus_input to send input after starting."""

TerminusExecuteTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name=TERMINUS_EXECUTE_TOOL_NAME,
        description=_TERMINUS_EXECUTE_DESCRIPTION,
        parameters={
            'type': 'object',
            'required': ['session_id', 'command'],
            'properties': {
                'session_id': {
                    'type': 'string',
                    'description': 'ID of the session to execute the command in. Required.',
                },
                'command': {
                    'type': 'string',
                    'description': 'The command to execute in the terminal session.',
                },
                'timeout': {
                    'type': 'integer',
                    'description': 'Command timeout in seconds. Defaults to 30.',
                },
                'capture_output': {
                    'type': 'boolean',
                    'description': 'Whether to capture and return output. Defaults to true.',
                },
            },
            'additionalProperties': False,
        },
    ),
)
