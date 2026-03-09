"""Pydantic schemas for task management."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .common import BaseSchema
from .inventory import LocationResponse, SKUResponse


class TaskType(str, Enum):
    """Task types."""

    PICK = "PICK"
    PUTAWAY = "PUTAWAY"
    RECEIVE = "RECEIVE"
    CYCLE_COUNT = "CYCLE_COUNT"
    REPLENISH = "REPLENISH"


class TaskStatus(str, Enum):
    """Task statuses."""

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"


# ============================================================================
# Task Schemas
# ============================================================================


class TaskBase(BaseSchema):
    """Base task schema."""

    facility_id: str = Field(..., max_length=50)
    task_type: TaskType
    sku_id: UUID
    quantity: int = Field(..., gt=0)
    lot_number: str | None = Field(None, max_length=100)
    from_location_id: UUID | None = None
    to_location_id: UUID | None = None
    priority: int = Field(5, ge=1, le=10)


class TaskCreate(TaskBase):
    """Schema for creating a task."""

    wave_id: UUID | None = None


class TaskAssign(BaseSchema):
    """Schema for assigning a task."""

    assigned_to: str = Field(..., max_length=100)


class TaskComplete(BaseSchema):
    """Schema for completing a task."""

    quantity_completed: int = Field(..., ge=0)
    notes: str | None = None


class TaskResponse(TaskBase):
    """Schema for task response."""

    id: UUID
    wave_id: UUID | None = None
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    # Nested (optional)
    from_location: LocationResponse | None = None
    to_location: LocationResponse | None = None
    sku: SKUResponse | None = None


class TaskSummary(BaseSchema):
    """Summary task response."""

    id: UUID
    facility_id: str
    wave_id: UUID | None = None
    task_type: TaskType
    status: TaskStatus
    sku_id: UUID
    quantity: int
    assigned_to: str | None = None
    priority: int
    created_at: datetime
