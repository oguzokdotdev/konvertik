from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ConversionTask(SQLModel, table=True):
    """Conversion task stored in the database."""

    __tablename__ = "conversion_tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    file_name: str = Field(index=True)
    file_size: int = Field(gt=0)
    target_format: str = Field(max_length=10)
    plan_tier: str = Field(default="free")

    status: str = Field(default="pending")
    error_message: Optional[str] = Field(default=None)

    input_path: Optional[str] = Field(default=None)
    output_path: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
