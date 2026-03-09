"""Order management endpoints."""

import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..auth import TokenPayload, validate_token
from ..db import DbSession
from ..models import Order, OrderLine
from ..schemas.common import PaginatedResponse
from ..schemas.orders import (
    OrderCreate,
    OrderLineResponse,
    OrderResponse,
    OrderStatus,
    OrderType,
    OrderUpdate,
)

router = APIRouter(prefix="/orders", tags=["Orders"])

CurrentUser = Annotated[TokenPayload, Depends(validate_token)]


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    data: OrderCreate,
    db: DbSession,
    _user: CurrentUser,
) -> OrderResponse:
    """Create a new order with order lines."""
    # Create order
    order_data = data.model_dump(exclude={"lines"})
    order = Order(**order_data)
    db.add(order)
    await db.flush()

    # Create order lines
    for line_data in data.lines:
        line = OrderLine(
            order_id=order.id,
            **line_data.model_dump(),
        )
        db.add(line)

    await db.flush()

    # Reload with lines
    result = await db.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.order_lines).selectinload(OrderLine.sku))
    )
    order = result.scalar_one()

    return OrderResponse.model_validate(order)


@router.get("", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    db: DbSession,
    _user: CurrentUser,
    facility_id: str = Query(..., description="Facility ID to filter by"),
    status_filter: OrderStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    order_type: OrderType | None = Query(None, description="Filter by order type"),
    customer_id: str | None = Query(None, description="Filter by customer"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[OrderResponse]:
    """List orders with filtering and pagination."""
    query = select(Order).where(Order.facility_id == facility_id)

    if status_filter:
        query = query.where(Order.status == status_filter.value)
    if order_type:
        query = query.where(Order.order_type == order_type.value)
    if customer_id:
        query = query.where(Order.customer_id == customer_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results with order lines
    offset = (page - 1) * page_size
    query = (
        query.options(selectinload(Order.order_lines))
        .offset(offset)
        .limit(page_size)
        .order_by(Order.priority, Order.created_at.desc())
    )
    result = await db.execute(query)
    orders = list(result.scalars().all())

    return PaginatedResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: DbSession,
    _user: CurrentUser,
) -> OrderResponse:
    """Get a specific order by ID with all lines."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.order_lines).selectinload(OrderLine.sku))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return OrderResponse.model_validate(order)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    data: OrderUpdate,
    db: DbSession,
    _user: CurrentUser,
) -> OrderResponse:
    """Update an order."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.order_lines))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    order.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(order)

    return OrderResponse.model_validate(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    db: DbSession,
    _user: CurrentUser,
) -> None:
    """Delete an order (only if PENDING)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status != OrderStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete order in status {order.status}",
        )

    await db.delete(order)


@router.post(
    "/{order_id}/lines",
    response_model=OrderLineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_order_line(
    order_id: UUID,
    data: OrderLineResponse,
    db: DbSession,
    _user: CurrentUser,
) -> OrderLineResponse:
    """Add a line to an existing order."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status != OrderStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add lines to order in status {order.status}",
        )

    line = OrderLine(
        order_id=order_id,
        sku_id=data.sku_id,
        lot_number=data.lot_number,
        quantity_ordered=data.quantity_ordered,
    )
    db.add(line)
    await db.flush()
    await db.refresh(line)

    return OrderLineResponse.model_validate(line)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    db: DbSession,
    _user: CurrentUser,
) -> OrderResponse:
    """Cancel an order."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.order_lines))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status in [OrderStatus.DISPATCHED.value, OrderStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in status {order.status}",
        )

    order.status = OrderStatus.CANCELLED.value
    order.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(order)

    return OrderResponse.model_validate(order)
