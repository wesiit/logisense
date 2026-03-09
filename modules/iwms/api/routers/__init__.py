"""iWMS API Routers."""

from .health import router as health_router
from .inventory import router as inventory_router
from .movements import router as movements_router
from .orders import router as orders_router
from .tasks import router as tasks_router
from .waves import router as waves_router

__all__ = [
    "health_router",
    "inventory_router",
    "movements_router",
    "orders_router",
    "tasks_router",
    "waves_router",
]
