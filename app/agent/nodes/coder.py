from __future__ import annotations
from errno import EL2HLT
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from toon import encode


from app.agent.prompts.coder import (
    CODER_DESIGN_BOOSTER,
    CODER_SYSTEM_PROMPT,
    FOLLOWUP_CODER_SYSTEM_PROMPT,
)
from app.agent.state import BuilderState

from app.agent.tools.files import (
    # Batch operations (ONLY USE THESE)
    batch_read_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Single-file creation
    create_file,
    # Utility
    list_files_internal,
)

from app.agent.tools.commands import (
    lint_project,
)
from app.utils.jobs import log_job_event

load_dotenv()

tools = [
    # Batch file operations (ONLY USE THESE FOR FILES)
    batch_read_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    create_file,
    # Command tools
    lint_project,
]


def coder(state: BuilderState) -> BuilderState:
    # Gather all design fields from state for coder prompt context

    if not state.coder_run and not state.is_followup:
        print("[CODER] Using first-hit non-followup prompt")
        log_job_event(
            state.job_id,
            node="coder",
            message="Creating landing page...",
            event_type="node_started",
        )

    elif state.is_followup and not state.coder_run:
        print("[CODER] Using first-hit follow-up prompt")
        log_job_event(
            state.job_id,
            node="coder",
            message="Updating landing page...",
            event_type="node_started",
        )

    print("\n\n[CODER] Follow-up condition met:", state.is_followup)

    _coder_prompt = (
        CODER_SYSTEM_PROMPT if not state.is_followup else FOLLOWUP_CODER_SYSTEM_PROMPT
    )

    print(
        "\n\n[CODER] Using prompt: ",
        "DEFAULT" if not state.is_followup else "FOLLOW-UP",
    )

    _coder_llm_ = ChatGoogleGenerativeAI(
        model="models/gemini-3-pro-preview",
        thinking_budget=64,
    ).bind_tools(
        tools,
        parallel_tool_calls=True,
    )

    # Build design context from structured guidelines if available
    design_context_section = ""
    design_guidelines = state.design_guidelines

    if design_guidelines and state.design_planner_run:
        design_context_section = encode(design_guidelines)
    else:
        design_context_section = (
            "\n### Design blueprint missing:\n"
            "No structured design guidelines are available yet. Request the Design Planner to run before coding."
        )

    project_spec = (
        "\n### Initialization payload (for data/reference only):\n"
        + state.init_payload_text
    )

    files = "\n".join(list_files_internal(state.session_id))

    SYS = SystemMessage(
        content=_coder_prompt
        + design_context_section
        + project_spec
        + CODER_DESIGN_BOOSTER
        + f"\n\n**********The following files exist in the codebase:\n{files}\n**********"
    )
    messages = [SYS, *state.messages]

    coder_response = _coder_llm_.invoke(messages)

    print(f"\n\n[CODER] {coder_response}")

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
            content="The previous request had an error. Please retry with the correct tool calls."
        )
        messages.append(coder_response)
        messages.append(recovery_msg)
        coder_response = _coder_llm_.invoke(messages)
        print(f"[CODER] Retry response: {coder_response}")

    # Check if there are tool calls - if so, return message without output
    if getattr(coder_response, "tool_calls", None):
        print(
            f"[CODER] Calling {len(coder_response.tool_calls)} tool(s) to build/adjust sections"
        )
        return {
            "messages": [coder_response],
            "coder_run": True,
            "deployment_failed": False,
            "deployment_error": "",
            # "coder_first_pass_run": False,
        }

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
        output = "Task completed."

    # Log final coder output as a node-level job event
    log_job_event(
        state.job_id,
        node="coder",
        message=output,
        event_type="node_completed",
    )

    return {
        "messages": [coder_response],
        "coder_output": output,
        # "coder_first_pass_run": True,
    }
