"""Alert management endpoints for UOIH API."""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Alert
from ..schemas import (
    ActiveAlertsResponse,
    AlertAcknowledge,
    AlertAcknowledgeResponse,
    AlertCreate,
    AlertResponse,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])
logger = structlog.get_logger()


@router.get("/active", response_model=ActiveAlertsResponse)
async def get_active_alerts(
    facility_id: str = Query(..., description="Facility identifier"),
    session: AsyncSession = Depends(get_session),
) -> ActiveAlertsResponse:
    """
    Get all active (unacknowledged) alerts for a facility.

    Returns alerts sorted by severity (CRITICAL first) then by creation time.
    """
    # Define severity order for sorting
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    query = (
        select(Alert)
        .where(Alert.facility_id == facility_id)
        .where(Alert.status == "ACTIVE")
        .order_by(Alert.created_at.desc())
    )

    result = await session.execute(query)
    alerts = result.scalars().all()

    # Sort by severity then by created_at
    sorted_alerts = sorted(
        alerts,
        key=lambda a: (severity_order.get(a.severity, 99), -a.created_at.timestamp()),
    )

    return ActiveAlertsResponse(
        facility_id=facility_id,
        total=len(sorted_alerts),
        alerts=[AlertResponse.model_validate(a) for a in sorted_alerts],
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertAcknowledgeResponse)
async def acknowledge_alert(
    alert_id: UUID,
    body: AlertAcknowledge,
    session: AsyncSession = Depends(get_session),
) -> AlertAcknowledgeResponse:
    """
    Acknowledge an alert.

    Sets the alert status to ACKNOWLEDGED and records the actor and timestamp.
    """
    query = select(Alert).where(Alert.id == alert_id)
    result = await session.execute(query)
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=f"Alert cannot be acknowledged (current status: {alert.status})",
        )

    # Update alert
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_by = body.actor
    alert.acknowledged_at = datetime.now(UTC)

    await session.flush()

    logger.info(
        "alert_acknowledged",
        alert_id=str(alert_id),
        actor=body.actor,
        facility_id=alert.facility_id,
    )

    return AlertAcknowledgeResponse(
        id=alert.id,
        status=alert.status,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
    )


@router.post("", response_model=AlertResponse, status_code=201)
async def create_alert(
    body: AlertCreate,
    session: AsyncSession = Depends(get_session),
) -> AlertResponse:
    """
    Create a new alert.

    Used internally by Airflow DAGs and other services to create alerts.
    """
    alert = Alert(
        facility_id=body.facility_id,
        module_id=body.module_id,
        alert_type=body.alert_type,
        severity=body.severity,
        title=body.title,
        body=body.body,
        alert_metadata=body.alert_metadata,
        status="ACTIVE",
    )

    session.add(alert)
    await session.flush()
    await session.refresh(alert)

    logger.info(
        "alert_created",
        alert_id=str(alert.id),
        severity=alert.severity,
        facility_id=alert.facility_id,
        alert_type=alert.alert_type,
    )

    return AlertResponse.model_validate(alert)
