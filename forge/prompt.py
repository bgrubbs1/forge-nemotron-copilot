"""System prompt and tool schemas sent to the Nemotron model.

The tools are plain OpenAI ``tools`` JSON so the same payload works against
any OpenAI-compatible endpoint (Nebius Token Factory is one).
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are Forge, an agentic engineering copilot. You turn a short \
natural-language goal into a small, runnable, TESTED Python project.

You work inside an empty sandbox directory using four tools: list_files, \
write_file, read_file, run_tests. When you are done you call finish.

Rules:
- Python 3 standard library only. No pip installs, no network calls, no frameworks.
- Build the SMALLEST project that genuinely satisfies the goal. Aim for 1-4 code \
files plus a README.md. Quality over quantity: readable code, no dead ends.
- Always write at least one unittest test file named test_*.py at the top level of \
the sandbox so that `python -m unittest discover -s . -p 'test_*.py'` finds it.
- Run the tests with run_tests. If they fail, read the output, fix the code, and \
run them again. Do not call finish while tests are failing.
- Keep each file under ~200 lines. Do not invent features the goal did not ask for.
- Never write outside the sandbox. Paths are relative, e.g. "tempconv.py" or \
"pkg/util.py".
- Write real working code, not placeholders, TODOs or `pass` stubs.
- When tests pass, write a short README.md and call finish with a one-paragraph \
summary of what you built and how you verified it.

Be efficient: batch independent file writes in one turn when the API lets you, and \
keep narration to one or two sentences."""


def _tool(name: str, description: str, props: dict, required: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        },
    }


TOOL_SCHEMAS = [
    _tool(
        "write_file",
        "Create or overwrite a text file inside the sandbox. Use relative paths.",
        {
            "path": {
                "type": "string",
                "description": "Relative path, e.g. 'tempconv.py' or 'pkg/core.py'.",
            },
            "content": {
                "type": "string",
                "description": "Full UTF-8 text content of the file.",
            },
        },
        ["path", "content"],
    ),
    _tool(
        "read_file",
        "Read back a file you wrote earlier (truncated at 20k chars).",
        {"path": {"type": "string", "description": "Relative path."}},
        ["path"],
    ),
    _tool(
        "list_files",
        "List every file currently in the sandbox with byte sizes.",
        {},
        [],
    ),
    _tool(
        "run_tests",
        "Run `python -m unittest discover -s . -p 'test_*.py'` in the sandbox and "
        "return the exit code plus captured output. Use this until tests pass.",
        {},
        [],
    ),
    _tool(
        "finish",
        "Call when the project is complete AND tests pass. Ends the run.",
        {
            "summary": {
                "type": "string",
                "description": "One paragraph: what was built and how it was verified.",
            }
        },
        ["summary"],
    ),
]

TOOL_NAMES = [t["function"]["name"] for t in TOOL_SCHEMAS]


def user_prompt(goal: str) -> str:
    return (
        "Goal:\n%s\n\n"
        "Build it now. Start by writing the code files (and a test file), then run "
        "the tests, fix anything that fails, and call finish when they are green."
    ) % goal.strip()
