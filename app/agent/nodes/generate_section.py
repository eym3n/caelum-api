from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agent.state import BuilderState
from app.agent.tools.files import get_session_dir
from app.utils.jobs import log_job_event
from app.utils.landing_pages import (
    get_landing_page_by_session_id,
    update_landing_page,
)
from app.models.landing_page import LandingPageUpdate
from app.agent.prompts.generate_section import SECTION_GENERATOR_PROMPT
from toon import encode


class SectionGenerationOutput(BaseModel):
    """Structured response returned by the section generator LLM."""

    filename: str = Field(
        ...,
        description="Relative .tsx path to write (e.g. src/components/sections/HeroSection.tsx)",
    )
    component_name: str = Field(
        ..., description="Named React component to export from the file"
    )
    code: str = Field(
        ..., description="Complete TypeScript/React source code for the section"
    )


def _build_section_prompt(
    design_guidelines: Dict[str, Any],
    section_blueprint: Dict[str, Any],
    init_payload: Dict[str, Any],
) -> List:
    guideline_text = encode(design_guidelines)
    blueprint_text = encode(section_blueprint)
    payload_text = encode(init_payload)

    human_content = (
        "You must implement the section described below using the project’s stack and guardrails."
        "\n\n### Global Design Guidelines (JSON encoded)\n"
        f"{guideline_text}\n\n"
        "### Section Blueprint (JSON encoded)\n"
        f"{blueprint_text}\n\n"
        "### Initialization Payload (JSON encoded)\n"
        f"{payload_text}\n\n"
        "Return only the JSON object matching the schema."
    )

    return [
        SystemMessage(content=SECTION_GENERATOR_PROMPT.strip()),
        HumanMessage(content=human_content),
    ]


async def _generate_single_section(
    section_blueprint: Dict[str, Any],
    design_guidelines: Dict[str, Any],
    init_payload: Dict[str, Any],
) -> SectionGenerationOutput:
    messages = _build_section_prompt(design_guidelines, section_blueprint, init_payload)
    section_name = (
        section_blueprint.get("section_name")
        or section_blueprint.get("section_id")
        or "Unnamed Section"
    )
    print(f"[GENERATE_SECTION] Launching worker for section: {section_name}")
    model = ChatOpenAI(model="gpt-5", reasoning_effort="high")
    structured_llm = model.with_structured_output(SectionGenerationOutput)
    last_exc: Exception | None = None
    for attempt in range(1, 10):
        try:
            result = await structured_llm.ainvoke(messages)
            print(
                f"[GENERATE_SECTION] Worker completed for: {section_name} (attempt {attempt})"
            )
            print(f"[GENERATE_SECTION] Result: {result}")
            if result is None:
                print(
                    f"[GENERATE_SECTION] Result is None for {section_name}, retrying..."
                )
                continue
            return result
        except Exception as exc:  # pragma: no cover - logging
            last_exc = exc
            print(
                f"[GENERATE_SECTION] Attempt {attempt} failed for {section_name}: {exc}"
            )
    raise RuntimeError(
        f"Section generation failed for {section_name} after 3 attempts."
    ) from last_exc


def _sanitize_section_filename(filename: str) -> str:
    cleaned = (filename or "").lstrip("./")
    cleaned = cleaned.replace("src/app/components/sections", "src/components/sections")
    if cleaned.startswith("components/sections/"):
        cleaned = "src/" + cleaned
    if not cleaned.startswith("src/components/sections"):
        name = Path(cleaned).name or "Section.tsx"
        cleaned = f"src/components/sections/{name}"
    return cleaned


def _write_section_file(session_dir: Path, result: SectionGenerationOutput) -> None:
    sanitized_filename = _sanitize_section_filename(result.filename)
    if sanitized_filename != result.filename:
        print(
            f"[GENERATE_SECTION] Adjusted filename from {result.filename} to {sanitized_filename}"
        )
        result.filename = sanitized_filename
    file_path = session_dir / sanitized_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = result.code.rstrip()
    stripped = content.lstrip()
    if not (stripped.startswith("'use client'") or stripped.startswith('"use client"')):
        content = "'use client';\n\n" + content
    if not content.endswith("\n"):
        content += "\n"
    file_path.write_text(content, encoding="utf-8")
    result.code = content


def _write_sections_index(
    session_dir: Path, results: List[SectionGenerationOutput]
) -> None:
    sections_dir = session_dir / "src" / "components" / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    export_lines = []
    for result in results:
        filename = Path(result.filename)
        if "sections" in filename.parts:
            try:
                idx = filename.parts.index("sections")
                relative = Path(*filename.parts[idx + 1 :])
            except ValueError:
                relative = filename
        else:
            relative = filename
        module_path = relative.with_suffix("")
        export_lines.append(
            f'export {{ {result.component_name} }} from "./{module_path.as_posix()}";'
        )

    export_content = "\n".join(export_lines) + "\n"
    (sections_dir / "index.ts").write_text(export_content, encoding="utf-8")


def generate_section(state: BuilderState) -> BuilderState:
    log_job_event(
        state.job_id,
        node="generate_section",
        message="Generating React sections per blueprint...",
        event_type="node_started",
    )

    design_guidelines = state.design_guidelines or {}
    sections = design_guidelines.get("sections") or []
    init_payload = state.init_payload or {}

    if not sections:
        log_job_event(
            state.job_id,
            node="generate_section",
            message="No sections found in design guidelines; skipping generation.",
            event_type="node_completed",
        )
        return {
            "generated_sections": [],
            "sections_generated": False,
        }

    session_dir = get_session_dir(state.session_id)

    async def run_workers() -> List[SectionGenerationOutput]:
        tasks: List[asyncio.Task[SectionGenerationOutput]] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            if tasks:
                await asyncio.sleep(1)
            task = asyncio.create_task(
                _generate_single_section(section, design_guidelines, init_payload)
            )
            tasks.append(task)
        if not tasks:
            return []
        return await asyncio.gather(*tasks)

    try:
        results = asyncio.run(run_workers())
        print(
            f"[GENERATE_SECTION] Async workers completed for session {state.session_id}"
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(run_workers())
        finally:
            asyncio.set_event_loop(None)
            loop.close()
        print(
            f"[GENERATE_SECTION] Async workers completed using dedicated loop for session {state.session_id}"
        )

    sanitized_results: List[SectionGenerationOutput] = results

    for result in sanitized_results:
        _write_section_file(session_dir, result)
        print(f"[GENERATE_SECTION] Wrote section file: {result.filename}")

    _write_sections_index(session_dir, sanitized_results)
    print("[GENERATE_SECTION] Updated sections/index.ts with new exports.")

    def _normalize_filename(value: str | None) -> str:
        return value.lstrip("./") if value else ""

    section_payload = []
    for blueprint in sections:
        if not isinstance(blueprint, dict):
            continue
        raw_filename = blueprint.get("section_file_name_tsx") or blueprint.get(
            "section_file_name"
        )
        blueprint_filename = _normalize_filename(
            _sanitize_section_filename(raw_filename)
        )
        match = next(
            (
                r
                for r in sanitized_results
                if _normalize_filename(r.filename) == blueprint_filename
            ),
            None,
        )
        if match:
            section_payload.append(
                {
                    "id": blueprint.get("section_id"),
                    "name": blueprint.get("section_name"),
                    "filename": match.filename,
                    "file_content": match.code,
                }
            )

    try:
        landing_page_doc = get_landing_page_by_session_id(state.session_id)
        if landing_page_doc and section_payload:
            update_landing_page(
                landing_page_doc.id,
                LandingPageUpdate(sections=section_payload),
            )
            print(
                f"[GENERATE_SECTION] Persisted {len(section_payload)} section entries to landing page {landing_page_doc.id}"
            )
    except Exception as persist_exc:  # pragma: no cover - logging only
        print(
            f"[GENERATE_SECTION] Warning: failed to persist sections for session {state.session_id}: {persist_exc}"
        )

    summary = f"Generated {len(sanitized_results)} section file(s)."
    log_job_event(
        state.job_id,
        node="generate_section",
        message=summary,
        event_type="node_completed",
        data={
            "sections": [r.filename for r in results],
        },
    )

    return {
        "generated_sections": [r.dict() for r in sanitized_results],
        "sections_generated": True,
    }
