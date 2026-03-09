"""Pydantic schemas for inventory operations."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import Field

from .common import BaseSchema


class MovementType(str, Enum):
    """Inventory movement types."""

    RECEIVE = "RECEIVE"
    PICK = "PICK"
    PUTAWAY = "PUTAWAY"
    TRANSFER = "TRANSFER"
    ADJUST = "ADJUST"
    CYCLE_COUNT = "CYCLE_COUNT"


# ============================================================================
# Location Schemas
# ============================================================================


class LocationBase(BaseSchema):
    """Base location schema."""

    facility_id: str = Field(..., max_length=50)
    zone_id: str | None = Field(None, max_length=50)
    aisle: str | None = Field(None, max_length=20)
    bay: str | None = Field(None, max_length=20)
    level: str | None = Field(None, max_length=20)
    bin: str | None = Field(None, max_length=20)
    location_code: str = Field(..., max_length=100)
    location_type: str | None = Field(None, max_length=50)
    max_weight_kg: Decimal | None = Field(None, ge=0)
    is_active: bool = True


class LocationCreate(LocationBase):
    """Schema for creating a location."""

    pass


class LocationResponse(LocationBase):
    """Schema for location response."""

    id: UUID
    created_at: datetime


# ============================================================================
# SKU Schemas
# ============================================================================


class SKUBase(BaseSchema):
    """Base SKU schema."""

    sku_code: str = Field(..., max_length=100)
    sku_name: str = Field(..., max_length=500)
    category_l1: str | None = Field(None, max_length=100)
    category_l2: str | None = Field(None, max_length=100)
    unit_of_measure: str | None = Field(None, max_length=20)
    weight_kg: Decimal | None = Field(None, ge=0)
    is_perishable: bool = False
    temperature_zone: str | None = Field(None, max_length=50)
    reorder_point: int | None = Field(None, ge=0)
    min_order_qty: int | None = Field(None, ge=1)
    is_active: bool = True


class SKUCreate(SKUBase):
    """Schema for creating a SKU."""

    pass


class SKUResponse(SKUBase):
    """Schema for SKU response."""

    id: UUID
    created_at: datetime


# ============================================================================
# Inventory Position Schemas
# ============================================================================


class InventoryPositionBase(BaseSchema):
    """Base inventory position schema."""

    facility_id: str = Field(..., max_length=50)
    location_id: UUID
    sku_id: UUID
    lot_number: str | None = Field(None, max_length=100)
    quantity: int = Field(0, ge=0)
    quantity_reserved: int = Field(0, ge=0)
    expiry_date: date | None = None


class InventoryPositionCreate(InventoryPositionBase):
    """Schema for creating an inventory position."""

    pass


class InventoryPositionUpdate(BaseSchema):
    """Schema for updating an inventory position."""

    quantity: int | None = Field(None, ge=0)
    quantity_reserved: int | None = Field(None, ge=0)
    expiry_date: date | None = None


class InventoryPositionResponse(InventoryPositionBase):
    """Schema for inventory position response."""

    id: UUID
    received_at: datetime | None = None
    last_counted_at: datetime | None = None
    last_movement_at: datetime | None = None
    created_at: datetime

    # Nested responses (optional)
    location: LocationResponse | None = None
    sku: SKUResponse | None = None


# ============================================================================
# Inventory Movement Schemas
# ============================================================================


class InventoryMovementBase(BaseSchema):
    """Base inventory movement schema."""

    facility_id: str = Field(..., max_length=50)
    movement_type: MovementType
    sku_id: UUID
    quantity: int = Field(..., gt=0)
    lot_number: str | None = Field(None, max_length=100)
    from_location_id: UUID | None = None
    to_location_id: UUID | None = None
    reference_id: str | None = Field(None, max_length=100)
    reference_type: str | None = Field(None, max_length=50)
    performed_by: str | None = Field(None, max_length=100)
    notes: str | None = None


class InventoryMovementCreate(InventoryMovementBase):
    """Schema for creating an inventory movement."""

    pass


class InventoryMovementResponse(InventoryMovementBase):
    """Schema for inventory movement response."""

    id: UUID
    performed_at: datetime

    # Nested responses (optional)
    from_location: LocationResponse | None = None
    to_location: LocationResponse | None = None
    sku: SKUResponse | None = None
