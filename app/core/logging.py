"""Structured logging setup (structlog → JSON), with correlation-id support."""

import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog + stdlib logging to emit JSON with ISO timestamps."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Human-friendly console in dev, JSON everywhere else.
    renderer = (
        structlog.dev.ConsoleRenderer()
        if settings.is_dev
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
