"""Logging configuration with structlog."""

import contextvars
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.settings import settings

# Context variable for correlation ID
correlation_id_var = contextvars.ContextVar[str]("correlation_id", default="-")


def setup_logging() -> None:
    """Configure structured logging with correlation ID support."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Custom processor to add correlation_id and service name
            lambda logger, method_name, event_dict: {
                **event_dict,
                "correlation_id": correlation_id_var.get(),
                "service": "protectogram",
            },
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add correlation ID to request and response headers."""
        # Get correlation ID from headers or generate new one
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Set in context variable
        correlation_id_var.set(correlation_id)

        # Add to request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Request-ID"] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request start and completion."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log request start and completion with timing."""
        start_time = time.time()

        # Log request start
        logger = get_logger("request")
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id_var.get(),
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log request completion
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id_var.get(),
        )

        return response


def install_middlewares(app: FastAPI) -> None:
    """Install middlewares in the correct order."""
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_with_context(
    logger: structlog.stdlib.BoundLogger, **context: Any
) -> structlog.stdlib.BoundLogger:
    """Add context to logger."""
    return logger.bind(**context)
