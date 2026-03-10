"""iWMS API Application."""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .config import get_settings
from .db import close_db, init_db
from .log_setup import bind_request_context, setup_logging
from .routers import (
    health_router,
    inventory_router,
    movements_router,
    orders_router,
    tasks_router,
    waves_router,
)
from .services.kafka_producer import close_kafka_producer, init_kafka_producer

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()

    # Setup logging
    setup_logging(debug=settings.DEBUG)
    logger.info(
        "starting_iwms_api",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
    )

    # Initialize database
    await init_db(settings)
    logger.info("database_initialized")

    # Initialize Kafka producer
    try:
        await init_kafka_producer(settings)
        logger.info("kafka_producer_initialized")
    except Exception as e:
        logger.warning("kafka_producer_init_failed", error=str(e))
        # Continue without Kafka - graceful degradation

    yield

    # Shutdown
    logger.info("shutting_down_iwms_api")
    await close_kafka_producer()
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="LogiSense iWMS API",
        description="Intelligent Warehouse Management System API",
        version=settings.SERVICE_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all requests with context."""
        context = bind_request_context(request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**context)

        logger.info("request_started")
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)

        return response

    # Validation error handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors with field-level details."""
        errors: list[dict[str, Any]] = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": errors,
            },
        )

    # General exception handler
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # Prometheus metrics
    Instrumentator(
        should_group_status_codes=True,
        should_group_untemplated=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")

    # Include routers
    app.include_router(health_router)
    app.include_router(inventory_router, prefix=settings.API_PREFIX)
    app.include_router(movements_router, prefix=settings.API_PREFIX)
    app.include_router(orders_router, prefix=settings.API_PREFIX)
    app.include_router(waves_router, prefix=settings.API_PREFIX)
    app.include_router(tasks_router, prefix=settings.API_PREFIX)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
