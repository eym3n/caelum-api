"""Fix Errors node - specialized LLM for resolving lint/type failures."""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.agent.prompts.fix_errors import FIX_ERRORS_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.files import (
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    list_files,
    list_files_internal,
)
from app.agent.tools.commands import lint_project
from app.utils.jobs import log_job_event

load_dotenv()

tools = [
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    list_files,
    lint_project,
]


def fix_errors(state: BuilderState) -> BuilderState:
    """Specialized node dedicated to fixing lint/type errors surfaced by linting."""
    response = None
    try:
        print("\n\n[FIX_ERRORS] 🧹 Starting lint/type error remediation...")

        session_id = state.session_id
        job_id = getattr(state, "job_id", None)
        lint_output = state.lint_output or "No lint output available."
        read_only_attempts = getattr(state, "fix_errors_read_only_attempts", 0)

        if job_id:
            log_job_event(
                job_id,
                node="fix_errors",
                message="Analyzing lint failures...",
                event_type="node_started",
                data={
                    "session_id": session_id,
                    "lint_excerpt": lint_output[:200],
                },
            )

        print(f"[FIX_ERRORS] Session: {session_id}")
        print(f"[FIX_ERRORS] Lint output snippet:\n{lint_output[:200]}...")

        files = "\n".join(list_files_internal(session_id))
        prompt_with_context = FIX_ERRORS_PROMPT.format(
            lint_output=lint_output, files_list=files
        )
        if read_only_attempts >= 2:
            prompt_with_context += (
                "\n\n⛔ STOP RE-READING FILES. You already inspected the sources. "
                "Apply the fixes now using batch_update_files, batch_update_lines, "
                "or batch_create_files, then run lint_project. Reading again without edits is not allowed."
            )

        fix_errors_llm = ChatOpenAI(
            model="gpt-5", reasoning_effort="medium"
        ).bind_tools(tools, parallel_tool_calls=True)

        system_message = SystemMessage(content=prompt_with_context)
        messages = [system_message, *state.messages]

        print("[FIX_ERRORS] Reviewing lint output and determining fixes...")
        response = fix_errors_llm.invoke(messages)

        print(f"\n\n[FIX_ERRORS] Response: {response}")

        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            num_calls = len(tool_calls)
            print(
                f"[FIX_ERRORS] Executing {num_calls} automated fix(es) for lint issues"
            )

            normalized_calls: list[str] = []
            for call in tool_calls:
                name = getattr(call, "name", None) or getattr(call, "tool_name", None)
                if not name and isinstance(call, dict):
                    name = call.get("name")
                normalized = (name or "").split(".")[-1]
                if normalized.startswith("designer_"):
                    normalized = normalized[len("designer_") :]
                normalized_calls.append(normalized)

            read_only_tools = {"batch_read_files", "list_files"}
            write_tools = {
                "batch_update_files",
                "batch_update_lines",
                "batch_create_files",
                "batch_delete_files",
                "lint_project",
            }
            contains_write = any(tool in write_tools for tool in normalized_calls)
            read_only = (
                not contains_write
                and normalized_calls
                and all(tool in read_only_tools for tool in normalized_calls)
            )
            next_attempts = read_only_attempts + 1 if read_only else 0

            if job_id:
                log_job_event(
                    job_id,
                    node="fix_errors",
                    message=f"Applying {num_calls} automated fix{'es' if num_calls != 1 else ''} for lint errors.",
                    event_type="node",
                    data={"tool_calls": num_calls},
                )
            return {
                "messages": [response],
                "fix_errors_run": True,
                "lint_failed": True,
                "fix_errors_read_only_attempts": next_attempts,
            }

        output = ""
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

        if not output:
            output = "Lint error analysis completed."

        print(f"[FIX_ERRORS] {output}")

        if job_id:
            log_job_event(
                job_id,
                node="fix_errors",
                message=output,
                event_type="node_completed",
            )

        return {
            "messages": [response],
            "fix_errors_run": True,
            "fix_errors_read_only_attempts": 0,
        }
    except Exception as exc:
        print(f"[FIX_ERRORS] Error: {exc}")
        if job_id:
            log_job_event(
                job_id,
                node="fix_errors",
                message="Fix errors node encountered an exception.",
                event_type="error",
                data={"error": str(exc)},
            )
        return {
            "messages": [response] if response is not None else state.messages,
            "fix_errors_run": True,
            "lint_failed": True,
            "lint_output": lint_output if "lint_output" in locals() else "",
            "fix_errors_read_only_attempts": read_only_attempts,
        }
