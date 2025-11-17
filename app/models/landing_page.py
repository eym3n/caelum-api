"""Landing page models and schemas."""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class LandingPageStatus(str, Enum):
    """Status enum for landing page generation."""
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    FAILED = "failed"


class LandingPageBase(BaseModel):
    """Base landing page schema with common fields."""
    session_id: str
    status: LandingPageStatus = LandingPageStatus.PENDING
    preview_url: Optional[str] = None
    deployment_url: Optional[str] = None
    business_data: Optional[dict] = None


class LandingPageCreate(BaseModel):
    """Schema for creating a new landing page."""
    session_id: str
    business_data: Optional[dict] = None


class LandingPageUpdate(BaseModel):
    """Schema for updating a landing page."""
    status: Optional[LandingPageStatus] = None
    preview_url: Optional[str] = None
    deployment_url: Optional[str] = None
    business_data: Optional[dict] = None


class LandingPageInDB(LandingPageBase):
    """Landing page schema as stored in database."""
    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(populate_by_name=True)


class LandingPage(LandingPageBase):
    """Landing page schema for API responses (public-facing)."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LandingPageList(BaseModel):
    """Schema for paginated landing page list."""
    items: list[LandingPage]
    total: int
    page: int
    page_size: int
    total_pages: int

