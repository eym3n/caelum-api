from __future__ import annotations

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.prompts import DESIGNER_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.commands import (
    init_nextjs_app,
    install_dependencies,
    lint_project,
    run_dev_server,
    run_npm_command,
)
from app.agent.tools.files import (
    create_file,
    delete_file,
    insert_lines,
    list_files,
    read_file,
    read_lines,
    remove_lines,
    update_file,
    update_lines,
)

load_dotenv()

tools = [
    # File tools
    list_files,
    read_file,
    read_lines,
    create_file,
    update_file,
    delete_file,
    remove_lines,
    insert_lines,
    update_lines,
    # Command tools
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    lint_project,
]

_designer_llm_ = ChatOpenAI(model="gpt-5", reasoning_effort="medium").bind_tools(tools)


def designer(state: BuilderState) -> BuilderState:
    if state.design_system_run:
        print("[DESIGNER] Design system already established — skipping")
        return {}

    SYS = SystemMessage(content=DESIGNER_SYSTEM_PROMPT)
    messages = [SYS, *state.messages]
    designer_response = _designer_llm_.invoke(messages)

    print(
        f"[DESIGNER] Response has tool_calls: {bool(getattr(designer_response, 'tool_calls', []))}"
    )

    if getattr(designer_response, "tool_calls", None):
        print(
            f"[DESIGNER] Calling {len(designer_response.tool_calls)} tool(s) to establish design system"
        )
        return {"messages": [designer_response]}

    guidelines = ""
    if isinstance(designer_response.content, str):
        guidelines = designer_response.content.strip()
    elif isinstance(designer_response.content, list):
        guidelines = "\n".join(str(part) for part in designer_response.content if part)

    if not guidelines:
        guidelines = "Design system established. Refer to generated files for details."

    print("[DESIGNER] Design system established and guidelines stored in state")

    return {
        "messages": [designer_response],
        "design_guidelines": guidelines,
        "design_system_run": True,
    }
