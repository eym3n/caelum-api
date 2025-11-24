from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.agent.state import BuilderState
from app.agent.tools.files import (
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    list_files,
)
from app.agent.tools.commands import lint_project
from app.agent.prompts.fix_errors import FIX_ERRORS_PROMPT
from app.utils.jobs import log_job_event


def fix_errors(state: BuilderState) -> BuilderState:
    log_job_event(
        state.job_id,
        node="fix_errors",
        message="Fixing lint errors...",
        event_type="node_started",
    )

    lint_output = state.lint_output or "No lint output available."

    files = batch_read_files.invoke
    tools = [
        batch_read_files,
        batch_create_files,
        batch_update_files,
        batch_delete_files,
        batch_update_lines,
        list_files,
        lint_project,
    ]

    llm = ChatOpenAI(model="gpt-5", reasoning_effort="medium").bind_tools(
        tools, parallel_tool_calls=True
    )

    system = SystemMessage(
        content=FIX_ERRORS_PROMPT.format(
            lint_output=lint_output, files_list=list_files.invoke({})
        ).strip()
    )
    human = HumanMessage(
        content="Follow the lint output above. Read relevant files, apply fixes, and rerun lint. Summarize the resolved issues when done."
    )

    messages = [system, human, *state.messages]

    response = llm.invoke([system, human])

    if getattr(response, "tool_calls", None):
        return {
            "messages": [response],
            "fix_errors_run": True,
        }

    summary = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    log_job_event(
        state.job_id,
        node="fix_errors",
        message=summary or "Resolved lint issues.",
        event_type="node_completed",
    )

    return {
        "messages": [response],
        "fix_errors_run": True,
    }
