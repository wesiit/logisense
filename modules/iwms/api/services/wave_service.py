"""Wave management service."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import InventoryPosition, Order, OrderLine, Task, Wave
from ..schemas.tasks import TaskStatus, TaskType
from ..schemas.waves import WaveCreate, WaveStatus
from .kafka_producer import KafkaProducer

logger = structlog.get_logger()


class WaveService:
    """Service for wave operations."""

    def __init__(self, db: AsyncSession, kafka: KafkaProducer | None = None) -> None:
        self.db = db
        self.kafka = kafka

    async def create_wave(self, data: WaveCreate) -> Wave:
        """
        Create a wave from a list of order IDs.

        Logic:
        1. Load all pending order lines for those orders
        2. Group tasks by zone (from location_code prefix)
        3. Create one PICK task per order line
        4. Set wave status to DRAFT
        """
        # Generate wave number
        wave_number = await self._generate_wave_number(data.facility_id)

        # Load orders with their lines
        orders_query = (
            select(Order)
            .where(
                Order.id.in_(data.order_ids),
                Order.facility_id == data.facility_id,
                Order.status == "PENDING",
            )
            .options(selectinload(Order.order_lines).selectinload(OrderLine.sku))
        )
        result = await self.db.execute(orders_query)
        orders = list(result.scalars().all())

        if not orders:
            raise ValueError("No pending orders found for the given IDs")

        # Collect all order lines
        all_lines: list[OrderLine] = []
        for order in orders:
            all_lines.extend(
                [line for line in order.order_lines if line.status == "PENDING"]
            )

        if not all_lines:
            raise ValueError("No pending order lines found")

        # Calculate totals
        total_orders = len(orders)
        total_lines = len(all_lines)
        total_units = sum(line.quantity_ordered for line in all_lines)

        # Create wave
        wave = Wave(
            facility_id=data.facility_id,
            wave_number=wave_number,
            status=WaveStatus.DRAFT.value,
            total_orders=total_orders,
            total_lines=total_lines,
            total_units=total_units,
            created_by=data.created_by,
        )
        self.db.add(wave)
        await self.db.flush()

        # Create pick tasks for each order line
        tasks = await self._create_pick_tasks(wave, all_lines, data.facility_id)

        # Update order statuses to WAVED
        for order in orders:
            order.status = "WAVED"
            order.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(wave)

        logger.info(
            "wave_created",
            wave_id=str(wave.id),
            wave_number=wave_number,
            total_orders=total_orders,
            total_lines=total_lines,
            total_units=total_units,
            task_count=len(tasks),
        )

        return wave

    async def _generate_wave_number(self, facility_id: str) -> str:
        """Generate a unique wave number."""
        today = datetime.utcnow().strftime("%Y%m%d")

        # Count existing waves for today
        query = (
            select(func.count())
            .select_from(Wave)
            .where(
                Wave.facility_id == facility_id,
                Wave.wave_number.like(f"W-{today}-%"),
            )
        )
        result = await self.db.execute(query)
        count = (result.scalar() or 0) + 1

        return f"W-{today}-{count:04d}"

    async def _create_pick_tasks(
        self,
        wave: Wave,
        order_lines: list[OrderLine],
        facility_id: str,
    ) -> list[Task]:
        """Create pick tasks for order lines, finding inventory positions."""
        tasks: list[Task] = []

        for line in order_lines:
            # Find inventory position for this SKU
            # Order by expiry_date (FEFO - First Expiry First Out)
            position_query = (
                select(InventoryPosition)
                .where(
                    InventoryPosition.facility_id == facility_id,
                    InventoryPosition.sku_id == line.sku_id,
                    InventoryPosition.quantity > InventoryPosition.quantity_reserved,
                )
                .options(selectinload(InventoryPosition.location))
                .order_by(
                    InventoryPosition.expiry_date.asc().nullslast(),
                    InventoryPosition.received_at.asc(),
                )
                .limit(1)
            )
            result = await self.db.execute(position_query)
            position = result.scalar_one_or_none()

            from_location_id = position.location_id if position else None

            # Create pick task
            task = Task(
                facility_id=facility_id,
                wave_id=wave.id,
                task_type=TaskType.PICK.value,
                status=TaskStatus.PENDING.value,
                sku_id=line.sku_id,
                lot_number=line.lot_number
                or (position.lot_number if position else None),
                quantity=line.quantity_ordered,
                from_location_id=from_location_id,
                priority=5,  # Default priority
            )
            self.db.add(task)
            tasks.append(task)

            # Reserve inventory if position found
            if position:
                position.quantity_reserved += line.quantity_ordered

        await self.db.flush()
        return tasks

    async def get_wave(
        self,
        wave_id: UUID,
        include_tasks: bool = False,
    ) -> Wave | None:
        """Get a wave by ID."""
        query = select(Wave).where(Wave.id == wave_id)
        if include_tasks:
            query = query.options(
                selectinload(Wave.tasks).selectinload(Task.from_location),
                selectinload(Wave.tasks).selectinload(Task.sku),
            )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_waves(
        self,
        facility_id: str,
        status: WaveStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Wave], int]:
        """List waves with filtering."""
        query = select(Wave).where(Wave.facility_id == facility_id)

        if status:
            query = query.where(Wave.status == status.value)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(Wave.created_at.desc())
        result = await self.db.execute(query)
        waves = list(result.scalars().all())

        return waves, total

    async def release_wave(
        self, wave_id: UUID, released_by: str | None = None
    ) -> Wave | None:
        """
        Release a wave for execution.

        Sets status to RELEASED, sets released_at, publishes Kafka event.
        """
        wave = await self.get_wave(wave_id, include_tasks=True)
        if not wave:
            return None

        if wave.status != WaveStatus.DRAFT.value:
            raise ValueError(f"Cannot release wave in status {wave.status}")

        now = datetime.utcnow()
        wave.status = WaveStatus.RELEASED.value
        wave.released_at = now

        # Get task count
        task_count = len(wave.tasks) if wave.tasks else 0

        await self.db.flush()
        await self.db.refresh(wave)

        logger.info(
            "wave_released",
            wave_id=str(wave_id),
            wave_number=wave.wave_number,
            task_count=task_count,
        )

        # Publish Kafka event
        if self.kafka:
            await self.kafka.publish_wave_released(
                wave_id=wave.id,
                wave_number=wave.wave_number,
                facility_id=wave.facility_id,
                total_orders=wave.total_orders,
                total_lines=wave.total_lines,
                total_units=wave.total_units,
                task_count=task_count,
                released_at=now,
                released_by=released_by,
            )

        return wave

    async def complete_wave(self, wave_id: UUID) -> Wave | None:
        """Mark a wave as complete."""
        wave = await self.get_wave(wave_id)
        if not wave:
            return None

        if wave.status not in [WaveStatus.RELEASED.value, WaveStatus.IN_PROGRESS.value]:
            raise ValueError(f"Cannot complete wave in status {wave.status}")

        wave.status = WaveStatus.COMPLETE.value
        wave.completed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(wave)

        logger.info(
            "wave_completed", wave_id=str(wave_id), wave_number=wave.wave_number
        )
        return wave

    async def get_wave_progress(self, wave_id: UUID) -> dict:
        """Get wave progress statistics."""
        wave = await self.get_wave(wave_id)
        if not wave:
            return {}

        # Get task counts by status
        query = (
            select(Task.status, func.count(Task.id))
            .where(Task.wave_id == wave_id)
            .group_by(Task.status)
        )
        result = await self.db.execute(query)
        status_counts = {row[0]: row[1] for row in result.all()}

        total_tasks = sum(status_counts.values())
        completed_tasks = status_counts.get(TaskStatus.COMPLETE.value, 0)

        return {
            "wave_id": str(wave_id),
            "wave_number": wave.wave_number,
            "status": wave.status,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": status_counts.get(TaskStatus.PENDING.value, 0),
            "in_progress_tasks": status_counts.get(TaskStatus.IN_PROGRESS.value, 0),
            "completion_percentage": (completed_tasks / total_tasks * 100)
            if total_tasks > 0
            else 0,
        }
