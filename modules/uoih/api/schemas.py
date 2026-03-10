"""Pydantic schemas for UOIH API."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- KPI Schemas ---
class DailyKPI(BaseModel):
    """Daily KPI metrics for a facility."""

    facility_id: str
    date: date
    total_movements: int = Field(ge=0)
    picks_completed: int = Field(ge=0)
    inventory_accuracy_pct: float = Field(ge=0, le=100)
    orders_fulfilled: int = Field(ge=0)


class DailyKPIResponse(BaseModel):
    """Response for daily KPIs endpoint."""

    facility_id: str
    date_from: date
    date_to: date
    kpis: list[DailyKPI]


class InventoryAccuracyPoint(BaseModel):
    """Single data point for inventory accuracy trend."""

    date: date
    accuracy_pct: float = Field(ge=0, le=100)
    cycle_counts: int = Field(ge=0)


class InventoryAccuracyResponse(BaseModel):
    """Response for inventory accuracy trend."""

    facility_id: str
    period_days: int = 30
    trend: list[InventoryAccuracyPoint]
    average_accuracy_pct: float


# --- Alert Schemas ---
class AlertBase(BaseModel):
    """Base alert schema."""

    facility_id: str
    module_id: str
    alert_type: str
    severity: str = Field(pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    title: str = Field(max_length=255)
    body: str | None = None
    alert_metadata: dict | None = None


class AlertCreate(AlertBase):
    """Schema for creating alerts."""

    pass


class AlertResponse(AlertBase):
    """Alert response schema."""

    id: UUID
    status: str
    created_at: datetime
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None

    model_config = {"from_attributes": True}


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""

    actor: str = Field(min_length=1, max_length=100)


class AlertAcknowledgeResponse(BaseModel):
    """Response after acknowledging an alert."""

    id: UUID
    status: str
    acknowledged_by: str
    acknowledged_at: datetime


class ActiveAlertsResponse(BaseModel):
    """Response for active alerts."""

    facility_id: str
    total: int
    alerts: list[AlertResponse]


# --- Health ---
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
