from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


from app.agent.prompts_new import CODER_SYSTEM_PROMPT
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
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    lint_project,
    run_npx_command,
    run_git_command,
    git_log,
    git_show,
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
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    run_npx_command,
    lint_project,
    run_git_command,
    git_log,
    git_show,
    check_css,
]

_coder_llm_ = ChatOpenAI(model="gpt-5", reasoning_effort="low").bind_tools(tools)


def coder(state: BuilderState) -> BuilderState:
    # Gather all design fields from state for coder prompt context
    design_context = {
        "raw_designer_output": (
            state.raw_designer_output if hasattr(state, "raw_designer_output") else ""
        ),
        "design_guidelines": (
            state.design_guidelines if hasattr(state, "design_guidelines") else ""
        ),
        "design_manifest": (
            state.design_manifest if hasattr(state, "design_manifest") else {}
        ),
        "component_specs": (
            state.component_specs if hasattr(state, "component_specs") else {}
        ),
        "tokens_css": state.tokens_css if hasattr(state, "tokens_css") else "",
        "accessibility_report": (
            state.accessibility_report if hasattr(state, "accessibility_report") else ""
        ),
        "byoc_export": state.byoc_export if hasattr(state, "byoc_export") else {},
        "design_system_run": (
            state.design_system_run if hasattr(state, "design_system_run") else False
        ),
    }

    def summarize_design_context(context):
        summary = []
        # Short summaries for each field

        guidelines = context.get("design_guidelines", "")
        if guidelines:
            summary.append(f"Design guidelines:\n{guidelines}")
        manifest = context.get("design_manifest", {})
        if manifest:
            summary.append(f"Design manifest present: ✓")
        specs = context.get("component_specs", {})
        if specs:
            summary.append(
                f"Component specs available for: {', '.join(list(specs.keys())[:4])}{'...' if len(specs) > 4 else ''}"
            )
        tokens_css = context.get("tokens_css", "")
        if tokens_css:
            summary.append("tokens.css present.")
        a11y = context.get("accessibility_report", "")
        if a11y:
            summary.append("Accessibility report present.")
        byoc = context.get("byoc_export", {})
        if byoc:
            summary.append("BYOC export present.")
        dsysrun = context.get("design_system_run", False)
        summary.append(f"Design system run: {'✅' if dsysrun else '❌'}")
        if not summary:
            summary.append(
                "(No design context available yet. Proceed with template defaults.)"
            )
        return "\n".join(summary)

    design_context_section = (
        "\n\nCURRENT DESIGN SYSTEM CONTEXT:\n"
        + summarize_design_context(design_context)
    )

    SYS = SystemMessage(content=CODER_SYSTEM_PROMPT + design_context_section)
    messages = [SYS, *state.messages]
    coder_response = _coder_llm_.invoke(messages)

    print(f"[CODER] {coder_response}")

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
        output = "Coder response completed. Refer to tool calls or message content."

    return {"messages": [coder_response], "coder_output": output}
