"""Deployment Fixer node - specialized LLM for fixing deployment errors."""

from __future__ import annotations
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.prompts.deployment_fixer import (
    DEPLOYMENT_FIXER_PROMPT_PASS_0,
    DEPLOYMENT_FIXER_PROMPT_PASS_1,
    DEPLOYMENT_FIXER_PROMPT_PASS_2,
)
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

from app.utils.jobs import log_job_event

load_dotenv()

# Tool sets for each pass
READ_TOOLS = [batch_read_files, list_files]
WRITE_TOOLS = [
    batch_update_lines,
    batch_update_files,
    batch_create_files,
    batch_delete_files,
]
ALL_TOOLS = [
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    list_files,
]


def deployment_fixer(state: BuilderState) -> BuilderState:
    """
    Specialized node for fixing deployment errors with a forced 3-pass workflow:

    Pass 0: Force batch_read_files to read the error files
    Pass 1: Force batch_update_lines to apply fixes
    Pass 2+: Auto mode - agent decides what to do
    """
    response = None
    try:
        print("\n\n[DEPLOYMENT_FIXER] 🔧 Starting deployment error analysis...")

        session_id = state.session_id
        job_id = getattr(state, "job_id", None)
        deployment_error = state.deployment_error or "No error details available"
        current_pass = state.deployment_fixer_pass

        print(f"[DEPLOYMENT_FIXER] Session: {session_id}")
        print(f"[DEPLOYMENT_FIXER] Current pass: {current_pass}")
        print(f"[DEPLOYMENT_FIXER] Error:\n{deployment_error[:500]}...")

        if job_id:
            log_job_event(
                job_id,
                node="deployment_fixer",
                message=f"Fixing deployment error",
                event_type="node_started",
                data={
                    "session_id": session_id,
                    "error_excerpt": deployment_error[:200],
                    "pass": current_pass,
                },
            )

        # Get list of files
        files = "\n".join(list_files_internal(session_id))

        # Select prompt, tools, and tool_choice based on pass
        if current_pass == 0:
            # Pass 0: Force reading files
            prompt_template = DEPLOYMENT_FIXER_PROMPT_PASS_0
            tools = READ_TOOLS
            tool_choice = "batch_read_files"
            print(
                "[DEPLOYMENT_FIXER] PASS 0: Forcing batch_read_files to read error files"
            )
        elif current_pass == 1:
            # Pass 1: Force writing fixes
            prompt_template = DEPLOYMENT_FIXER_PROMPT_PASS_1
            tools = WRITE_TOOLS
            tool_choice = "batch_update_lines"
            print(
                "[DEPLOYMENT_FIXER] PASS 1: Forcing batch_update_lines to apply fixes"
            )
        else:
            # Pass 2+: Auto mode
            prompt_template = DEPLOYMENT_FIXER_PROMPT_PASS_2
            tools = ALL_TOOLS
            tool_choice = "auto"
            print(f"[DEPLOYMENT_FIXER] PASS {current_pass}: Auto mode - agent decides")

        # Build prompt with context
        prompt_with_context = prompt_template.format(
            deployment_error=deployment_error, files_list=files
        )

        # Create LLM with appropriate tool binding
        _deployment_fixer_llm_ = ChatGoogleGenerativeAI(
            model="models/gemini-3-pro-preview", thinking_budget=256
        ).bind_tools(
            tools,
            tool_choice=tool_choice,
            parallel_tool_calls=True,
        )

        SYS = SystemMessage(content=prompt_with_context)
        messages = [SYS, *state.messages]

        print(f"[DEPLOYMENT_FIXER] Invoking LLM with tool_choice={tool_choice}...")
        response = _deployment_fixer_llm_.invoke(messages)

        print(f"\n\n[DEPLOYMENT_FIXER] Response: {response}")

        # Check if there are tool calls
        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            num_calls = len(tool_calls)
            tool_names = [tc.get("name") for tc in tool_calls]
            print(f"[DEPLOYMENT_FIXER] Tool calls: {tool_names}")

            if job_id:
                log_job_event(
                    job_id,
                    node="deployment_fixer",
                    message=f"Pass {current_pass}: Executing {tool_names}",
                    event_type="node",
                    data={
                        "tool_calls": num_calls,
                        "tools": tool_names,
                        "pass": current_pass,
                    },
                )

            # Increment pass counter for next iteration
            next_pass = current_pass + 1

            return {
                "messages": [response],
                "deployment_fixer_run": True,
                "deployment_fixer_pass": next_pass,
                "deployment_failed": True,  # Still in fixing mode
            }

        # No tool calls - this shouldn't happen with tool_choice="batch_*" but handle it
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

        # If we're still in pass 0 or 1 and got no tool calls, force increment to try again
        next_pass = current_pass + 1 if current_pass < 2 else current_pass

        return {
            "messages": [response],
            "deployment_fixer_run": True,
            "deployment_fixer_pass": next_pass,
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
