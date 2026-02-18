from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from openhands.llm.tool_names import TERMINUS_INPUT_TOOL_NAME

_TERMINUS_INPUT_DESCRIPTION = """Sends input to a running process in the terminal session.

Use this tool to:
- Send text input to process stdin (e.g., responding to prompts)
- Send control sequences (e.g., 'C-c' for Ctrl+C, 'C-d' for Ctrl+D)
- Retrieve additional output from running processes (send empty string)

This is particularly useful for interactive programs like:
- Python/Ruby/Node REPLs
- Debuggers (gdb, pdb, etc.)
- Interactive CLIs (psql, mysql, etc.)
- Programs waiting for user input"""

TerminusInputTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name=TERMINUS_INPUT_TOOL_NAME,
        description=_TERMINUS_INPUT_DESCRIPTION,
        parameters={
            'type': 'object',
            'required': ['session_id'],
            'properties': {
                'session_id': {
                    'type': 'string',
                    'description': 'ID of the session with the running process. Required.',
                },
                'input_text': {
                    'type': 'string',
                    'description': 'Text to send to the process stdin. Empty string retrieves output without sending input.',
                },
                'is_control': {
                    'type': 'boolean',
                    'description': 'Whether the input is a control sequence (e.g., "C-c", "C-d"). Defaults to false.',
                },
            },
            'additionalProperties': False,
        },
    ),
)
