from __future__ import annotations

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.prompts_new import ARCHITECT_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.files import list_files, read_file, read_lines

load_dotenv()

tools = [list_files, read_file, read_lines]

_architect_llm_ = ChatOpenAI(model="gpt-5").bind_tools(tools)


def architect(state: BuilderState) -> BuilderState:
    design_guidelines = (
        state.design_guidelines.strip() if state.design_guidelines else ""
    )
    guidelines_section = (
        "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n" + design_guidelines
        if design_guidelines
        else "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n- Design system not documented yet. Coordinate with the design agent to establish one."
    )

    previous_blueprint = (
        state.architecture_blueprint.strip() if state.architecture_blueprint else ""
    )
    previous_architecture_section = (
        "\n\nEXISTING ARCHITECTURE BLUEPRINT:\n" + previous_blueprint
        if previous_blueprint
        else "\n\nEXISTING ARCHITECTURE BLUEPRINT:\n- No prior blueprint. Produce a fresh architecture overview."
    )

    SYS = SystemMessage(
        content=ARCHITECT_SYSTEM_PROMPT
        + guidelines_section
        + previous_architecture_section
    )
    messages = [SYS, *state.messages]

    architect_response = _architect_llm_.invoke(messages)

    print(
        f"[ARCHITECT] Response has tool_calls: {bool(getattr(architect_response, 'tool_calls', []))}"
    )

    # Check for malformed function call
    finish_reason = getattr(architect_response, "response_metadata", {}).get(
        "finish_reason"
    )
    if finish_reason == "MALFORMED_FUNCTION_CALL":
        print(
            "[ARCHITECT] ⚠️  Malformed function call detected. Retrying with a simpler prompt..."
        )
        recovery_msg = HumanMessage(
            content="The previous request had an error. Please respond with a clear text explanation of the architecture without making tool calls."
        )
        messages.append(architect_response)
        messages.append(recovery_msg)
        architect_response = _architect_llm_.invoke(messages)
        print(f"[ARCHITECT] Retry response: {architect_response}")

    if getattr(architect_response, "tool_calls", None):
        print(
            f"[ARCHITECT] Calling {len(architect_response.tool_calls)} tool(s) for architectural discovery"
        )
        return {"messages": [architect_response]}

    blueprint = ""
    if isinstance(architect_response.content, str):
        blueprint = architect_response.content.strip()
    elif isinstance(architect_response.content, list):
        blueprint = "\n".join(
            str(segment) for segment in architect_response.content if segment
        ).strip()

    if not blueprint:
        blueprint = "Architecture blueprint generated. Refer to response content."

    print("[ARCHITECT] Architecture blueprint captured in state")
    print(f"[ARCHITECT] {architect_response.content}")

    return {
        "messages": [architect_response],
        "architecture_blueprint": blueprint,
        "architect_system_run": True,
        "architect_pending": False,
        "architect_output": blueprint,
    }
