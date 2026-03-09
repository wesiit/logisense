"""Inventory business logic service."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import SKU, InventoryMovement, InventoryPosition, Location
from ..schemas.inventory import (
    InventoryMovementCreate,
    InventoryPositionCreate,
    InventoryPositionUpdate,
    LocationCreate,
    MovementType,
    SKUCreate,
)
from .kafka_producer import KafkaProducer

logger = structlog.get_logger()


class InventoryService:
    """Service for inventory operations."""

    def __init__(self, db: AsyncSession, kafka: KafkaProducer | None = None) -> None:
        self.db = db
        self.kafka = kafka

    # =========================================================================
    # Location Operations
    # =========================================================================

    async def create_location(self, data: LocationCreate) -> Location:
        """Create a new location."""
        location = Location(**data.model_dump())
        self.db.add(location)
        await self.db.flush()
        await self.db.refresh(location)
        logger.info(
            "location_created",
            location_id=str(location.id),
            location_code=location.location_code,
        )
        return location

    async def get_location(self, location_id: UUID) -> Location | None:
        """Get a location by ID."""
        result = await self.db.execute(
            select(Location).where(Location.id == location_id)
        )
        return result.scalar_one_or_none()

    async def get_location_by_code(self, location_code: str) -> Location | None:
        """Get a location by code."""
        result = await self.db.execute(
            select(Location).where(Location.location_code == location_code)
        )
        return result.scalar_one_or_none()

    async def list_locations(
        self,
        facility_id: str,
        zone_id: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Location], int]:
        """List locations with filtering and pagination."""
        query = select(Location).where(Location.facility_id == facility_id)

        if zone_id:
            query = query.where(Location.zone_id == zone_id)
        if is_active is not None:
            query = query.where(Location.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(Location.location_code)
        result = await self.db.execute(query)
        locations = list(result.scalars().all())

        return locations, total

    # =========================================================================
    # SKU Operations
    # =========================================================================

    async def create_sku(self, data: SKUCreate) -> SKU:
        """Create a new SKU."""
        sku = SKU(**data.model_dump())
        self.db.add(sku)
        await self.db.flush()
        await self.db.refresh(sku)
        logger.info("sku_created", sku_id=str(sku.id), sku_code=sku.sku_code)
        return sku

    async def get_sku(self, sku_id: UUID) -> SKU | None:
        """Get a SKU by ID."""
        result = await self.db.execute(select(SKU).where(SKU.id == sku_id))
        return result.scalar_one_or_none()

    async def get_sku_by_code(self, sku_code: str) -> SKU | None:
        """Get a SKU by code."""
        result = await self.db.execute(select(SKU).where(SKU.sku_code == sku_code))
        return result.scalar_one_or_none()

    async def list_skus(
        self,
        category_l1: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[SKU], int]:
        """List SKUs with filtering and pagination."""
        query = select(SKU)

        if category_l1:
            query = query.where(SKU.category_l1 == category_l1)
        if is_active is not None:
            query = query.where(SKU.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(SKU.sku_code)
        result = await self.db.execute(query)
        skus = list(result.scalars().all())

        return skus, total

    # =========================================================================
    # Inventory Position Operations
    # =========================================================================

    async def create_inventory_position(
        self, data: InventoryPositionCreate
    ) -> InventoryPosition:
        """Create a new inventory position."""
        position = InventoryPosition(**data.model_dump())
        position.received_at = datetime.utcnow()
        self.db.add(position)
        await self.db.flush()
        await self.db.refresh(position)
        logger.info(
            "inventory_position_created",
            position_id=str(position.id),
            facility_id=position.facility_id,
        )
        return position

    async def get_inventory_position(
        self,
        position_id: UUID,
        include_relations: bool = False,
    ) -> InventoryPosition | None:
        """Get an inventory position by ID."""
        query = select(InventoryPosition).where(InventoryPosition.id == position_id)
        if include_relations:
            query = query.options(
                selectinload(InventoryPosition.location),
                selectinload(InventoryPosition.sku),
            )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_inventory_position(
        self,
        position_id: UUID,
        data: InventoryPositionUpdate,
    ) -> InventoryPosition | None:
        """Update an inventory position."""
        position = await self.get_inventory_position(position_id)
        if not position:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(position, key, value)

        await self.db.flush()
        await self.db.refresh(position)
        logger.info("inventory_position_updated", position_id=str(position_id))
        return position

    async def list_inventory_positions(
        self,
        facility_id: str,
        location_id: UUID | None = None,
        sku_id: UUID | None = None,
        include_relations: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[InventoryPosition], int]:
        """List inventory positions with filtering."""
        query = select(InventoryPosition).where(
            InventoryPosition.facility_id == facility_id
        )

        if location_id:
            query = query.where(InventoryPosition.location_id == location_id)
        if sku_id:
            query = query.where(InventoryPosition.sku_id == sku_id)
        if include_relations:
            query = query.options(
                selectinload(InventoryPosition.location),
                selectinload(InventoryPosition.sku),
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        query = (
            query.offset(offset)
            .limit(limit)
            .order_by(InventoryPosition.created_at.desc())
        )
        result = await self.db.execute(query)
        positions = list(result.scalars().all())

        return positions, total

    # =========================================================================
    # Inventory Movement Operations
    # =========================================================================

    async def create_movement(
        self,
        data: InventoryMovementCreate,
        update_positions: bool = True,
    ) -> InventoryMovement:
        """Create an inventory movement and update positions."""
        # Create movement record
        movement = InventoryMovement(**data.model_dump())
        self.db.add(movement)

        if update_positions:
            await self._apply_movement(data)

        await self.db.flush()
        await self.db.refresh(movement)

        logger.info(
            "inventory_movement_created",
            movement_id=str(movement.id),
            movement_type=data.movement_type.value,
            quantity=data.quantity,
        )

        # Publish Kafka event
        if self.kafka:
            await self.kafka.publish_inventory_movement(
                movement_id=movement.id,
                facility_id=movement.facility_id,
                movement_type=movement.movement_type,
                sku_id=movement.sku_id,
                quantity=movement.quantity,
                from_location_id=movement.from_location_id,
                to_location_id=movement.to_location_id,
                lot_number=movement.lot_number,
                performed_by=movement.performed_by,
                performed_at=movement.performed_at,
            )

        return movement

    async def _apply_movement(self, data: InventoryMovementCreate) -> None:
        """Apply movement to inventory positions."""
        now = datetime.utcnow()

        # Handle source position (decrease quantity)
        if data.from_location_id and data.movement_type in [
            MovementType.PICK,
            MovementType.TRANSFER,
        ]:
            source_position = await self._get_or_create_position(
                facility_id=data.facility_id,
                location_id=data.from_location_id,
                sku_id=data.sku_id,
                lot_number=data.lot_number,
            )
            source_position.quantity -= data.quantity
            source_position.last_movement_at = now

        # Handle destination position (increase quantity)
        if data.to_location_id and data.movement_type in [
            MovementType.RECEIVE,
            MovementType.PUTAWAY,
            MovementType.TRANSFER,
        ]:
            dest_position = await self._get_or_create_position(
                facility_id=data.facility_id,
                location_id=data.to_location_id,
                sku_id=data.sku_id,
                lot_number=data.lot_number,
            )
            dest_position.quantity += data.quantity
            dest_position.last_movement_at = now
            if data.movement_type == MovementType.RECEIVE:
                dest_position.received_at = now

        # Handle adjustments
        if data.movement_type == MovementType.ADJUST and data.to_location_id:
            position = await self._get_or_create_position(
                facility_id=data.facility_id,
                location_id=data.to_location_id,
                sku_id=data.sku_id,
                lot_number=data.lot_number,
            )
            position.quantity = data.quantity  # Adjustment sets absolute quantity
            position.last_movement_at = now

        # Handle cycle counts
        if data.movement_type == MovementType.CYCLE_COUNT and data.to_location_id:
            position = await self._get_or_create_position(
                facility_id=data.facility_id,
                location_id=data.to_location_id,
                sku_id=data.sku_id,
                lot_number=data.lot_number,
            )
            position.quantity = data.quantity
            position.last_counted_at = now
            position.last_movement_at = now

    async def _get_or_create_position(
        self,
        facility_id: str,
        location_id: UUID,
        sku_id: UUID,
        lot_number: str | None,
    ) -> InventoryPosition:
        """Get existing position or create new one."""
        query = select(InventoryPosition).where(
            InventoryPosition.facility_id == facility_id,
            InventoryPosition.location_id == location_id,
            InventoryPosition.sku_id == sku_id,
        )
        if lot_number:
            query = query.where(InventoryPosition.lot_number == lot_number)
        else:
            query = query.where(InventoryPosition.lot_number.is_(None))

        result = await self.db.execute(query)
        position = result.scalar_one_or_none()

        if not position:
            position = InventoryPosition(
                facility_id=facility_id,
                location_id=location_id,
                sku_id=sku_id,
                lot_number=lot_number,
                quantity=0,
            )
            self.db.add(position)
            await self.db.flush()

        return position

    async def list_movements(
        self,
        facility_id: str,
        movement_type: MovementType | None = None,
        sku_id: UUID | None = None,
        include_relations: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[InventoryMovement], int]:
        """List inventory movements with filtering."""
        query = select(InventoryMovement).where(
            InventoryMovement.facility_id == facility_id
        )

        if movement_type:
            query = query.where(InventoryMovement.movement_type == movement_type.value)
        if sku_id:
            query = query.where(InventoryMovement.sku_id == sku_id)
        if include_relations:
            query = query.options(
                selectinload(InventoryMovement.from_location),
                selectinload(InventoryMovement.to_location),
                selectinload(InventoryMovement.sku),
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        query = (
            query.offset(offset)
            .limit(limit)
            .order_by(InventoryMovement.performed_at.desc())
        )
        result = await self.db.execute(query)
        movements = list(result.scalars().all())

        return movements, total
