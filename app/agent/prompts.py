from pathlib import Path

# Load design manifest
_manifest_path = Path(__file__).parent / "docs" / "DESIGN_MANIFEST.md"
_design_manifest = _manifest_path.read_text() if _manifest_path.exists() else ""

from app.agent.prompts_new import (
    ROUTER_SYSTEM_PROMPT,
    CLARIFY_SYSTEM_PROMPT,
    DESIGNER_SYSTEM_PROMPT,
    CODER_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    ARCHITECT_SYSTEM_PROMPT,
)



