"""Job models and schemas for asynchronous graph executions."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, List

from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    """Status enum for graph execution jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Type of job – maps to how the graph was invoked."""

    INIT = "init"
    CHAT = "chat"


class JobEvent(BaseModel):
    """Single node execution event within a job."""

    id: str = Field(..., description="Unique event identifier (UUID).")
    node: str = Field(..., description="Name of the graph node that produced this event.")
    timestamp: datetime = Field(..., description="When this event was recorded (UTC).")
    event_type: str = Field(
        ..., description="Type of event (e.g. node_started, node_completed, error)."
    )
    message: str = Field(
        "", description="Short human-readable summary or output for this event."
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured payload for this event (partial node state, metadata, etc.).",
    )


class JobBase(BaseModel):
    """Base schema with fields common to all jobs."""

    type: JobType
    status: JobStatus = JobStatus.PENDING
    session_id: str
    user_id: Optional[str] = None
    # Optional user-facing metadata (e.g. original prompt)
    title: Optional[str] = None
    description: Optional[str] = None


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    type: JobType
    session_id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    # Optional initial payload snapshot (e.g. init/chat payload)
    initial_payload: Optional[dict[str, Any]] = None


class JobInDB(JobBase):
    """Job schema as stored in MongoDB."""

    id: str = Field(alias="_id")
    events: List[JobEvent] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class Job(JobBase):
    """Job schema for API responses."""

    id: str
    events: List[JobEvent] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobList(BaseModel):
    """Schema for paginated job list responses."""

    items: List[Job]
    total: int
    page: int
    page_size: int
    total_pages: int


