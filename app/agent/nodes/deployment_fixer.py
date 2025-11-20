"""Deployment Fixer node - specialized LLM for fixing deployment errors."""

from __future__ import annotations
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
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
    lint_project,
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
        deployment_error = state.deployment_error or "No error details available"

        print(f"[DEPLOYMENT_FIXER] Session: {session_id}")
        print(f"[DEPLOYMENT_FIXER] Error:\n{deployment_error[:200]}...")

        # Get list of files
        files = "\n".join(list_files_internal(session_id))

        # Build specialized prompt with error context
        prompt_with_context = DEPLOYMENT_FIXER_PROMPT.format(
            deployment_error=deployment_error, files_list=files
        )

        # Use GPT-5 with minimal reasoning for fast, focused fixes
        _deployment_fixer_llm_ = ChatOpenAI(
            model="gpt-5", reasoning_effort="low"
        ).bind_tools(
            tools,
            parallel_tool_calls=True,
        )

        SYS = SystemMessage(content=prompt_with_context)
        messages = [SYS]

        print("[DEPLOYMENT_FIXER] Analyzing deployment error and determining fixes...")
        response = _deployment_fixer_llm_.invoke(messages)

        print(f"\n\n[DEPLOYMENT_FIXER] Response: {response}")

        # Check if there are tool calls
        if getattr(response, "tool_calls", None):
            print(
                f"[DEPLOYMENT_FIXER] Making {len(response.tool_calls)} fix(es) to resolve deployment error"
            )
            return {
                "messages": [response],
                "deployment_fixer_run": True,
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

        return {
            "messages": [response],
            "deployment_fixer_run": True,
        }
    except Exception as e:
        print(f"[DEPLOYMENT_FIXER] Error: {e}")
        return {
            "messages": [response] if response is not None else state.messages,
            "deployment_fixer_run": True,
            "deployment_failed": True,
            "deployment_error": str(e),
        }
