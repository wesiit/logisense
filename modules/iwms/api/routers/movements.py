"""Inventory movement endpoints."""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ..auth import TokenPayload, validate_token
from ..db import DbSession
from ..schemas.common import PaginatedResponse
from ..schemas.inventory import (
    InventoryMovementCreate,
    InventoryMovementResponse,
    MovementType,
)
from ..services.inventory_service import InventoryService
from ..services.kafka_producer import KafkaProducer, get_kafka_producer

router = APIRouter(prefix="/inventory/movements", tags=["Inventory Movements"])


def get_inventory_service(
    db: DbSession,
    kafka: KafkaProducer = Depends(get_kafka_producer),
) -> InventoryService:
    """Dependency to get inventory service with Kafka."""
    return InventoryService(db, kafka)


InventorySvc = Annotated[InventoryService, Depends(get_inventory_service)]
CurrentUser = Annotated[TokenPayload, Depends(validate_token)]


@router.post(
    "",
    response_model=InventoryMovementResponse,
    status_code=201,
)
async def create_movement(
    data: InventoryMovementCreate,
    service: InventorySvc,
    user: CurrentUser,
) -> InventoryMovementResponse:
    """
    Record an inventory movement.

    Movement types:
    - RECEIVE: Goods received into a location
    - PICK: Goods picked from a location
    - PUTAWAY: Goods put away to a storage location
    - TRANSFER: Goods moved between locations
    - ADJUST: Inventory adjustment (sets absolute quantity)
    - CYCLE_COUNT: Cycle count update

    This endpoint:
    1. Creates a movement record
    2. Updates affected inventory positions
    3. Publishes event to Kafka topic `logisense.iwms.inventory.movement`
    """
    # Set performed_by from token if not provided
    if not data.performed_by:
        data.performed_by = user.preferred_username or user.sub

    movement = await service.create_movement(data)
    return InventoryMovementResponse.model_validate(movement)


@router.get("", response_model=PaginatedResponse[InventoryMovementResponse])
async def list_movements(
    service: InventorySvc,
    _user: CurrentUser,
    facility_id: str = Query(..., description="Facility ID to filter by"),
    movement_type: MovementType | None = Query(
        None, description="Filter by movement type"
    ),
    sku_id: UUID | None = Query(None, description="Filter by SKU"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[InventoryMovementResponse]:
    """List inventory movements with filtering and pagination."""
    offset = (page - 1) * page_size
    movements, total = await service.list_movements(
        facility_id=facility_id,
        movement_type=movement_type,
        sku_id=sku_id,
        include_relations=True,
        offset=offset,
        limit=page_size,
    )

    return PaginatedResponse(
        items=[InventoryMovementResponse.model_validate(m) for m in movements],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
