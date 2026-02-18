from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from openhands.llm.tool_names import TERMINUS_STOP_TOOL_NAME

_TERMINUS_STOP_DESCRIPTION = """Stops and cleans up a terminal session.

This will:
- Terminate any running processes in the session
- Clean up session resources
- Free the session ID for reuse

Use force=true if a process is stuck and won't terminate gracefully."""

TerminusStopTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name=TERMINUS_STOP_TOOL_NAME,
        description=_TERMINUS_STOP_DESCRIPTION,
        parameters={
            'type': 'object',
            'required': ['session_id'],
            'properties': {
                'session_id': {
                    'type': 'string',
                    'description': 'ID of the session to stop. Required.',
                },
                'force': {
                    'type': 'boolean',
                    'description': 'Whether to force kill the session. Defaults to false.',
                },
            },
            'additionalProperties': False,
        },
    ),
)
