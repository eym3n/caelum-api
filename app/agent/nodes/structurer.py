from __future__ import annotations
from langchain_core.messages import SystemMessage, AIMessage
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.agent.state import BuilderState


load_dotenv()


# LLM
STRUCTURER_SYSTEM_PROMPT = """
You are the **Structurer Agent**. Convert the Designer Agent's text (from Pass 1) into fully structured artifacts.

REQUIREMENTS:
- Return a value that matches the provided Pydantic schema exactly (using with_structured_output).
- Populate:
  - design_manifest: include meta (brand/version/locales), a11y, RTL, tokens (color/typography/space/radii/shadows/motion), themes, components inventory, layouts, assets metadata.
  - component_specs: keys for Button, Input, Nav, Hero, FeaturesGrid, Pricing, Testimonials, FAQ, CTA, Footer. Each spec should include name, category, tokens, props (types/defaults), states/variants, a11y, optional tests.
  - tokens_css: valid CSS variables mapping token names to values. Use reasonable defaults if not specified.
  - accessibility_report: Markdown describing WCAG 2.2 AA contrast, focus states, keyboard support, RTL validation steps.
  - byoc_export: JSON compatible with Sitecore BYOC (componentName, propsSchema, slots/placeholders, variants). Ensure mapping from component_specs is coherent.
- If the Designer text omits something, fill with safe, minimal, brand-agnostic defaults. Use Arabic (RTL) and French (LTR) by default.
- Use deterministic, neutral token naming (e.g., color.primary.500).
- Do NOT invent external URLs; use placeholders (e.g., ./public/brand/logo.svg) when necessary.
"""

_structurer_llm_ = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


# Models
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DesignerStructuredOutput(BaseModel):
    # Core design artifacts
    design_manifest: Dict[str, Any] = Field(
        ..., description="Full design_manifest.json as a dict."
    )
    component_specs: Dict[str, Dict[str, Any]] = Field(
        ..., description="Map of component name to its spec JSON as dict."
    )
    tokens_css: str = Field(..., description="CSS variables file contents.")
    accessibility_report: str = Field(..., description="Markdown accessibility report.")
    byoc_export: Dict[str, Any] = Field(
        ..., description="Sitecore BYOC-compatible payload."
    )

    # Optional diagnostics
    errors: Optional[List[str]] = Field(
        default=None, description="Non-fatal warnings or missing assumptions resolved."
    )


def structurer(state: BuilderState) -> BuilderState:
    designer_payload = (
        state.design_guidelines if state.design_guidelines else {"note": "No guidelines"}
    )
    SYS = SystemMessage(
        content=STRUCTURER_SYSTEM_PROMPT
        + "\n\nDESIGNER_OUTPUT:\n"
        + str(designer_payload)
    )
    messages = [SYS, *state.messages]
    structurer_response = _structurer_llm_.with_structured_output(
        DesignerStructuredOutput
    ).invoke(messages)
    print(f"[STRUCTURER] Response: {structurer_response}")
    return {
        "design_manifest": structurer_response.design_manifest,
        "component_specs": structurer_response.component_specs,
        "tokens_css": structurer_response.tokens_css,
        "accessibility_report": structurer_response.accessibility_report,
        "byoc_export": structurer_response.byoc_export,
    }
