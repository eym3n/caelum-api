from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.prompts.design_blueprint_pdf import DESIGN_BLUEPRINT_PDF_PROMPT
from app.agent.state import BuilderState
from app.agent.utils.pdf import markdown_to_pdf
from app.agent.utils.storage import upload_file_to_gcs
from app.config import Config
from app.utils.landing_pages import update_landing_page_status
from app.utils.jobs import log_job_event


_documentation_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-09-2025", temperature=0.2
)


def _serialize_payload(data: dict[str, Any]) -> str:
    if not data:
        return "Not provided."
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)


def _write_markdown(markdown_text: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markdown_text, encoding="utf-8")


def design_blueprint_pdf(state: BuilderState) -> BuilderState:
    job_id = state.job_id
    log_job_event(
        job_id,
        node="design_blueprint_pdf",
        message="Authoring design blueprint documentation...",
        event_type="node_started",
    )

    if not state.design_guidelines:
        log_job_event(
            job_id,
            node="design_blueprint_pdf",
            message="Design guidelines missing; skipping PDF generation.",
            event_type="node_completed",
        )
        return {"design_blueprint_pdf_run": False}

    system = SystemMessage(content=DESIGN_BLUEPRINT_PDF_PROMPT)
    company_payload = _serialize_payload(state.init_payload)
    guidelines_payload = _serialize_payload(state.design_guidelines)

    context_block = (
        "### Company / Intake Payload\n"
        f"{company_payload}\n\n"
        "### Design Planner Blueprint\n"
        f"{guidelines_payload}"
    )
    human = HumanMessage(content=context_block)

    try:
        llm_response = _documentation_llm.invoke([system, human])
        markdown_text = (
            llm_response.content
            if isinstance(llm_response.content, str)
            else str(llm_response.content)
        )

        print(f"[DESIGN_BLUEPRINT_PDF] Markdown text: {markdown_text}")

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        base_name = f"{state.session_id}-{timestamp}"
        output_dir = Path(Config.OUTPUT_PATH) / "design_blueprints"
        markdown_path = output_dir / f"{base_name}.md"
        pdf_path = output_dir / f"{base_name}.pdf"

        _write_markdown(markdown_text, markdown_path)
        markdown_to_pdf(markdown_text, pdf_path)

        destination_blob = f"design_blueprints/{state.session_id}/{base_name}.pdf"
        pdf_url = upload_file_to_gcs(pdf_path, destination_blob=destination_blob)

        if pdf_url is None:
            pdf_url = pdf_path.resolve().as_posix()
            storage_message = "Stored locally (GCS client unavailable)."
        else:
            storage_message = "Uploaded blueprint PDF to Google Cloud Storage."

        log_job_event(
            job_id,
            node="design_blueprint_pdf",
            message="Generated design blueprint PDF documentation.",
            event_type="node_completed",
            data={
                "markdown_path": markdown_path.as_posix(),
                "pdf_path": pdf_path.as_posix(),
                "pdf_url": pdf_url,
                "storage_note": storage_message,
            },
        )

        if state.session_id and pdf_url:
            try:
                update_landing_page_status(
                    session_id=state.session_id,
                    design_blueprint_pdf_url=pdf_url,
                )
            except Exception as update_exc:
                print(
                    f"[DESIGN_BLUEPRINT_PDF] Warning: failed to persist PDF URL for session {state.session_id}: {update_exc}"
                )

        return {
            "design_blueprint_markdown": markdown_text,
            "design_blueprint_pdf_url": pdf_url,
            "design_blueprint_pdf_run": True,
        }

    except Exception as exc:
        import traceback

        error_trace = traceback.format_exc()
        log_job_event(
            job_id,
            node="design_blueprint_pdf",
            message=f"Design blueprint PDF generation failed: {exc}",
            event_type="error",
            data={"error": str(exc), "traceback": error_trace[:800]},
        )
        return {"design_blueprint_pdf_run": False}
