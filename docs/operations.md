# Operations & Observability

## 1. Structured Logging & Correlated Traces

The platform utilizes `structlog` for high-performance structured logging.
- **Local Development**: Outputs human-friendly, colored console logs.
- **Production (`LOG_FORMAT=json`)**: Outputs machine-parseable JSON lines with standardized fields:

```json
{
  "event": "http_request_finished",
  "level": "info",
  "timestamp": "2026-10-10T06:00:00.123456Z",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status_code": 200,
  "duration_ms": 14.85,
  "client_ip": "198.51.100.4",
  "request_id": "req_a1b2c3d4e5f6"
}
```

Every request is assigned a unique `request_id` (propagated via `X-Request-ID`), allowing developers to trace an entire request journey across log aggregators.

## 2. Metrics & Telemetry

- **OpenTelemetry Hook**: The platform initializes OpenTelemetry in `app.core.observability.setup_telemetry()`. To export to an OpenTelemetry Collector or Grafana Tempo, configure an `OTLPSpanExporter` in that module.
- **Metrics Scraping**: Prometheus-compatible metrics can be scraped or exported for request counts, response latency histograms, database connection pool saturation, and error rates.

## 3. Graceful Shutdown & Resource Management

FastAPI's lifespan context manager handles termination signals (`SIGTERM`, `SIGINT`):
1. In-flight requests are allowed to finish within Kubernetes termination grace periods (default 30 seconds).
2. The shared HTTP client connections are drained and closed.
3. Redis client connection pools are released.
4. The SQLAlchemy async engine is cleanly disposed (`await engine.dispose()`), terminating remaining database connections.
