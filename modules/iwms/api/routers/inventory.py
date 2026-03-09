"""Inventory management endpoints."""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import TokenPayload, validate_token
from ..db import DbSession
from ..schemas.common import PaginatedResponse
from ..schemas.inventory import (
    InventoryPositionCreate,
    InventoryPositionResponse,
    InventoryPositionUpdate,
    LocationCreate,
    LocationResponse,
    SKUCreate,
    SKUResponse,
)
from ..services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def get_inventory_service(db: DbSession) -> InventoryService:
    """Dependency to get inventory service."""
    return InventoryService(db)


InventorySvc = Annotated[InventoryService, Depends(get_inventory_service)]
CurrentUser = Annotated[TokenPayload, Depends(validate_token)]


# =============================================================================
# Location Endpoints
# =============================================================================


@router.post(
    "/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_location(
    data: LocationCreate,
    service: InventorySvc,
    _user: CurrentUser,
) -> LocationResponse:
    """Create a new warehouse location."""
    location = await service.create_location(data)
    return LocationResponse.model_validate(location)


@router.get("/locations", response_model=PaginatedResponse[LocationResponse])
async def list_locations(
    service: InventorySvc,
    _user: CurrentUser,
    facility_id: str = Query(..., description="Facility ID to filter by"),
    zone_id: str | None = Query(None, description="Zone ID to filter by"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[LocationResponse]:
    """List locations with filtering and pagination."""
    offset = (page - 1) * page_size
    locations, total = await service.list_locations(
        facility_id=facility_id,
        zone_id=zone_id,
        is_active=is_active,
        offset=offset,
        limit=page_size,
    )

    return PaginatedResponse(
        items=[LocationResponse.model_validate(loc) for loc in locations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    service: InventorySvc,
    _user: CurrentUser,
) -> LocationResponse:
    """Get a specific location by ID."""
    location = await service.get_location(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )
    return LocationResponse.model_validate(location)


# =============================================================================
# SKU Endpoints
# =============================================================================


@router.post(
    "/skus",
    response_model=SKUResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sku(
    data: SKUCreate,
    service: InventorySvc,
    _user: CurrentUser,
) -> SKUResponse:
    """Create a new SKU."""
    sku = await service.create_sku(data)
    return SKUResponse.model_validate(sku)


@router.get("/skus", response_model=PaginatedResponse[SKUResponse])
async def list_skus(
    service: InventorySvc,
    _user: CurrentUser,
    category_l1: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[SKUResponse]:
    """List SKUs with filtering and pagination."""
    offset = (page - 1) * page_size
    skus, total = await service.list_skus(
        category_l1=category_l1,
        is_active=is_active,
        offset=offset,
        limit=page_size,
    )

    return PaginatedResponse(
        items=[SKUResponse.model_validate(sku) for sku in skus],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/skus/{sku_id}", response_model=SKUResponse)
async def get_sku(
    sku_id: UUID,
    service: InventorySvc,
    _user: CurrentUser,
) -> SKUResponse:
    """Get a specific SKU by ID."""
    sku = await service.get_sku(sku_id)
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )
    return SKUResponse.model_validate(sku)


# =============================================================================
# Inventory Position Endpoints
# =============================================================================


@router.post(
    "/positions",
    response_model=InventoryPositionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inventory_position(
    data: InventoryPositionCreate,
    service: InventorySvc,
    _user: CurrentUser,
) -> InventoryPositionResponse:
    """Create a new inventory position."""
    position = await service.create_inventory_position(data)
    return InventoryPositionResponse.model_validate(position)


@router.get("/positions", response_model=PaginatedResponse[InventoryPositionResponse])
async def list_inventory_positions(
    service: InventorySvc,
    _user: CurrentUser,
    facility_id: str = Query(..., description="Facility ID to filter by"),
    location_id: UUID | None = Query(None, description="Filter by location"),
    sku_id: UUID | None = Query(None, description="Filter by SKU"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[InventoryPositionResponse]:
    """List inventory positions with filtering and pagination."""
    offset = (page - 1) * page_size
    positions, total = await service.list_inventory_positions(
        facility_id=facility_id,
        location_id=location_id,
        sku_id=sku_id,
        include_relations=True,
        offset=offset,
        limit=page_size,
    )

    return PaginatedResponse(
        items=[InventoryPositionResponse.model_validate(pos) for pos in positions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/positions/{position_id}", response_model=InventoryPositionResponse)
async def get_inventory_position(
    position_id: UUID,
    service: InventorySvc,
    _user: CurrentUser,
) -> InventoryPositionResponse:
    """Get a specific inventory position by ID."""
    position = await service.get_inventory_position(position_id, include_relations=True)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory position not found",
        )
    return InventoryPositionResponse.model_validate(position)


@router.patch("/positions/{position_id}", response_model=InventoryPositionResponse)
async def update_inventory_position(
    position_id: UUID,
    data: InventoryPositionUpdate,
    service: InventorySvc,
    _user: CurrentUser,
) -> InventoryPositionResponse:
    """Update an inventory position."""
    position = await service.update_inventory_position(position_id, data)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory position not found",
        )
    return InventoryPositionResponse.model_validate(position)
