from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.state import BuilderState
from app.agent.models.design_guidelines import DesignGuidelines
from app.utils.jobs import log_job_event
from app.agent.prompts.design_planner import (
    DESIGN_PLANNER_PROMPT_TEMPLATE,
    HERO_CONCEPTS,
    FEATURES_LAYOUT_OPTIONS,
    NAV_STYLE_INSPIRATION,
)
from toon import encode
from app.utils.landing_pages import (
    get_landing_page_by_session_id,
    update_landing_page,
)
from app.models.landing_page import LandingPageUpdate


_design_planner_llm_ = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-09-2025")


def design_planner(state: BuilderState) -> BuilderState:
    """
    Design Planner Node - Generates the full creative blueprint consumed directly by the coder.

    This node runs before any coding happens and produces a structured DesignGuidelines object
    that contains page-level directives plus per-section blueprints. The coder will rely on this
    blueprint to build fully self-contained section components (no global design system layer).

    NO TOOLS - This node only analyzes the init payload and generates structured output.
    """
    log_job_event(
        state.job_id,
        node="design_planner",
        message="Generating global design blueprint...",
        event_type="node_started",
    )
    session_id = state.session_id
    print(f"🎨 [DESIGN_PLANNER] Generating design guidelines for session: {session_id}")

    # Build context from init payload
    init_payload_text = state.init_payload_text or "No initialization payload provided."

    data_context_parts: list[str] = []
    if state.campaign_data_digest:
        data_context_parts.append(
            "### Campaign Performance Digest\n" + state.campaign_data_digest.strip()
        )
    if state.experiment_data_digest:
        data_context_parts.append(
            "### Experiment Insights Digest\n" + state.experiment_data_digest.strip()
        )
    if state.data_insights:
        data_context_parts.append(
            "### Structured Data Signals (JSON)\n" + encode(state.data_insights)
        )
    if state.data_warnings:
        warning_block = "\n".join(f"- {warning}" for warning in state.data_warnings)
        data_context_parts.append("### Data Quality Warnings\n" + warning_block)
    if data_context_parts:
        init_payload_text = init_payload_text + "\n\n" + "\n\n".join(data_context_parts)

    # Inject inspiration into prompt
    hero_insp_str = "\n".join([f"- {item}" for item in HERO_CONCEPTS])
    features_insp_str = "\n".join([f"- {item}" for item in FEATURES_LAYOUT_OPTIONS])
    nav_insp_str = "\n".join([f"- {item}" for item in NAV_STYLE_INSPIRATION])

    prompt = DESIGN_PLANNER_PROMPT_TEMPLATE.replace(
        "**_hero_inspiration_**", hero_insp_str
    )
    prompt = prompt.replace("**_features_inspiration_**", features_insp_str)
    prompt = prompt.replace("**_nav_inspiration_**", nav_insp_str)

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
            data=design_guidelines.model_dump(),
        )

        # Store structured guidelines in state
        # We'll add a new field to BuilderState to hold this
        guidelines_dict = design_guidelines.model_dump()
        print(encode(guidelines_dict))

        # Persist design guidelines to the landing page record
        try:
            landing_page_doc = get_landing_page_by_session_id(session_id)
            if landing_page_doc:
                business_data = landing_page_doc.business_data or {}
                business_data["design_guidelines"] = guidelines_dict
                update_landing_page(
                    landing_page_doc.id,
                    LandingPageUpdate(business_data=business_data),
                )
        except Exception as persist_exc:  # pragma: no cover - log but don't fail
            print(
                f"[DESIGN_PLANNER] Warning: failed to persist design guidelines for session {session_id}: {persist_exc}"
            )

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
