from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


from app.agent.prompts_new import (
    CODER_SYSTEM_PROMPT,
    CODER_DESIGN_BOOSTER,
    FOLLOWUP_CODER_SYSTEM_PROMPT,
)
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
    # Command tools
    lint_project,
]


def coder(state: BuilderState) -> BuilderState:
    # Gather all design fields from state for coder prompt context

    print("\n\n[CODER] Follow-up condition met:", state.is_followup)

    _coder_prompt = (
        CODER_SYSTEM_PROMPT if not state.is_followup else FOLLOWUP_CODER_SYSTEM_PROMPT
    )

    print(
        "\n\n[CODER] Using prompt: ",
        "DEFAULT" if not state.is_followup else "FOLLOW-UP",
    )

    _coder_llm_ = ChatOpenAI(model="gpt-5", reasoning_effort="minimal").bind_tools(
        tools,
        parallel_tool_calls=True,
        tool_choice=None if state.coder_run else "batch_read_files",
    )

    # Build design context from structured guidelines if available
    design_context_section = ""
    design_guidelines = state.design_guidelines

    if design_guidelines and state.design_planner_run:
        # Use structured design guidelines from design_planner
        def _build_color_tokens(tokens: list[dict]) -> str:
            if not tokens:
                return "- No color tokens provided"
            lines = []
            for token in tokens:
                name = token.get("name", "color-unnamed")
                value = token.get("value", "#000000")
                usage = token.get("usage", "General use")
                lines.append(f"- {name}: {value} → {usage}")
            return "\n".join(lines)

        def _build_typography(typo: list[dict]) -> str:
            if not typo:
                return "- No typography specifications provided"
            lines = []
            for spec in typo:
                family = spec.get("family", "Inter")
                weights = ", ".join(spec.get("weights", [])) or "400, 600"
                variable = spec.get("variable_name", "--font-sans")
                usage = spec.get("usage", "General text")
                lines.append(
                    f"- {family} (weights: {weights}) → variable {variable} — {usage}"
                )
            return "\n".join(lines)

        def _build_animations(anims: list[dict]) -> str:
            if not anims:
                return "- No animation specs provided"
            lines = []
            for anim in anims:
                anim_type = anim.get("type", "fade-in")
                target = anim.get("target", "section")
                duration = anim.get("duration", "0.6s")
                easing = anim.get("easing", "ease-out")
                notes = anim.get("notes", "")
                note_suffix = f" — {notes}" if notes else ""
                lines.append(
                    f"- {anim_type} on {target} ({duration}, {easing}){note_suffix}"
                )
            return "\n".join(lines)

        def _build_sections(sections: list[dict]) -> str:
            if not sections:
                return "- No section blueprints provided"
            blocks: list[str] = []
            for section in sections:
                section_id = section.get("section_id", "section")
                section_name = section.get("section_name", section_id.title())
                composition = section.get(
                    "composition",
                    "Define composition for this section including layout, grid, and hierarchy.",
                )
                background = section.get(
                    "background",
                    "Describe static background treatment, gradients, and layering.",
                )
                content = section.get(
                    "content_guidance",
                    "Outline content structure, messaging tone, CTAs, and data references.",
                )
                motion = section.get(
                    "motion",
                    "Specify entrance animations, scroll effects, and hover interactions.",
                )
                assets = section.get("assets_usage", "No images provided")
                responsive = section.get(
                    "responsive_notes",
                    "Mobile-first responsive design with appropriate breakpoints",
                )
                custom_notes = section.get("custom_section_notes")
                custom_suffix = (
                    f"\n    - Custom Notes: {custom_notes}" if custom_notes else ""
                )

                blocks.append(
                    f"""
**{section_name} ({section_id})**
    - Composition & Layout: {composition}
    - Background & Layering: {background}
    - Content Guidance: {content}
    - Motion & Interaction: {motion}
    - Assets Usage: {assets}
    - Responsive Notes: {responsive}{custom_suffix}
"""
                )
            return "".join(blocks)

        design_context_section = f"""
### Your Design System (from Design Planner):

**Theme:** {design_guidelines.get('theme', 'dark')}
**Design Philosophy:** {design_guidelines.get('design_philosophy', 'Unspecified design philosophy')}
**Brand Tone:** {design_guidelines.get('brand_tone', 'Unspecified brand tone')}

**Color Tokens:**
{_build_color_tokens(design_guidelines.get('colors', []))}

**Typography Specs:**
{_build_typography(design_guidelines.get('typography', []))}

**Layout Parameters:**
- Container Max Width: {design_guidelines.get('container_max_width', '1280px')}
- Section Spacing: {design_guidelines.get('section_spacing', 'py-16 md:py-24')}
- Grid System: {design_guidelines.get('grid_system', '12-column grid with gap-6 and responsive breakpoints at sm/md/lg/xl')}

**Component Styles:**
- Buttons: {design_guidelines.get('button_styles', 'Refer to design planner instructions for button styles')}
- Inputs: {design_guidelines.get('input_styles', 'Refer to design planner instructions for input styles')}
- Cards: {design_guidelines.get('card_styles', 'Refer to design planner instructions for card styles')}

**Motion Philosophy:** {design_guidelines.get('motion_philosophy', 'Subtle, purposeful, respects prefers-reduced-motion')}

**Animations:**
{_build_animations(design_guidelines.get('animations', []))}

**Section Blueprints (IMPLEMENT IN THIS ORDER):**
{_build_sections(design_guidelines.get('sections', []))}

**Coder Instructions from Design Planner:**
{design_guidelines.get('coder_instructions', 'Implement all sections following the blueprints above.')}

**CRITICAL:**
- Use the design tokens defined in globals.css (color variables, utilities)
- Use the font variables from layout.tsx
- Follow the exact section order above
- Implement each section's composition, background, and motion as specified
- Use the component styles (buttons, inputs, cards) consistently
- Respect the assets usage (only use images if specified)
- Apply responsive notes for mobile/tablet breakpoints
"""
    else:
        # Fallback to raw designer output (for follow-ups or if guidelines not available)
        design_context_section = (
            "\n### Your design system instructions:\n" + state.raw_designer_output
        )

    project_spec = (
        "\n### You are tasked with building and coding this project:\n"
        + state.init_payload_text
    )

    files = "\n".join(list_files_internal(state.session_id))

    SYS = SystemMessage(
        content=_coder_prompt
        + project_spec
        + design_context_section
        + f"\n\nThe following files exist in the session: {files}"
        + "\n\nSTART WORKING, YOU CANNOT CIRCLE BACK TO THE USER UNTIL YOU HAVE COMPLETED THE TASK. DO NOT ASK THE USER FOR ANYTHING UNTIL YOU HAVE COMPLETED THE TASK. DO NOT ASK FOR CONFIRMATION OR ANYTHING, JUST ACT."
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
            f"[CODER] Calling {len(coder_response.tool_calls)} tool(s) to establish design system"
        )
        return {
            "messages": [coder_response],
            "coder_run": True,
            "deployment_failed": False,
            "deployment_error": "",
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
        message="Coder completed implementation pass.",
        event_type="node_completed",
        data={"summary_preview": output[:400]},
    )

    return {"messages": [coder_response], "coder_output": output}
