"""API tests for health probes."""

from httpx import AsyncClient


async def test_liveness_probe_returns_200(client: AsyncClient) -> None:
    """Liveness probe must immediately return 200 OK with status ok."""
    resp = await client.get("/api/v1/health/liveness")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readiness_probe_returns_ready(client: AsyncClient) -> None:
    """Readiness probe must return 200 OK and reports database health."""
    resp = await client.get("/api/v1/health/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "healthy"
