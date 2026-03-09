"""SQLAlchemy ORM models for iWMS schema."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .db import Base

# Schema name
SCHEMA = "iwms"


class Location(Base):
    """Warehouse location master."""

    __tablename__ = "locations"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    facility_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    zone_id: Mapped[str | None] = mapped_column(String(50), index=True)
    aisle: Mapped[str | None] = mapped_column(String(20))
    bay: Mapped[str | None] = mapped_column(String(20))
    level: Mapped[str | None] = mapped_column(String(20))
    bin: Mapped[str | None] = mapped_column(String(20))
    location_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    location_type: Mapped[str | None] = mapped_column(String(50), index=True)
    max_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    inventory_positions: Mapped[list["InventoryPosition"]] = relationship(
        back_populates="location"
    )


class SKU(Base):
    """Product/SKU master."""

    __tablename__ = "skus"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    sku_code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    sku_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category_l1: Mapped[str | None] = mapped_column(String(100), index=True)
    category_l2: Mapped[str | None] = mapped_column(String(100))
    unit_of_measure: Mapped[str | None] = mapped_column(String(20))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    is_perishable: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    temperature_zone: Mapped[str | None] = mapped_column(String(50), index=True)
    reorder_point: Mapped[int | None] = mapped_column(Integer)
    min_order_qty: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    inventory_positions: Mapped[list["InventoryPosition"]] = relationship(
        back_populates="sku"
    )


class InventoryPosition(Base):
    """Current inventory state."""

    __tablename__ = "inventory_positions"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    facility_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    location_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.locations.id"),
        nullable=False,
        index=True,
    )
    sku_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.skus.id"),
        nullable=False,
        index=True,
    )
    lot_number: Mapped[str | None] = mapped_column(String(100), index=True)
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quantity_reserved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)
    received_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_counted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_movement_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="inventory_positions")
    sku: Mapped["SKU"] = relationship(back_populates="inventory_positions")


class InventoryMovement(Base):
    """Inventory transaction history."""

    __tablename__ = "inventory_movements"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    facility_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    from_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.locations.id"), index=True
    )
    to_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.locations.id"), index=True
    )
    sku_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.skus.id"),
        nullable=False,
        index=True,
    )
    lot_number: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100), index=True)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    performed_by: Mapped[str | None] = mapped_column(String(100))
    performed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    from_location: Mapped["Location | None"] = relationship(
        foreign_keys=[from_location_id]
    )
    to_location: Mapped["Location | None"] = relationship(foreign_keys=[to_location_id])
    sku: Mapped["SKU"] = relationship()


class Order(Base):
    """Outbound/transfer/return orders."""

    __tablename__ = "orders"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    facility_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    order_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="'PENDING'",
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    customer_id: Mapped[str | None] = mapped_column(String(100), index=True)
    carrier_code: Mapped[str | None] = mapped_column(String(50))
    required_ship_date: Mapped[date | None] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    order_lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderLine(Base):
    """Order line items."""

    __tablename__ = "order_lines"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.skus.id"),
        nullable=False,
        index=True,
    )
    lot_number: Mapped[str | None] = mapped_column(String(100))
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_picked: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="'PENDING'",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="order_lines")
    sku: Mapped["SKU"] = relationship()


class Wave(Base):
    """Pick wave groupings."""

    __tablename__ = "waves"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    facility_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    wave_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="DRAFT",
        server_default="'DRAFT'",
        index=True,
    )
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_lines: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_units: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_by: Mapped[str | None] = mapped_column(String(100))
    released_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(back_populates="wave")


class Task(Base):
    """Warehouse tasks (pick, putaway, etc.)."""

    __tablename__ = "tasks"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    facility_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    wave_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.waves.id"), index=True
    )
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="'PENDING'",
        index=True,
    )
    from_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.locations.id"), index=True
    )
    to_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.locations.id"), index=True
    )
    sku_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.skus.id"),
        nullable=False,
        index=True,
    )
    lot_number: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(100), index=True)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    wave: Mapped["Wave | None"] = relationship(back_populates="tasks")
    from_location: Mapped["Location | None"] = relationship(
        foreign_keys=[from_location_id]
    )
    to_location: Mapped["Location | None"] = relationship(foreign_keys=[to_location_id])
    sku: Mapped["SKU"] = relationship()
