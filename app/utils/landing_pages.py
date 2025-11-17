"""Utility functions for landing page operations."""

from datetime import datetime
from typing import Optional
import uuid
from app.db import get_landing_pages_collection
from app.models.landing_page import (
    LandingPage,
    LandingPageCreate,
    LandingPageUpdate,
    LandingPageInDB,
    LandingPageStatus,
)


def create_landing_page(
    user_id: str, landing_page_data: LandingPageCreate
) -> Optional[LandingPage]:
    """
    Create a new landing page for a user.

    Args:
        user_id: The ID of the user creating the landing page
        landing_page_data: Landing page creation data

    Returns:
        The created landing page or None if database unavailable
    """
    collection = get_landing_pages_collection()
    if collection is None:
        return None

    landing_page_id = str(uuid.uuid4())
    now = datetime.utcnow()

    landing_page_doc = {
        "_id": landing_page_id,
        "user_id": user_id,
        "session_id": landing_page_data.session_id,
        "status": LandingPageStatus.PENDING.value,
        "preview_url": None,
        "deployment_url": None,
        "business_data": landing_page_data.business_data,
        "created_at": now,
        "updated_at": now,
    }

    collection.insert_one(landing_page_doc)

    return LandingPage(
        id=landing_page_id,
        user_id=user_id,
        session_id=landing_page_data.session_id,
        status=LandingPageStatus.PENDING,
        preview_url=None,
        deployment_url=None,
        business_data=landing_page_data.business_data,
        created_at=now,
        updated_at=now,
    )


def get_landing_page_by_id(landing_page_id: str) -> Optional[LandingPageInDB]:
    """
    Get a landing page by its ID.

    Args:
        landing_page_id: The landing page ID

    Returns:
        The landing page or None if not found
    """
    collection = get_landing_pages_collection()
    if collection is None:
        return None

    landing_page_data = collection.find_one({"_id": landing_page_id})
    if landing_page_data is None:
        return None

    return LandingPageInDB(**landing_page_data)


def get_landing_page_by_session_id(session_id: str) -> Optional[LandingPageInDB]:
    """
    Get a landing page by its session ID.

    Args:
        session_id: The session ID

    Returns:
        The landing page or None if not found
    """
    collection = get_landing_pages_collection()
    if collection is None:
        return None

    landing_page_data = collection.find_one({"session_id": session_id})
    if landing_page_data is None:
        return None

    return LandingPageInDB(**landing_page_data)


def get_user_landing_pages(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[LandingPageStatus] = None,
) -> tuple[list[LandingPageInDB], int]:
    """
    Get all landing pages for a user with pagination.

    Args:
        user_id: The user ID
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        status_filter: Optional status to filter by

    Returns:
        Tuple of (list of landing pages, total count)
    """
    collection = get_landing_pages_collection()
    if collection is None:
        return [], 0

    query = {"user_id": user_id}
    if status_filter:
        query["status"] = status_filter.value

    # Get total count
    total = collection.count_documents(query)

    # Get paginated results, sorted by created_at descending
    cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)

    landing_pages = [LandingPageInDB(**doc) for doc in cursor]

    return landing_pages, total


def update_landing_page(
    landing_page_id: str, update_data: LandingPageUpdate
) -> Optional[LandingPageInDB]:
    """
    Update a landing page.

    Args:
        landing_page_id: The landing page ID
        update_data: Data to update

    Returns:
        The updated landing page or None if not found
    """
    collection = get_landing_pages_collection()
    if collection is None:
        return None

    # Build update document
    update_doc = {"updated_at": datetime.utcnow()}

    if update_data.status is not None:
        update_doc["status"] = update_data.status.value
    if update_data.preview_url is not None:
        update_doc["preview_url"] = update_data.preview_url
    if update_data.deployment_url is not None:
        update_doc["deployment_url"] = update_data.deployment_url
    if update_data.business_data is not None:
        update_doc["business_data"] = update_data.business_data

    # Update the document
    result = collection.find_one_and_update(
        {"_id": landing_page_id}, {"$set": update_doc}, return_document=True
    )

    if result is None:
        return None

    return LandingPageInDB(**result)


def delete_landing_page(landing_page_id: str, user_id: str) -> bool:
    """
    Delete a landing page (only if owned by the user).

    Args:
        landing_page_id: The landing page ID
        user_id: The user ID (for authorization check)

    Returns:
        True if deleted, False otherwise
    """
    collection = get_landing_pages_collection()
    if collection is None:
        return False

    result = collection.delete_one({"_id": landing_page_id, "user_id": user_id})
    return result.deleted_count > 0


def update_landing_page_status(
    session_id: str,
    status: LandingPageStatus,
    preview_url: Optional[str] = None,
    deployment_url: Optional[str] = None,
) -> Optional[LandingPageInDB]:
    """
    Update landing page status by session ID.
    Convenience function for updating during generation/deployment.

    Args:
        session_id: The session ID
        status: New status
        preview_url: Optional preview URL
        deployment_url: Optional deployment URL

    Returns:
        The updated landing page or None if not found
    """
    collection = get_landing_pages_collection()
    if collection is None:
        return None

    update_doc = {"status": status.value, "updated_at": datetime.utcnow()}

    if preview_url is not None:
        update_doc["preview_url"] = preview_url
    if deployment_url is not None:
        update_doc["deployment_url"] = deployment_url

    result = collection.find_one_and_update(
        {"session_id": session_id}, {"$set": update_doc}, return_document=True
    )

    if result is None:
        return None

    return LandingPageInDB(**result)
