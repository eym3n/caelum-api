from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


from app.agent.prompts_new import CODER_SYSTEM_PROMPT, CODER_DESIGN_BOOSTER
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
)

from app.agent.tools.commands import (
    run_npm_command,
    lint_project,
    run_npx_command,
    check_css,
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
    run_npm_command,
    run_npx_command,
    lint_project,
    check_css,
]


def coder(state: BuilderState) -> BuilderState:
    # Gather all design fields from state for coder prompt context

    if state.coder_run:
        _coder_llm_ = ChatOpenAI(
            model="gpt-5", reasoning_effort="minimal", verbosity="low"
        ).bind_tools(tools, parallel_tool_calls=True)

    else:
        _coder_llm_ = ChatOpenAI(
            model="gpt-5", reasoning_effort="minimal", verbosity="low"
        ).bind_tools(tools, parallel_tool_calls=True, tool_choice="any")

    design_context_section = "\n### Designer Notes:\n" + state.raw_designer_output

    project_spec = (
        "\n### You are tasked with building and coding this project:\n"
        + state.init_payload_text
    )

    SYS = SystemMessage(
        content=CODER_SYSTEM_PROMPT
        + project_spec
        + design_context_section
        + CODER_DESIGN_BOOSTER
    )
    HUMAN = HumanMessage(content="Start coding the landing page for my project. ")
    messages = [SYS, *state.messages, HUMAN]

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
            f"[CODER] Calling {len(coder_response.tool_calls)} tool(s) to establish design system"
        )
        return {"messages": [coder_response], "coder_run": True}

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

    return {"messages": [coder_response], "coder_output": output}
