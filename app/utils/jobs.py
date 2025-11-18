"""Utility functions for job and job-event persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Tuple, List
import uuid

from app.db import get_jobs_collection
from app.models.job import Job, JobInDB, JobCreate, JobEvent, JobStatus, JobType


def create_job(job_data: JobCreate) -> Optional[Job]:
    """
    Create a new job document in MongoDB.

    Returns:
        The created Job, or None if database unavailable.
    """
    collection = get_jobs_collection()
    if collection is None:
        return None

    job_id = str(uuid.uuid4())
    now = datetime.utcnow()

    doc = {
        "_id": job_id,
        "type": job_data.type.value if isinstance(job_data.type, JobType) else job_data.type,
        "status": JobStatus.RUNNING.value,
        "session_id": job_data.session_id,
        "user_id": job_data.user_id,
        "title": job_data.title,
        "description": job_data.description,
        "initial_payload": job_data.initial_payload or {},
        "events": [],
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }

    collection.insert_one(doc)

    return Job(
        id=job_id,
        type=JobType(doc["type"]),
        status=JobStatus.RUNNING,
        session_id=doc["session_id"],
        user_id=doc["user_id"],
        title=doc["title"],
        description=doc["description"],
        events=[],
        created_at=now,
        updated_at=now,
        error_message=None,
    )


def _normalize_event_type(node: str, raw_event_type: str | None = None) -> str:
    """Best-effort mapping of node/update to a compact event type string."""
    if raw_event_type:
        return raw_event_type
    # Minimal heuristic for now
    if node in {"__start__", "__end__"}:
        return "graph"
    return "node"


def append_job_event(
    job_id: str,
    *,
    node: str,
    message: str = "",
    event_type: Optional[str] = None,
    data: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Append a single event to a job's events array.

    Returns:
        True if the job was updated, False otherwise.
    """
    collection = get_jobs_collection()
    if collection is None:
        return False

    event_id = str(uuid.uuid4())
    now = datetime.utcnow()

    event_doc = {
        "id": event_id,
        "node": node,
        "timestamp": now,
        "event_type": _normalize_event_type(node, event_type),
        "message": message or "",
        "data": data or {},
    }

    result = collection.update_one(
        {"_id": job_id},
        {
            "$push": {"events": event_doc},
            "$set": {"updated_at": now},
        },
    )

    return result.modified_count == 1


def log_job_event(
    job_id: str | None,
    *,
    node: str,
    message: str = "",
    event_type: Optional[str] = None,
    data: Optional[dict[str, Any]] = None,
) -> None:
    """
    Convenience helper for logging a job event when you already have a job id.

    Safe to call from anywhere (nodes, runners); no-op if job_id is missing.
    """
    if not job_id:
        return
    try:
        append_job_event(
            job_id,
            node=node,
            message=message,
            event_type=event_type,
            data=data or {},
        )
    except Exception as e:
        # Never let logging failures break the graph.
        print(f"[JOBS] Warning: failed to log job event for node '{node}': {e}")


def update_job_status(
    job_id: str,
    *,
    status: JobStatus,
    error_message: Optional[str] = None,
) -> bool:
    """
    Update job status (and optional error message).

    Returns:
        True if the job was updated, False otherwise.
    """
    collection = get_jobs_collection()
    if collection is None:
        return False

    now = datetime.utcnow()
    update_doc: dict[str, Any] = {
        "status": status.value if isinstance(status, JobStatus) else status,
        "updated_at": now,
    }
    if error_message is not None:
        update_doc["error_message"] = error_message

    result = collection.update_one(
        {"_id": job_id},
        {"$set": update_doc},
    )
    return result.modified_count == 1


def get_job(job_id: str, *, user_id: Optional[str] = None) -> Optional[JobInDB]:
    """
    Fetch a single job by id (and optional user ownership).

    Returns:
        JobInDB or None.
    """
    collection = get_jobs_collection()
    if collection is None:
        return None

    query: dict[str, Any] = {"_id": job_id}
    if user_id is not None:
        query["user_id"] = user_id

    doc = collection.find_one(query)
    if not doc:
        return None

    # Normalize events into JobEvent models
    events = []
    for ev in doc.get("events", []):
        events.append(
            JobEvent(
                id=ev.get("id", ""),
                node=ev.get("node", ""),
                timestamp=ev.get("timestamp"),
                event_type=ev.get("event_type", ""),
                message=ev.get("message", ""),
                data=ev.get("data", {}) or {},
            )
        )

    return JobInDB(
        _id=str(doc.get("_id")),
        type=doc.get("type"),
        status=doc.get("status"),
        session_id=doc.get("session_id"),
        user_id=doc.get("user_id"),
        title=doc.get("title"),
        description=doc.get("description"),
        events=events,
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
        error_message=doc.get("error_message"),
    )


def list_jobs_for_user(
    user_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[JobInDB], int]:
    """
    List jobs for a given user with basic pagination.

    Returns:
        (jobs, total_count)
    """
    collection = get_jobs_collection()
    if collection is None:
        return [], 0

    page = max(page, 1)
    page_size = max(page_size, 1)
    skip = (page - 1) * page_size

    query = {"user_id": user_id}

    total = collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )

    items: List[JobInDB] = []
    for doc in cursor:
        events = []
        for ev in doc.get("events", []):
            events.append(
                JobEvent(
                    id=ev.get("id", ""),
                    node=ev.get("node", ""),
                    timestamp=ev.get("timestamp"),
                    event_type=ev.get("event_type", ""),
                    message=ev.get("message", ""),
                    data=ev.get("data", {}) or {},
                )
            )

        items.append(
            JobInDB(
                _id=str(doc.get("_id")),
                type=doc.get("type"),
                status=doc.get("status"),
                session_id=doc.get("session_id"),
                user_id=doc.get("user_id"),
                title=doc.get("title"),
                description=doc.get("description"),
                events=events,
                created_at=doc.get("created_at"),
                updated_at=doc.get("updated_at"),
                error_message=doc.get("error_message"),
            )
        )

    return items, total


