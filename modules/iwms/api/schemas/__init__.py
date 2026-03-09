"""Pydantic schemas for iWMS API."""

from .inventory import (
    InventoryMovementCreate,
    InventoryMovementResponse,
    InventoryPositionCreate,
    InventoryPositionResponse,
    InventoryPositionUpdate,
    LocationCreate,
    LocationResponse,
    SKUCreate,
    SKUResponse,
)
from .orders import (
    OrderCreate,
    OrderLineCreate,
    OrderLineResponse,
    OrderResponse,
    OrderUpdate,
)
from .tasks import (
    TaskAssign,
    TaskComplete,
    TaskCreate,
    TaskResponse,
)
from .waves import (
    WaveCreate,
    WaveResponse,
    WaveWithTasks,
)

__all__ = [
    "InventoryMovementCreate",
    "InventoryMovementResponse",
    "InventoryPositionCreate",
    "InventoryPositionResponse",
    "InventoryPositionUpdate",
    # Inventory
    "LocationCreate",
    "LocationResponse",
    # Orders
    "OrderCreate",
    "OrderLineCreate",
    "OrderLineResponse",
    "OrderResponse",
    "OrderUpdate",
    "SKUCreate",
    "SKUResponse",
    "TaskAssign",
    "TaskComplete",
    # Tasks
    "TaskCreate",
    "TaskResponse",
    # Waves
    "WaveCreate",
    "WaveResponse",
    "WaveWithTasks",
]
