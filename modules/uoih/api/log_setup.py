"""Structured logging configuration for UOIH API."""

import logging
import sys

import structlog
from fastapi import Request


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging with structlog."""
    log_level = logging.DEBUG if debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
            if not debug
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_request_id(request: Request) -> str:
    """Extract request ID from headers."""
    return request.headers.get(
        "X-Request-ID", request.headers.get("X-Correlation-ID", "")
    )


def bind_request_context(request: Request) -> dict:
    """Extract context from request for logging."""
    return {
        "request_id": get_request_id(request),
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
    }
