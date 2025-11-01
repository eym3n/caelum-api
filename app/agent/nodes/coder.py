from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


from app.agent.prompts import CODER_SYSTEM_PROMPT
from app.agent.state import BuilderState

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

from app.agent.tools.commands import (
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    lint_project,
    run_npx_command,
    run_git_command,
    git_log,
    git_show,
    check_css,
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
    run_npx_command,
    lint_project,
    run_git_command,
    git_log,
    git_show,
    check_css,
]

_coder_llm_ = ChatGoogleGenerativeAI(model="gemini-2.5-flash").bind_tools(tools)


def coder(state: BuilderState) -> BuilderState:
    TODO_LIST = getattr(state, "planner_output", [])
    guidelines = state.design_guidelines.strip() if state.design_guidelines else ""
    guidelines_section = (
        "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n" + guidelines
        if guidelines
        else "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n- Design system guidelines not yet available. Coordinate with the design agent output or maintain neutral styling."
    )

    blueprint = (
        state.architecture_blueprint.strip() if state.architecture_blueprint else ""
    )
    blueprint_section = (
        "\n\nCURRENT ARCHITECTURE BLUEPRINT:\n" + blueprint
        if blueprint
        else "\n\nCURRENT ARCHITECTURE BLUEPRINT:\n- Architecture blueprint not yet available. Coordinate with the architect agent output or confirm structure with the planner."
    )

    SYS = SystemMessage(
        content=CODER_SYSTEM_PROMPT
        + guidelines_section
        + blueprint_section
        + f"\n\nTODO List: {TODO_LIST}"
    )
    messages = [SYS, *state.messages]
    coder_response = _coder_llm_.invoke(messages)

    print(f"[CODER] {coder_response}")

    # Check for malformed function call
    finish_reason = getattr(coder_response, "response_metadata", {}).get(
        "finish_reason"
    )
    if finish_reason == "MALFORMED_FUNCTION_CALL":
        print(
            "[CODER] ⚠️  Malformed function call detected. Retrying with a simpler prompt..."
        )
        # Retry with a recovery message
        recovery_msg = HumanMessage(
            content="The previous request had an error. Please respond with a clear text explanation of what you were trying to do, without making tool calls. Then I'll help you make the correct tool calls."
        )
        messages.append(coder_response)
        messages.append(recovery_msg)
        coder_response = _coder_llm_.invoke(messages)
        print(f"[CODER] Retry response: {coder_response}")

    # Extract content as string (handle both str and list responses)
    output = ""
    if isinstance(coder_response.content, str):
        output = coder_response.content.strip()
    elif isinstance(coder_response.content, list):
        output = "\n".join(
            (
                str(segment.get("text", segment))
                if isinstance(segment, dict)
                else str(segment)
            )
            for segment in coder_response.content
            if segment
        ).strip()

    if not output:
        output = "Coder response completed. Refer to tool calls or message content."

    return {"messages": [coder_response], "coder_output": output}
