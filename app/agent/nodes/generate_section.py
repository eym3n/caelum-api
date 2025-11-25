from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import SystemMessage, HumanMessage
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
from google import genai


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


EXAMPLES_BASE_DIR = Path(__file__).resolve().parent.parent / "examples"
SECTION_EXAMPLES_DIR = EXAMPLES_BASE_DIR / "components" / "sections"
_SECTION_EXAMPLES_CACHE: Dict[str, Dict[str, str]] | None = None
_GENAI_CLIENT: genai.Client | None = None


def _normalize_section_key(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _load_section_examples() -> Dict[str, Dict[str, str]]:
    global _SECTION_EXAMPLES_CACHE
    if _SECTION_EXAMPLES_CACHE is not None:
        return _SECTION_EXAMPLES_CACHE

    examples: Dict[str, Dict[str, str]] = {}
    if SECTION_EXAMPLES_DIR.exists():
        for file_path in SECTION_EXAMPLES_DIR.glob("*.tsx"):
            key = _normalize_section_key(file_path.stem)
            if not key:
                continue
            try:
                examples[key] = {
                    "relative_path": str(file_path.relative_to(EXAMPLES_BASE_DIR)),
                    "code": file_path.read_text(encoding="utf-8"),
                }
            except Exception as exc:  # pragma: no cover - logging only
                print(
                    f"[GENERATE_SECTION] Warning: failed to load example {file_path}: {exc}"
                )

    _SECTION_EXAMPLES_CACHE = examples
    return examples


def _get_genai_client() -> genai.Client:
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        _GENAI_CLIENT = genai.Client()
    return _GENAI_CLIENT


def _resolve_section_example(
    section_blueprint: Dict[str, Any],
) -> Dict[str, str] | None:
    examples = _load_section_examples()
    candidate_values: List[str] = []

    raw_filename = section_blueprint.get(
        "section_file_name_tsx"
    ) or section_blueprint.get("section_file_name")
    if isinstance(raw_filename, str):
        candidate_values.append(Path(raw_filename).stem)

    section_name = section_blueprint.get("section_name")
    section_id = section_blueprint.get("section_id")
    for value in (section_name, section_id):
        if not isinstance(value, str):
            continue
        candidate_values.append(value)
        parts = re.split(r"[\s_\-]+", value.strip())
        if parts:
            pascal = "".join(part.capitalize() for part in parts if part)
            if pascal:
                candidate_values.append(pascal)

    normalized_candidates = [
        _normalize_section_key(candidate) for candidate in candidate_values if candidate
    ]

    for candidate in normalized_candidates:
        if candidate in examples:
            return examples[candidate]

    for candidate in normalized_candidates:
        for key, example in examples.items():
            if candidate and (candidate in key or key in candidate):
                return example

    return None


def _build_section_prompt(
    design_guidelines: Dict[str, Any],
    section_blueprint: Dict[str, Any],
    init_payload: Dict[str, Any],
) -> List:
    guideline_text = encode(design_guidelines)
    blueprint_text = encode(section_blueprint)
    payload_text = encode(init_payload)
    example_entry = _resolve_section_example(section_blueprint)

    human_content = (
        "You must implement the section described below using the project’s stack and guardrails."
        "\n\n### Global Design Guidelines (JSON encoded)\n"
        f"{guideline_text}\n\n"
        "### Section Blueprint (JSON encoded)\n"
        f"{blueprint_text}\n\n"
        "### Initialization Payload (JSON encoded)\n"
        f"{payload_text}\n"
    )

    if example_entry:
        example_payload = encode(
            {
                "reference_filename": example_entry["relative_path"],
                "reference_code": example_entry["code"],
            }
        )
        human_content += (
            "\n### Section Reference Example (JSON encoded)\n"
            f"{example_payload}\n"
            "Use this reference as the structural template: mirror its import order, React component shell, props typing patterns, FEAAS registration shape, motion setup, and helper constant organization. Only change names, defaults, and content where the blueprint requires it."
        )
    else:
        human_content += (
            "\n### Section Reference Example\n"
            "No direct example available; follow the guardrails and business context precisely.\n"
        )

    human_content += (
        "\nAlways stay as close as possible to the reference syntax and structure so the generated component feels like a sibling to the example.\n"
        "Return only the JSON object matching the schema."
    )

    return [
        SystemMessage(content=SECTION_GENERATOR_PROMPT.strip()),
        HumanMessage(content=human_content),
    ]


def _messages_to_prompt(messages: List) -> str:
    chunks: List[str] = []
    for message in messages:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            chunks.append(content.strip())
        elif isinstance(content, list):
            chunks.append("\n".join(str(item) for item in content))
        else:
            chunks.append(str(content))
    prompt = "\n\n".join(chunk for chunk in chunks if chunk)
    return prompt.strip()


async def _invoke_gemini_structured(messages: List) -> SectionGenerationOutput:
    prompt = _messages_to_prompt(messages)
    if not prompt:
        raise ValueError("Gemini prompt was empty.")

    client = _get_genai_client()

    def _call() -> SectionGenerationOutput:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": SectionGenerationOutput.model_json_schema(),
            },
        )
        raw_text = getattr(response, "text", "") or ""
        if not raw_text.strip():
            raise ValueError("Gemini returned empty response text.")
        return SectionGenerationOutput.model_validate_json(raw_text)

    return await asyncio.to_thread(_call)


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
    try:
        system_prompt = getattr(messages[0], "content", "")
        human_prompt = getattr(messages[1], "content", "")
        print(
            f"[GENERATE_SECTION] Prompt for {section_name}:\n"
            f"--- SYSTEM ---\n{system_prompt}\n"
            f"--- HUMAN ---\n{human_prompt}\n"
            f"--- END PROMPT ({section_name}) ---"
        )
    except Exception as prompt_exc:  # pragma: no cover - logging only
        print(
            f"[GENERATE_SECTION] Warning: failed to print prompt for {section_name}: {prompt_exc}"
        )
    print(f"[GENERATE_SECTION] Launching worker for section: {section_name}")

    fallback_model = ChatOpenAI(
        model="gpt-5", reasoning_effort="low"
    ).with_structured_output(SectionGenerationOutput)

    last_exc: Exception | None = None

    # Primary attempts with Gemini
    for attempt in range(1, 4):
        try:
            result = await _invoke_gemini_structured(messages)
            print(
                f"[GENERATE_SECTION] (Gemini) Worker completed for: {section_name} (attempt {attempt})"
            )
            print(f"[GENERATE_SECTION] Result: {result}")
            if result is None:
                print(
                    f"[GENERATE_SECTION] Result is None for {section_name} using Gemini, retrying..."
                )
                continue
            return result
        except Exception as exc:  # pragma: no cover - logging
            last_exc = exc
            print(
                f"[GENERATE_SECTION] (Gemini) Attempt {attempt} failed for {section_name}: {exc}"
            )

    print(
        f"[GENERATE_SECTION] Switching to GPT-5 fallback for section: {section_name} after 3 Gemini failures."
    )

    # Fallback attempts with GPT-5
    for attempt in range(4, 10):
        try:
            result = await fallback_model.ainvoke(messages)
            print(
                f"[GENERATE_SECTION] (GPT-5) Worker completed for: {section_name} (attempt {attempt - 3})"
            )
            print(f"[GENERATE_SECTION] Result: {result}")
            if result is None:
                print(
                    f"[GENERATE_SECTION] Result is None for {section_name} using GPT-5, retrying..."
                )
                continue
            return result
        except Exception as exc:  # pragma: no cover - logging
            last_exc = exc
            print(
                f"[GENERATE_SECTION] (GPT-5) Attempt {attempt - 3} failed for {section_name}: {exc}"
            )

    raise RuntimeError(
        f"Section generation failed for {section_name} after exhausting Gemini and GPT-5 attempts."
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
            expected_component = blueprint.get("component_name")
            if isinstance(expected_component, str) and expected_component:
                if match.component_name != expected_component:
                    print(
                        f"[GENERATE_SECTION] Aligning component name from {match.component_name} to blueprint value {expected_component}"
                    )
                    match.component_name = expected_component
            section_payload.append(
                {
                    "id": blueprint.get("section_id"),
                    "name": blueprint.get("section_name"),
                    "component_name": expected_component or match.component_name,
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
