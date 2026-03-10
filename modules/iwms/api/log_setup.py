"""Structured logging configuration for iWMS API."""

import logging
import sys
from typing import Any

import structlog
from fastapi import Request


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging with structlog."""
    # Set log level
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            # Use JSON in production, console in debug
            structlog.processors.JSONRenderer()
            if not debug
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiokafka").setLevel(logging.WARNING)


def get_request_id(request: Request) -> str:
    """Extract request ID from headers or generate one."""
    return request.headers.get(
        "X-Request-ID", request.headers.get("X-Correlation-ID", "")
    )


def bind_request_context(request: Request) -> dict[str, Any]:
    """Extract context from request for logging."""
    return {
        "request_id": get_request_id(request),
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
    }
