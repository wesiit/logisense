"""Wave management endpoints."""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import TokenPayload, validate_token
from ..db import DbSession
from ..schemas.common import PaginatedResponse
from ..schemas.waves import WaveCreate, WaveResponse, WaveStatus, WaveWithTasks
from ..services.kafka_producer import KafkaProducer, get_kafka_producer
from ..services.wave_service import WaveService

router = APIRouter(prefix="/waves", tags=["Waves"])


def get_wave_service(
    db: DbSession,
    kafka: KafkaProducer = Depends(get_kafka_producer),
) -> WaveService:
    """Dependency to get wave service."""
    return WaveService(db, kafka)


WaveSvc = Annotated[WaveService, Depends(get_wave_service)]
CurrentUser = Annotated[TokenPayload, Depends(validate_token)]


@router.post(
    "",
    response_model=WaveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wave(
    data: WaveCreate,
    service: WaveSvc,
    user: CurrentUser,
) -> WaveResponse:
    """
    Create a new wave from a list of order IDs.

    This endpoint:
    1. Loads all pending order lines for the given orders
    2. Groups tasks by zone (from location_code prefix)
    3. Creates one PICK task per order line
    4. Sets wave status to DRAFT
    """
    # Set created_by from token if not provided
    if not data.created_by:
        data.created_by = user.preferred_username or user.sub

    try:
        wave = await service.create_wave(data)
        return WaveResponse.model_validate(wave)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=PaginatedResponse[WaveResponse])
async def list_waves(
    service: WaveSvc,
    _user: CurrentUser,
    facility_id: str = Query(..., description="Facility ID to filter by"),
    status_filter: WaveStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[WaveResponse]:
    """List waves with filtering and pagination."""
    offset = (page - 1) * page_size
    waves, total = await service.list_waves(
        facility_id=facility_id,
        status=status_filter,
        offset=offset,
        limit=page_size,
    )

    return PaginatedResponse(
        items=[WaveResponse.model_validate(w) for w in waves],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{wave_id}", response_model=WaveWithTasks)
async def get_wave(
    wave_id: UUID,
    service: WaveSvc,
    _user: CurrentUser,
) -> WaveWithTasks:
    """Get a specific wave by ID with all tasks."""
    wave = await service.get_wave(wave_id, include_tasks=True)
    if not wave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wave not found",
        )

    response = WaveWithTasks.model_validate(wave)
    response.task_count = len(wave.tasks) if wave.tasks else 0
    return response


@router.post("/{wave_id}/release", response_model=WaveWithTasks)
async def release_wave(
    wave_id: UUID,
    service: WaveSvc,
    user: CurrentUser,
) -> WaveWithTasks:
    """
    Release a wave for execution.

    This endpoint:
    1. Sets wave status to RELEASED
    2. Sets released_at timestamp
    3. Publishes event to Kafka topic `logisense.iwms.wave.released`
    4. Returns wave with task count
    """
    released_by = user.preferred_username or user.sub

    try:
        wave = await service.release_wave(wave_id, released_by=released_by)
        if not wave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wave not found",
            )

        response = WaveWithTasks.model_validate(wave)
        response.task_count = len(wave.tasks) if wave.tasks else 0
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{wave_id}/complete", response_model=WaveResponse)
async def complete_wave(
    wave_id: UUID,
    service: WaveSvc,
    _user: CurrentUser,
) -> WaveResponse:
    """Mark a wave as complete."""
    try:
        wave = await service.complete_wave(wave_id)
        if not wave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wave not found",
            )
        return WaveResponse.model_validate(wave)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{wave_id}/progress")
async def get_wave_progress(
    wave_id: UUID,
    service: WaveSvc,
    _user: CurrentUser,
) -> dict:
    """Get wave progress statistics."""
    progress = await service.get_wave_progress(wave_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wave not found",
        )
    return progress
