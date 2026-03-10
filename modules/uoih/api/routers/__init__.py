"""UOIH API routers."""

from .alerts import router as alerts_router
from .health import router as health_router
from .kpis import router as kpis_router

__all__ = ["alerts_router", "health_router", "kpis_router"]
