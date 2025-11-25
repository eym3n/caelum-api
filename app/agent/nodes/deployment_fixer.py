"""Deployment Fixer node - specialized LLM for fixing deployment errors."""

from __future__ import annotations
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.agent.prompts.deployment_fixer import DEPLOYMENT_FIXER_PROMPT
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
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
    list_files,
]


def deployment_fixer(state: BuilderState) -> BuilderState:
    """
    Specialized node for fixing deployment errors.

    Focuses exclusively on analyzing deployment failures and making
    targeted fixes to resolve the issues.
    """
    response = None  # ensure defined for exception handling
    try:
        print("\n\n[DEPLOYMENT_FIXER] 🔧 Starting deployment error analysis...")

        session_id = state.session_id
        job_id = getattr(state, "job_id", None)
        deployment_error = state.deployment_error or "No error details available"
        read_only_attempts = state.deployment_fixer_read_only_attempts

        if job_id:
            log_job_event(
                job_id,
                node="deployment_fixer",
                message="Analyzing deployment failure...",
                event_type="node_started",
                data={
                    "session_id": session_id,
                    "error_excerpt": deployment_error[:200],
                    "read_only_attempts": read_only_attempts,
                },
            )

        print(f"[DEPLOYMENT_FIXER] Session: {session_id}")
        print(f"[DEPLOYMENT_FIXER] Read-only attempts so far: {read_only_attempts}")
        print(f"[DEPLOYMENT_FIXER] Error:\n{deployment_error[:200]}...")

        # Get list of files
        files = "\n".join(list_files_internal(session_id))

        # Build specialized prompt with error context
        prompt_with_context = DEPLOYMENT_FIXER_PROMPT.format(
            deployment_error=deployment_error, files_list=files
        )

        # Add escalation warning if agent keeps reading without fixing
        if read_only_attempts >= 2:
            prompt_with_context += (
                "\n\n🚨 CRITICAL WARNING: You have read files multiple times without applying any fixes. "
                "This is NOT acceptable. Your NEXT action MUST be to use batch_update_files, batch_update_lines, "
                "or batch_create_files to actually fix the deployment error. Reading more files is FORBIDDEN until "
                "you make a concrete code change. If you do not apply a fix NOW, the deployment will remain broken."
            )

        # Use GPT-5 with minimal reasoning for fast, focused fixes
        _deployment_fixer_llm_ = ChatOpenAI(model="gpt-4.1").bind_tools(
            tools,
            parallel_tool_calls=True,
        )

        SYS = SystemMessage(content=prompt_with_context)
        messages = [SYS, *state.messages]

        print("[DEPLOYMENT_FIXER] Analyzing deployment error and determining fixes...")
        response = _deployment_fixer_llm_.invoke(messages)

        print(f"\n\n[DEPLOYMENT_FIXER] Response: {response}")

        # Check if there are tool calls
        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            num_calls = len(tool_calls)
            print(
                f"[DEPLOYMENT_FIXER] Making {num_calls} fix(es) to resolve deployment error"
            )

            # Check if agent is only reading files (no write operations)
            write_tools = {
                "batch_create_files",
                "batch_update_files",
                "batch_delete_files",
                "batch_update_lines",
            }
            read_tools = {"batch_read_files", "list_files"}

            tool_names = {tc.get("name") for tc in tool_calls}
            has_write = bool(tool_names & write_tools)
            only_read = bool(tool_names & read_tools) and not has_write

            new_read_only_count = read_only_attempts + 1 if only_read else 0

            if only_read:
                print(
                    f"[DEPLOYMENT_FIXER] WARNING: Agent is only reading files (attempt {new_read_only_count}). No fixes applied yet."
                )
            else:
                print(
                    f"[DEPLOYMENT_FIXER] Agent is applying actual fixes. Resetting read-only counter."
                )

            if job_id:
                log_job_event(
                    job_id,
                    node="deployment_fixer",
                    message=f"Applying {num_calls} automated fix{'es' if num_calls != 1 else ''} for deployment failure.",
                    event_type="node",
                    data={
                        "tool_calls": num_calls,
                        "has_write_operations": has_write,
                        "read_only_attempts": new_read_only_count,
                    },
                )
            return {
                "messages": [response],
                "deployment_fixer_run": True,
                "deployment_fixer_read_only_attempts": new_read_only_count,
                # Keep deployment error info for context but mark as being fixed
                "deployment_failed": True,  # Still failed, but fixing
            }

        # If no tool calls, extract explanation
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
            output = "Deployment error analysis completed."

        print(f"[DEPLOYMENT_FIXER] {output}")

        if job_id:
            log_job_event(
                job_id,
                node="deployment_fixer",
                message=output,
                event_type="node_completed",
            )

        return {
            "messages": [response],
            "deployment_fixer_run": True,
        }
    except Exception as e:
        print(f"[DEPLOYMENT_FIXER] Error: {e}")
        if job_id:
            log_job_event(
                job_id,
                node="deployment_fixer",
                message="Deployment fixer encountered an exception.",
                event_type="error",
                data={"error": str(e)},
            )
        return {
            "messages": [response] if response is not None else state.messages,
            "deployment_fixer_run": True,
            "deployment_failed": True,
            "deployment_error": str(e),
        }
