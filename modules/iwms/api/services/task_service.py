"""Task management service."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Task
from ..schemas.tasks import TaskAssign, TaskComplete, TaskCreate, TaskStatus

logger = structlog.get_logger()


class TaskService:
    """Service for task operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_task(self, data: TaskCreate) -> Task:
        """Create a new task."""
        task = Task(**data.model_dump())
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        logger.info(
            "task_created",
            task_id=str(task.id),
            task_type=task.task_type,
            facility_id=task.facility_id,
        )
        return task

    async def get_task(
        self,
        task_id: UUID,
        include_relations: bool = False,
    ) -> Task | None:
        """Get a task by ID."""
        query = select(Task).where(Task.id == task_id)
        if include_relations:
            query = query.options(
                selectinload(Task.from_location),
                selectinload(Task.to_location),
                selectinload(Task.sku),
                selectinload(Task.wave),
            )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        facility_id: str,
        wave_id: UUID | None = None,
        status: TaskStatus | None = None,
        task_type: str | None = None,
        assigned_to: str | None = None,
        include_relations: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Task], int]:
        """List tasks with filtering."""
        query = select(Task).where(Task.facility_id == facility_id)

        if wave_id:
            query = query.where(Task.wave_id == wave_id)
        if status:
            query = query.where(Task.status == status.value)
        if task_type:
            query = query.where(Task.task_type == task_type)
        if assigned_to:
            query = query.where(Task.assigned_to == assigned_to)
        if include_relations:
            query = query.options(
                selectinload(Task.from_location),
                selectinload(Task.to_location),
                selectinload(Task.sku),
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results - order by priority (lower = higher priority) then created_at
        query = (
            query.offset(offset).limit(limit).order_by(Task.priority, Task.created_at)
        )
        result = await self.db.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def assign_task(self, task_id: UUID, data: TaskAssign) -> Task | None:
        """Assign a task to a worker."""
        task = await self.get_task(task_id)
        if not task:
            return None

        if task.status not in [TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value]:
            raise ValueError(f"Cannot assign task in status {task.status}")

        task.assigned_to = data.assigned_to
        task.status = TaskStatus.ASSIGNED.value

        await self.db.flush()
        await self.db.refresh(task)

        logger.info(
            "task_assigned",
            task_id=str(task_id),
            assigned_to=data.assigned_to,
        )
        return task

    async def start_task(self, task_id: UUID) -> Task | None:
        """Start a task (set to IN_PROGRESS)."""
        task = await self.get_task(task_id)
        if not task:
            return None

        if task.status not in [TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value]:
            raise ValueError(f"Cannot start task in status {task.status}")

        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(task)

        logger.info("task_started", task_id=str(task_id))
        return task

    async def complete_task(self, task_id: UUID, data: TaskComplete) -> Task | None:
        """Complete a task."""
        task = await self.get_task(task_id)
        if not task:
            return None

        if task.status == TaskStatus.COMPLETE.value:
            raise ValueError("Task is already completed")
        if task.status == TaskStatus.CANCELLED.value:
            raise ValueError("Cannot complete a cancelled task")

        task.status = TaskStatus.COMPLETE.value
        task.completed_at = datetime.utcnow()

        # Start task if not already started
        if not task.started_at:
            task.started_at = task.completed_at

        await self.db.flush()
        await self.db.refresh(task)

        logger.info(
            "task_completed",
            task_id=str(task_id),
            quantity_completed=data.quantity_completed,
        )
        return task

    async def cancel_task(self, task_id: UUID) -> Task | None:
        """Cancel a task."""
        task = await self.get_task(task_id)
        if not task:
            return None

        if task.status == TaskStatus.COMPLETE.value:
            raise ValueError("Cannot cancel a completed task")

        task.status = TaskStatus.CANCELLED.value

        await self.db.flush()
        await self.db.refresh(task)

        logger.info("task_cancelled", task_id=str(task_id))
        return task

    async def get_task_counts_by_status(
        self,
        facility_id: str,
        wave_id: UUID | None = None,
    ) -> dict[str, int]:
        """Get task counts grouped by status."""
        query = (
            select(Task.status, func.count(Task.id))
            .where(Task.facility_id == facility_id)
            .group_by(Task.status)
        )
        if wave_id:
            query = query.where(Task.wave_id == wave_id)

        result = await self.db.execute(query)
        return {row[0]: row[1] for row in result.all()}
