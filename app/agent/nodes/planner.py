from __future__ import annotations
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.prompts import PLANNER_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.files import list_files, read_file, read_lines

load_dotenv()

tools = [list_files, read_file, read_lines]

_planner_llm_ = ChatGoogleGenerativeAI(model="gemini-2.5-flash").bind_tools(tools)


def planner(state: BuilderState) -> BuilderState:
    guidelines = state.design_guidelines.strip() if state.design_guidelines else ""
    guidelines_section = (
        "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n" + guidelines
        if guidelines
        else "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n- Design system guidelines not yet available. Coordinate with the design agent or use a neutral Tailwind baseline until they are provided."
    )

    blueprint = (
        state.architecture_blueprint.strip() if state.architecture_blueprint else ""
    )
    blueprint_section = (
        "\n\nCURRENT ARCHITECTURE BLUEPRINT:\n" + blueprint
        if blueprint
        else "\n\nCURRENT ARCHITECTURE BLUEPRINT:\n- Architecture blueprint not yet available. Confer with the architect agent output or draft a provisional structure before planning."
    )

    SYS = SystemMessage(
        content=PLANNER_SYSTEM_PROMPT + guidelines_section + blueprint_section
    )
    messages = [SYS, *state.messages]
    planner_response = _planner_llm_.invoke(messages)

    print(f"[PLANNER] Response has tool_calls: {bool(planner_response.tool_calls)}")

    # Check for malformed function call
    finish_reason = getattr(planner_response, "response_metadata", {}).get(
        "finish_reason"
    )
    if finish_reason == "MALFORMED_FUNCTION_CALL":
        print(
            "[PLANNER] ⚠️  Malformed function call detected. Retrying with a simpler prompt..."
        )
        recovery_msg = HumanMessage(
            content="The previous request had an error. Please respond with a clear numbered list of tasks without making tool calls."
        )
        messages.append(planner_response)
        messages.append(recovery_msg)
        planner_response = _planner_llm_.invoke(messages)
        print(f"[PLANNER] Retry response: {planner_response}")

    # If the planner wants to call tools, return early to execute them
    if planner_response.tool_calls:
        print(f"[PLANNER] Calling {len(planner_response.tool_calls)} tool(s)")
        return {"messages": [planner_response]}

    # Extract todo list from the response content
    # Handle both string and list content types
    content_str = ""
    if isinstance(planner_response.content, str):
        content_str = planner_response.content
    elif isinstance(planner_response.content, list):
        content_str = "\n".join(
            (
                str(segment.get("text", segment))
                if isinstance(segment, dict)
                else str(segment)
            )
            for segment in planner_response.content
            if segment
        )

    todo_list = []

    if content_str:
        # Parse numbered or bulleted list from content
        # Look for lines starting with numbers (1., 2., etc.) or bullets (-, *, •)
        lines = content_str.split("\n")
        for line in lines:
            line = line.strip()
            # Match patterns like "1. Task", "- Task", "* Task", "• Task"
            match = re.match(r"^(?:\d+\.|\-|\*|•)\s+(.+)$", line)
            if match:
                todo_list.append(match.group(1))

    # If no todo items found, use the full content as a single item
    if not todo_list and content_str:
        todo_list = [content_str]

    print(f"[PLANNER] Extracted {len(todo_list)} todo items: {todo_list}")

    return {"messages": [planner_response], "planner_output": todo_list}
