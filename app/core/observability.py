"""Observability, OpenTelemetry, and metrics configuration."""

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("observability")


def setup_telemetry() -> None:
    """Initialize OpenTelemetry instrumentation if configured."""
    settings = get_settings()
    try:
        from opentelemetry import trace

        # Minimal setup hook that projects can extend with TracerProvider, OTLPSpanExporter, etc.
        _ = trace.get_tracer(settings.APP_NAME)
        logger.info("telemetry_initialized", tracer_name=settings.APP_NAME)
    except ImportError:
        logger.debug("opentelemetry_not_installed")


class SimpleMetrics:
    """In-memory lightweight metrics tracker for Prometheus-compatible scrape points."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def get_metrics(self) -> dict[str, Any]:
        return dict(self._counters)


metrics = SimpleMetrics()
