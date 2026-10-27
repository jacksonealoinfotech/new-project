"""Structured logging configuration using structlog with security redaction."""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "authorization",
    "cookie",
    "api_key",
    "secret_key",
}


def redact_sensitive_data(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Recursively redact sensitive key values to prevent accidental credential leakage in logs."""

    def _redact(val: Any) -> Any:
        if isinstance(val, dict):
            return {
                k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS else _redact(v)
                for k, v in val.items()
            }
        if isinstance(val, list):
            return [_redact(item) for item in val]
        return val

    return {
        k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS else _redact(v)
        for k, v in event_dict.items()
    }


def configure_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """Initialize structured logging pipeline with appropriate formatters and processors."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        redact_sensitive_data,
    ]

    if log_format.lower() == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # Silence overly verbose third-party loggers
    for verbose_logger in ("uvicorn.access", "sqlalchemy.engine", "httpcore", "httpx"):
        logging.getLogger(verbose_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a bound structlog logger instance."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
