import re
from typing import Any, Dict, List

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
    CANONICAL_SECTION_LIBRARY,
    CANONICAL_SECTION_ALIASES,
)
from toon import encode
from app.utils.landing_pages import (
    get_landing_page_by_session_id,
    update_landing_page,
)
from app.models.landing_page import LandingPageUpdate


_design_planner_llm_ = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-09-2025")

_CANONICAL_REGISTRY: Dict[str, Dict[str, str]] = {
    entry["section_id"]: entry for entry in CANONICAL_SECTION_LIBRARY
}


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


_CANONICAL_ALIAS_MAP: Dict[str, str] = {
    _normalize_key(alias): canonical
    for alias, canonical in CANONICAL_SECTION_ALIASES.items()
}
for entry in CANONICAL_SECTION_LIBRARY:
    canonical_id = entry["section_id"]
    for candidate in (
        entry["section_id"],
        entry["section_name"],
        entry["component_name"],
        entry["component_name"].removesuffix("Section"),
    ):
        key = _normalize_key(candidate)
        if not key:
            continue
        _CANONICAL_ALIAS_MAP[key] = canonical_id


def _to_pascal_case(value: str | None) -> str:
    if not value:
        return ""
    parts = re.split(r"[^a-z0-9]+", value.lower())
    return "".join(part.capitalize() for part in parts if part)


def _to_human_label(pascal: str) -> str:
    if not pascal:
        return "Custom Section"
    words = re.findall(r"[A-Z][a-z0-9]*", pascal)
    return (" ".join(words) or pascal) + " Section"


def _canonicalize_section(section: Dict[str, Any], index: int) -> Dict[str, Any]:
    candidates: List[str] = []
    for key in ("section_id", "section_name", "component_name"):
        value = section.get(key)
        if isinstance(value, str):
            candidates.append(value)
    filename = section.get("section_file_name_tsx")
    if isinstance(filename, str):
        basename = filename.split("/")[-1]
        if basename.endswith(".tsx"):
            basename = basename[:-4]
        candidates.append(basename)

    canonical_entry: Dict[str, str] | None = None
    for candidate in candidates:
        normalized = _normalize_key(candidate)
        canonical_id = _CANONICAL_ALIAS_MAP.get(normalized)
        if canonical_id:
            canonical_entry = _CANONICAL_REGISTRY.get(canonical_id)
            if canonical_entry:
                break

    if canonical_entry:
        section["section_id"] = canonical_entry["section_id"]
        section["section_name"] = canonical_entry["section_name"]
        section["component_name"] = canonical_entry["component_name"]
        section["section_file_name_tsx"] = canonical_entry["section_file_name_tsx"]
        return section

    # Custom section normalization
    source_seed = (
        section.get("section_name")
        or section.get("section_id")
        or f"Custom {index + 1}"
    )
    pascal = _to_pascal_case(source_seed) or f"Custom{index + 1}"
    if not pascal.endswith("Section"):
        component_name = f"{pascal}Section"
    else:
        component_name = pascal
        pascal = pascal[: -len("Section")] or pascal
    human_label = section.get("section_name")
    if not human_label or _normalize_key(human_label) != _normalize_key(pascal):
        section["section_name"] = _to_human_label(pascal)
    section["component_name"] = component_name
    slug = section.get("section_id")
    desired_slug = re.sub(r"[^a-z0-9]+", "-", section["section_name"].lower()).strip(
        "-"
    )
    if not desired_slug:
        desired_slug = f"custom-section-{index + 1:02d}"
    section["section_id"] = desired_slug
    section["section_file_name_tsx"] = f"src/components/sections/{component_name}.tsx"
    return section


def _canonicalize_section_blueprints(guidelines: Dict[str, Any]) -> None:
    sections = guidelines.get("sections")
    if not isinstance(sections, list):
        return
    for idx, section in enumerate(sections):
        if isinstance(section, dict):
            _canonicalize_section(section, idx)
            section["ordering_index"] = section.get("ordering_index") or f"{idx:02d}"


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

    canonical_sections_str = "\n".join(
        f"- {entry['section_name']} → component `{entry['component_name']}` | id `{entry['section_id']}` | file `{entry['section_file_name_tsx']}`"
        for entry in CANONICAL_SECTION_LIBRARY
    )

    prompt = DESIGN_PLANNER_PROMPT_TEMPLATE.replace(
        "**_hero_inspiration_**", hero_insp_str
    )
    prompt = prompt.replace("**_features_inspiration_**", features_insp_str)
    prompt = prompt.replace("**_nav_inspiration_**", nav_insp_str)
    prompt = prompt.replace("**_canonical_sections_table_**", canonical_sections_str)

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

        # Prepare canonicalized guidelines for logging and persistence
        guidelines_dict = design_guidelines.model_dump()
        _canonicalize_section_blueprints(guidelines_dict)
        print(encode(guidelines_dict))

        # Log to job system
        log_job_event(
            state.job_id,
            node="design_planner",
            message="Design planner generated comprehensive design guidelines.",
            event_type="node_completed",
            data=guidelines_dict,
        )

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
