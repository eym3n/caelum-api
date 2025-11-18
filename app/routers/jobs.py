from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.deps import get_current_user
from app.models.user import User
from app.models.job import Job, JobList
from app.utils.jobs import get_job, list_jobs_for_user


router = APIRouter()


class JobResponse(BaseModel):
    job: Job


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_detail(job_id: str, current_user: User = Depends(get_current_user)):
    """
    Fetch a single job (graph execution) by id for the current user.

    The job contains overall status and the full event history for each node
    that has run so far.
    """
    job_in_db = get_job(job_id, user_id=current_user.id)
    if not job_in_db:
        raise HTTPException(status_code=404, detail="Job not found")

    # Convert JobInDB → Job
    job = Job(
        id=job_in_db.id,
        type=job_in_db.type,
        status=job_in_db.status,
        session_id=job_in_db.session_id,
        user_id=job_in_db.user_id,
        title=job_in_db.title,
        description=job_in_db.description,
        events=job_in_db.events,
        created_at=job_in_db.created_at,
        updated_at=job_in_db.updated_at,
        error_message=job_in_db.error_message,
    )
    return JobResponse(job=job)


@router.get("/jobs", response_model=JobList)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List jobs (graph executions) for the current user with basic pagination.
    """
    items, total = list_jobs_for_user(current_user.id, page=page, page_size=page_size)

    jobs: list[Job] = []
    for job_in_db in items:
        jobs.append(
            Job(
                id=job_in_db.id,
                type=job_in_db.type,
                status=job_in_db.status,
                session_id=job_in_db.session_id,
                user_id=job_in_db.user_id,
                title=job_in_db.title,
                description=job_in_db.description,
                events=job_in_db.events,
                created_at=job_in_db.created_at,
                updated_at=job_in_db.updated_at,
                error_message=job_in_db.error_message,
            )
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return JobList(
        items=jobs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


