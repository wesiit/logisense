"""Pydantic schemas for wave management."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .common import BaseSchema
from .tasks import TaskResponse


class WaveStatus(str, Enum):
    """Wave statuses."""

    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


# ============================================================================
# Wave Schemas
# ============================================================================


class WaveBase(BaseSchema):
    """Base wave schema."""

    facility_id: str = Field(..., max_length=50)
    wave_number: str = Field(..., max_length=100)


class WaveCreate(BaseSchema):
    """Schema for creating a wave."""

    facility_id: str = Field(..., max_length=50)
    order_ids: list[UUID] = Field(..., min_length=1)
    created_by: str | None = Field(None, max_length=100)


class WaveResponse(WaveBase):
    """Schema for wave response."""

    id: UUID
    status: WaveStatus = WaveStatus.DRAFT
    total_orders: int = 0
    total_lines: int = 0
    total_units: int = 0
    created_by: str | None = None
    released_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class WaveWithTasks(WaveResponse):
    """Wave response with tasks included."""

    tasks: list[TaskResponse] = Field(default_factory=list)
    task_count: int = 0


class WaveReleasedEvent(BaseSchema):
    """Kafka event for wave release."""

    event_type: str = "wave.released"
    wave_id: UUID
    wave_number: str
    facility_id: str
    total_orders: int
    total_lines: int
    total_units: int
    task_count: int
    released_at: datetime
    released_by: str | None = None
