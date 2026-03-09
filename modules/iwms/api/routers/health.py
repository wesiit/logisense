"""Health check endpoints."""

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import text

from ..db import DbSession

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str = "iwms-api"
    version: str = "0.1.0"


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str
    database: str
    kafka: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check.

    Returns service status without checking dependencies.
    """
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(db: DbSession, response: Response) -> ReadyResponse:
    """
    Readiness check with dependency validation.

    Checks database connectivity and other critical dependencies.
    """
    result = ReadyResponse(status="ok", database="unknown", kafka="unknown")

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        result.database = "ok"
    except Exception:
        result.database = "error"
        result.status = "degraded"

    # Kafka check is best-effort (producer might not be initialized)
    try:
        from ..services.kafka_producer import get_kafka_producer

        producer = get_kafka_producer()
        result.kafka = "ok" if producer._started else "not_started"
    except RuntimeError:
        result.kafka = "not_initialized"

    if result.status != "ok":
        response.status_code = 503

    return result
