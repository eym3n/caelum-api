"""Landing pages router for CRUD operations."""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.models.user import User
from app.models.landing_page import (
    LandingPage,
    LandingPageCreate,
    LandingPageUpdate,
    LandingPageList,
    LandingPageStatus,
)
from app.deps import get_current_user
from app.utils.landing_pages import (
    create_landing_page,
    get_landing_page_by_id,
    get_landing_page_by_session_id,
    get_user_landing_pages,
    update_landing_page,
    delete_landing_page,
)
from app.agent.tools.files import get_session_dir
from pathlib import Path
import math
from typing import Any, List

router = APIRouter(tags=["landing-pages"])


def _build_sections_payload(landing_page) -> List[dict[str, Any]]:
    session_dir = get_session_dir(landing_page.session_id)
    stored_sections = landing_page.sections or []

    if stored_sections:
        section_entries = [
            section.model_dump()
            if hasattr(section, "model_dump")
            else dict(section)
            if isinstance(section, dict)
            else section
            for section in stored_sections
        ]
    else:
        business_data = landing_page.business_data or {}
        design_guidelines = business_data.get("design_guidelines") or {}
        raw_sections = design_guidelines.get("sections") or []
        if not isinstance(raw_sections, list):
            raw_sections = []
        section_entries = [
            {
                "id": section.get("section_id"),
                "name": section.get("section_name"),
                "component_name": section.get("component_name"),
                "filename": section.get("section_file_name_tsx")
                or section.get("section_file_name"),
            }
            for section in raw_sections
            if isinstance(section, dict)
        ]

    payload: List[dict[str, Any]] = []

    for entry in section_entries:
        if hasattr(entry, "model_dump"):
            entry = entry.model_dump()
        elif not isinstance(entry, dict):
            entry = dict(entry)

        section_id = entry.get("id")
        section_name = entry.get("name")
        component_name = entry.get("component_name")
        filename = entry.get("filename") or ""

        file_content = None
        if filename:
            normalized = filename.lstrip("./")
            file_path = session_dir / Path(normalized)
            try:
                if file_path.exists():
                    file_content = file_path.read_text(encoding="utf-8")
            except Exception as exc:  # pragma: no cover - log for debugging
                print(
                    f"[LANDING_PAGES] Warning: failed to read section file {file_path}: {exc}"
                )

        payload.append(
            {
                "id": section_id,
                "name": section_name,
                "component_name": component_name,
                "filename": filename,
                "file_content": file_content,
            }
        )

    return payload


# Landing pages are created automatically by the agent system at /init
# This endpoint is not exposed - use /v1/agent/init to start a new landing page generation


@router.get("/", response_model=LandingPageList)
async def list_landing_pages(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status_filter: LandingPageStatus | None = Query(
        None, description="Filter by status"
    ),
):
    """
    Get all landing pages for the current user with pagination.

    Args:
        current_user: Current authenticated user
        page: Page number (starts at 1)
        page_size: Number of items per page
        status_filter: Optional status filter

    Returns:
        Paginated list of landing pages
    """
    skip = (page - 1) * page_size

    landing_pages, total = get_user_landing_pages(
        current_user.id, skip=skip, limit=page_size, status_filter=status_filter
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # Convert to public model
    items = [
        LandingPage(
            id=lp.id,
            user_id=lp.user_id,
            session_id=lp.session_id,
            status=LandingPageStatus(lp.status),
            preview_url=lp.preview_url,
            deployment_url=lp.deployment_url,
            business_data=lp.business_data,
            design_blueprint_pdf_url=lp.design_blueprint_pdf_url,
            created_at=lp.created_at,
            updated_at=lp.updated_at,
        )
        for lp in landing_pages
    ]

    return LandingPageList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{landing_page_id}", response_model=LandingPage)
async def get_landing_page(
    landing_page_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific landing page by ID.

    Args:
        landing_page_id: The landing page ID
        current_user: Current authenticated user

    Returns:
        The landing page

    Raises:
        HTTPException: If not found or not authorized
    """
    landing_page = get_landing_page_by_id(landing_page_id)

    if landing_page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landing page not found",
        )

    # Check authorization
    if landing_page.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this landing page",
        )

    return LandingPage(
        id=landing_page.id,
        user_id=landing_page.user_id,
        session_id=landing_page.session_id,
        status=LandingPageStatus(landing_page.status),
        preview_url=landing_page.preview_url,
        deployment_url=landing_page.deployment_url,
        business_data=landing_page.business_data,
        design_blueprint_pdf_url=landing_page.design_blueprint_pdf_url,
        created_at=landing_page.created_at,
        updated_at=landing_page.updated_at,
        sections=_build_sections_payload(landing_page),
    )


@router.get("/session/{session_id}", response_model=LandingPage)
async def get_landing_page_by_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a landing page by session ID.

    Args:
        session_id: The session ID
        current_user: Current authenticated user

    Returns:
        The landing page

    Raises:
        HTTPException: If not found or not authorized
    """
    landing_page = get_landing_page_by_session_id(session_id)

    if landing_page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landing page not found",
        )

    # Check authorization
    if landing_page.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this landing page",
        )

    return LandingPage(
        id=landing_page.id,
        user_id=landing_page.user_id,
        session_id=landing_page.session_id,
        status=LandingPageStatus(landing_page.status),
        preview_url=landing_page.preview_url,
        deployment_url=landing_page.deployment_url,
        business_data=landing_page.business_data,
        design_blueprint_pdf_url=landing_page.design_blueprint_pdf_url,
        created_at=landing_page.created_at,
        updated_at=landing_page.updated_at,
        sections=_build_sections_payload(landing_page),
    )


@router.patch("/{landing_page_id}", response_model=LandingPage)
async def update_landing_page_endpoint(
    landing_page_id: str,
    update_data: LandingPageUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Update a landing page.

    Args:
        landing_page_id: The landing page ID
        update_data: Data to update
        current_user: Current authenticated user

    Returns:
        The updated landing page

    Raises:
        HTTPException: If not found or not authorized
    """
    # First check if landing page exists and user is authorized
    existing = get_landing_page_by_id(landing_page_id)

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landing page not found",
        )

    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this landing page",
        )

    # Update the landing page
    updated = update_landing_page(landing_page_id, update_data)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landing page not found",
        )

    return LandingPage(
        id=updated.id,
        user_id=updated.user_id,
        session_id=updated.session_id,
        status=updated.status,
        preview_url=updated.preview_url,
        deployment_url=updated.deployment_url,
        business_data=updated.business_data,
        design_blueprint_pdf_url=updated.design_blueprint_pdf_url,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        sections=_build_sections_payload(updated),
    )


@router.delete("/{landing_page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_landing_page_endpoint(
    landing_page_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a landing page.

    Args:
        landing_page_id: The landing page ID
        current_user: Current authenticated user

    Raises:
        HTTPException: If not found or not authorized
    """
    deleted = delete_landing_page(landing_page_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landing page not found or not authorized",
        )
