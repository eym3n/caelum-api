import json
import random
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from app.agent.state import BuilderState
from app.agent.models.design_guidelines import DesignGuidelines
from app.utils.jobs import log_job_event
from app.agent.prompts.design_planner import (
    DESIGN_PLANNER_PROMPT_TEMPLATE,
    HERO_CONCEPTS,
    FEATURES_LAYOUT_OPTIONS,
    NAV_STYLE_INSPIRATION,
    PRICING_PLANS_OPTIONS,
    CTA_SECTION_GUIDELINES,
    TESTIMONIALS_SOCIAL_PROOF_OPTIONS,
)
from toon import encode


_design_planner_llm_ = ChatOpenAI(model="gpt-5", reasoning_effort="minimal")


def design_planner(state: BuilderState) -> BuilderState:
    """
    Design Planner Node - Generates structured design guidelines.

    This node runs BEFORE the designer and makes ALL creative design decisions.
    It outputs a structured DesignGuidelines object that will be stored in state
    and used by the designer node to implement the actual files.

    NO TOOLS - This node only analyzes the init payload and generates structured output.
    """
    session_id = state.session_id
    print(f"🎨 [DESIGN_PLANNER] Generating design guidelines for session: {session_id}")

    # Build context from init payload
    init_payload_text = state.init_payload_text or "No initialization payload provided."

    # Inject inspiration lists into prompt (randomize order for variety)
    prompt = DESIGN_PLANNER_PROMPT_TEMPLATE
    prompt = prompt.replace(
        "**_hero_inspiration_**",
        "\n".join(random.sample(HERO_CONCEPTS, len(HERO_CONCEPTS))),
    )
    prompt = prompt.replace(
        "**_features_inspiration_**",
        "\n".join(random.sample(FEATURES_LAYOUT_OPTIONS, len(FEATURES_LAYOUT_OPTIONS))),
    )
    prompt = prompt.replace(
        "**_nav_inspiration_**",
        "\n".join(random.sample(NAV_STYLE_INSPIRATION, len(NAV_STYLE_INSPIRATION))),
    )
    prompt = prompt.replace(
        "**_pricing_inspiration_**",
        "\n".join(random.sample(PRICING_PLANS_OPTIONS, len(PRICING_PLANS_OPTIONS))),
    )
    prompt = prompt.replace(
        "**_cta_inspiration_**",
        "\n".join(random.sample(CTA_SECTION_GUIDELINES, len(CTA_SECTION_GUIDELINES))),
    )
    prompt = prompt.replace(
        "**_testimonials_inspiration_**",
        "\n".join(
            random.sample(
                TESTIMONIALS_SOCIAL_PROOF_OPTIONS,
                len(TESTIMONIALS_SOCIAL_PROOF_OPTIONS),
            )
        ),
    )

    system_message = SystemMessage(content=prompt + init_payload_text)
    messages = [system_message, *state.messages]

    try:
        # Generate structured design guidelines
        print("[DESIGN_PLANNER] Invoking LLM with structured output...")
        design_guidelines: DesignGuidelines = (
            _design_planner_llm_.with_structured_output(DesignGuidelines).invoke(
                messages
            )
        )

        print(f"✅ [DESIGN_PLANNER] Generated design guidelines:")

        # Log to job system
        log_job_event(
            state.job_id,
            node="design_planner",
            message="Design planner generated comprehensive design guidelines.",
            event_type="node_completed",
            data={
                "theme": design_guidelines.theme,
                "color_count": len(design_guidelines.colors),
                "typography_count": len(design_guidelines.typography),
                "section_count": len(design_guidelines.sections),
                "animation_count": len(design_guidelines.animations),
            },
        )

        # Store structured guidelines in state
        # We'll add a new field to BuilderState to hold this
        guidelines_dict = design_guidelines.model_dump()
        print(encode(guidelines_dict))

        return {
            "design_guidelines": guidelines_dict,
            "design_planner_run": True,
        }

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"❌ [DESIGN_PLANNER] Error generating design guidelines: {e}")
        print(f"[DESIGN_PLANNER] Full traceback:\n{error_details}")
        log_job_event(
            state.job_id,
            node="design_planner",
            message=f"Design planner failed: {str(e)}",
            event_type="error",
            data={"error": str(e), "traceback": error_details[:500]},
        )
        # Return empty guidelines on error - designer will fall back to default behavior
        return {
            "design_guidelines": {},
            "design_planner_run": False,
        }
