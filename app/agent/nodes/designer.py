from __future__ import annotations

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
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
    # Batch operations (ONLY USE THESE)
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
    list_files,
)

load_dotenv()

tools = [
    # Batch file operations (ONLY USE THESE FOR FILES)
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
    list_files,
    # Command tools
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    lint_project,
]

_designer_llm_ = ChatGoogleGenerativeAI(model="gemini-2.5-flash").bind_tools(tools)


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

    # Check for malformed function call
    finish_reason = getattr(designer_response, "response_metadata", {}).get(
        "finish_reason"
    )
    if finish_reason == "MALFORMED_FUNCTION_CALL":
        print(
            "[DESIGNER] ⚠️  Malformed function call detected. Retrying with a simpler prompt..."
        )
        recovery_msg = HumanMessage(
            content="The previous request had an error. Please respond with a clear text explanation of the design system without making tool calls."
        )
        messages.append(designer_response)
        messages.append(recovery_msg)
        designer_response = _designer_llm_.invoke(messages)
        print(f"[DESIGNER] Retry response: {designer_response}")

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

    print(f"[DESIGNER] guidelines: {guidelines}")

    return {
        "messages": [designer_response],
        "design_guidelines": guidelines,
        "design_system_run": True,
    }
