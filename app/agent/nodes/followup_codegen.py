from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from toon import encode

from app.agent.prompts.coder import FOLLOWUP_CODER_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.files import (
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    list_files_internal,
)
from app.agent.tools.commands import lint_project
from app.utils.jobs import log_job_event


FOLLOWUP_TOOLS = [
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    lint_project,
]


def followup_codegen(state: BuilderState) -> BuilderState:
    """LLM node that handles follow-up coding requests with full tool access."""

    log_job_event(
        state.job_id,
        node="followup_codegen",
        message="Applying follow-up code updates...",
        event_type="node_started",
    )

    design_guidelines = state.design_guidelines or {}
    design_context = (
        encode(design_guidelines)
        if design_guidelines and state.design_planner_run
        else "Design blueprint not available in structured form."
    )
    init_payload_text = state.init_payload_text or "No initialization payload captured."

    files_snapshot = "\n".join(list_files_internal(state.session_id))

    system_content = (
        FOLLOWUP_CODER_SYSTEM_PROMPT.strip()
        + "\n\n### Design Guidelines (JSON encoded)\n"
        + design_context
        + "\n\n### Initialization Payload (flattened)\n"
        + init_payload_text
        + f"\n\n**********Current session file tree**********\n{files_snapshot}\n**********************************************"
    )

    system_message = SystemMessage(content=system_content)
    messages = [system_message, *state.messages]

    llm = ChatGoogleGenerativeAI(
        model="models/gemini-3-pro-preview", temperature=0.1
    ).bind_tools(FOLLOWUP_TOOLS, parallel_tool_calls=True)

    response = llm.invoke(messages)

    # If the LLM requests tool calls, hand control to the tool execution node
    if getattr(response, "tool_calls", None):
        print(
            f"[FOLLOWUP_CODEGEN] Dispatching {len(response.tool_calls)} tool call(s) for follow-up work."
        )
        return {
            "messages": [response],
        }

    # Aggregate textual output for logging
    if isinstance(response.content, str):
        output = response.content.strip()
    elif isinstance(response.content, list):
        output = "\n".join(
            (
                str(segment.get("text", segment))
                if isinstance(segment, dict)
                else str(segment)
            )
            for segment in response.content
            if segment
        ).strip()
    else:
        output = "Follow-up coding task completed."

    if not output:
        output = "Follow-up coding task completed."

    log_job_event(
        state.job_id,
        node="followup_codegen",
        message=output,
        event_type="node_completed",
    )

    print(f"[FOLLOWUP_CODEGEN] {output}")

    return {
        "messages": [response],
    }

