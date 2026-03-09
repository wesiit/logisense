"""Task management endpoints."""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import TokenPayload, validate_token
from ..db import DbSession
from ..schemas.common import PaginatedResponse
from ..schemas.tasks import TaskAssign, TaskComplete, TaskResponse, TaskStatus, TaskType
from ..services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_task_service(db: DbSession) -> TaskService:
    """Dependency to get task service."""
    return TaskService(db)


TaskSvc = Annotated[TaskService, Depends(get_task_service)]
CurrentUser = Annotated[TokenPayload, Depends(validate_token)]


@router.get("", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    service: TaskSvc,
    _user: CurrentUser,
    facility_id: str = Query(..., description="Facility ID to filter by"),
    wave_id: UUID | None = Query(None, description="Filter by wave"),
    status_filter: TaskStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    task_type: TaskType | None = Query(None, description="Filter by task type"),
    assigned_to: str | None = Query(None, description="Filter by assigned worker"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[TaskResponse]:
    """List tasks with filtering and pagination."""
    offset = (page - 1) * page_size
    tasks, total = await service.list_tasks(
        facility_id=facility_id,
        wave_id=wave_id,
        status=status_filter,
        task_type=task_type.value if task_type else None,
        assigned_to=assigned_to,
        include_relations=True,
        offset=offset,
        limit=page_size,
    )

    return PaginatedResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    service: TaskSvc,
    _user: CurrentUser,
) -> TaskResponse:
    """Get a specific task by ID."""
    task = await service.get_task(task_id, include_relations=True)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: UUID,
    data: TaskAssign,
    service: TaskSvc,
    _user: CurrentUser,
) -> TaskResponse:
    """Assign a task to a worker."""
    try:
        task = await service.assign_task(task_id, data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: UUID,
    service: TaskSvc,
    _user: CurrentUser,
) -> TaskResponse:
    """Start a task (set to IN_PROGRESS)."""
    try:
        task = await service.start_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    data: TaskComplete,
    service: TaskSvc,
    _user: CurrentUser,
) -> TaskResponse:
    """Complete a task."""
    try:
        task = await service.complete_task(task_id, data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    service: TaskSvc,
    _user: CurrentUser,
) -> TaskResponse:
    """Cancel a task."""
    try:
        task = await service.cancel_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/stats/by-status")
async def get_task_stats(
    service: TaskSvc,
    _user: CurrentUser,
    facility_id: str = Query(..., description="Facility ID"),
    wave_id: UUID | None = Query(None, description="Filter by wave"),
) -> dict[str, int]:
    """Get task counts grouped by status."""
    return await service.get_task_counts_by_status(facility_id, wave_id)
