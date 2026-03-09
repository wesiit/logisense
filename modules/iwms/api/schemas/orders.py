"""Pydantic schemas for orders."""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .common import BaseSchema
from .inventory import SKUResponse


class OrderType(str, Enum):
    """Order types."""

    OUTBOUND = "OUTBOUND"
    TRANSFER = "TRANSFER"
    RETURN = "RETURN"


class OrderStatus(str, Enum):
    """Order statuses."""

    PENDING = "PENDING"
    WAVED = "WAVED"
    PICKING = "PICKING"
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    CANCELLED = "CANCELLED"


class OrderLineStatus(str, Enum):
    """Order line statuses."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    SHORT = "SHORT"


# ============================================================================
# Order Line Schemas
# ============================================================================


class OrderLineBase(BaseSchema):
    """Base order line schema."""

    sku_id: UUID
    lot_number: str | None = Field(None, max_length=100)
    quantity_ordered: int = Field(..., gt=0)


class OrderLineCreate(OrderLineBase):
    """Schema for creating an order line."""

    pass


class OrderLineResponse(OrderLineBase):
    """Schema for order line response."""

    id: UUID
    order_id: UUID
    quantity_picked: int = 0
    status: OrderLineStatus = OrderLineStatus.PENDING
    created_at: datetime

    # Nested
    sku: SKUResponse | None = None


# ============================================================================
# Order Schemas
# ============================================================================


class OrderBase(BaseSchema):
    """Base order schema."""

    facility_id: str = Field(..., max_length=50)
    order_number: str = Field(..., max_length=100)
    order_type: OrderType
    priority: int = Field(5, ge=1, le=10)
    customer_id: str | None = Field(None, max_length=100)
    carrier_code: str | None = Field(None, max_length=50)
    required_ship_date: date | None = None


class OrderCreate(OrderBase):
    """Schema for creating an order."""

    lines: list[OrderLineCreate] = Field(default_factory=list)


class OrderUpdate(BaseSchema):
    """Schema for updating an order."""

    priority: int | None = Field(None, ge=1, le=10)
    customer_id: str | None = None
    carrier_code: str | None = None
    required_ship_date: date | None = None
    status: OrderStatus | None = None


class OrderResponse(OrderBase):
    """Schema for order response."""

    id: UUID
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime
    updated_at: datetime | None = None

    # Nested
    order_lines: list[OrderLineResponse] | None = None


class OrderSummary(BaseSchema):
    """Summary order response without lines."""

    id: UUID
    facility_id: str
    order_number: str
    order_type: OrderType
    status: OrderStatus
    priority: int
    customer_id: str | None = None
    required_ship_date: date | None = None
    created_at: datetime
    line_count: int = 0
    total_units: int = 0
