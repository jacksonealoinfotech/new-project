"""Security tests for HTTP defense-in-depth headers and request ID propagation."""

from httpx import AsyncClient


async def test_security_headers_present_on_all_responses(client: AsyncClient) -> None:
    """All HTTP responses must enforce nosniff, DENY, and Referrer-Policy."""
    resp = await client.get("/api/v1/health/liveness")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


async def test_request_id_generated_and_propagated(client: AsyncClient) -> None:
    """Incoming request ID must be preserved or generated and attached to response headers."""
    # 1. Without header -> generated
    resp1 = await client.get("/api/v1/health/liveness")
    req_id1 = resp1.headers.get("X-Request-ID")
    assert req_id1 is not None
    assert req_id1.startswith("req_")

    # 2. With client-provided header -> preserved
    custom_id = "custom-client-trace-id-999"
    resp2 = await client.get("/api/v1/health/liveness", headers={"X-Request-ID": custom_id})
    assert resp2.headers.get("X-Request-ID") == custom_id
