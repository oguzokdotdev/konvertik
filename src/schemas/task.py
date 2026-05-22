from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UploadRequest(BaseModel):
    """Request schema for creating a conversion task."""

    target_format: str = Field(max_length=10)
    plan_tier: Literal["free", "pro"] = Field(default="free")


class TaskResponse(BaseModel):
    """Response schema for a conversion task."""

    id: UUID
    file_name: str
    file_size: int
    target_format: str
    plan_tier: Literal["free", "pro"]
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DownloadResponse(BaseModel):
    """Response schema for a download link."""

    task_id: UUID
    download_url: str
    file_name: str