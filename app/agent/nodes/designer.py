from __future__ import annotations
import random

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.agent.prompts.designer import (
    DESIGNER_SYSTEM_PROMPT,
    FOLLOWUP_DESIGNER_SYSTEM_PROMPT,
    SUMMARIZE_DESIGNER_SYSTEM_PROMPT,
)
from app.agent.state import BuilderState
from app.agent.tools.commands import lint_project
from toon import encode
from app.utils.jobs import log_job_event
from app.agent.tools.files import (
    # Batch operations
    batch_read_files,
    designer_batch_create_files,
    designer_batch_update_files,
    designer_batch_update_lines,
    # Utility
    list_files_internal,
    read_file,
    read_lines,
)

load_dotenv()

# LLM
tools = [
    # Batch file operations (ONLY USE THESE FOR FILES)
    batch_read_files,
    designer_batch_create_files,
    designer_batch_update_files,
    designer_batch_update_lines,
    # Utility
    read_file,
    read_lines,
    # Command tools
    lint_project,
]


_designer_llm_ = ChatOpenAI(model="gpt-5", reasoning_effort="low").bind_tools(tools)


def designer(state: BuilderState) -> BuilderState:
    # Check if we have design_guidelines from design_planner
    design_guidelines = state.design_guidelines
    has_guidelines = bool(design_guidelines and state.design_planner_run)

    files = "\n".join(list_files_internal(state.session_id))

    if has_guidelines:
        # Use simplified implementation prompt with guidelines

        guidelines = encode(design_guidelines)
        prompt = DESIGNER_SYSTEM_PROMPT.replace("**_guidelines_**", guidelines)

        SYS = SystemMessage(content=prompt)
    elif getattr(state, "is_followup", False):
        prompt = FOLLOWUP_DESIGNER_SYSTEM_PROMPT
        SYS = SystemMessage(
            content=prompt + f"\n\nThe following files exist in the session: {files}"
        )
    elif (
        "globals.css" in files
        and "tailwind.config.ts" in files
        and "layout.tsx" in files
    ):
        prompt = SUMMARIZE_DESIGNER_SYSTEM_PROMPT
        print("[DESIGNER] Summarizing design system")
        SYS = SystemMessage(content=prompt)
    else:
        SYS = SystemMessage(
            content=prompt + f"\n\nThe following files exist in the session: {files}"
        )

    messages = [SYS, *state.messages] if not state.design_system_run else state.messages
    designer_response = _designer_llm_.invoke(messages)

    print(f"[DESIGNER] Response: {designer_response}")

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
        return {"messages": [designer_response], "design_system_run": True}

    # Log final designer guidelines as a node-level job event
    log_job_event(
        state.job_id,
        node="designer",
        message="Designer completed design system pass.",
        event_type="node_completed",
    )

    return {
        "messages": [designer_response],
        "design_system_run": True,
    }
