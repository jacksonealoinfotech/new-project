"""API tests for rate limiting and abuse prevention."""

from httpx import AsyncClient


async def test_rate_limiting_enforced_on_login(client: AsyncClient) -> None:
    """Exceeding endpoint rate limit must return 429 RATE_LIMIT_EXCEEDED with Retry-After."""
    payload = {"email": "ratelimit@example.com", "password": "Password123!"}

    # The login endpoint limit is 10 requests per 60 seconds
    responses = []
    for _ in range(12):
        resp = await client.post("/api/v1/auth/login", json=payload)
        responses.append(resp)

    # The final requests should be rate-limited (status 429)
    rate_limited_responses = [r for r in responses if r.status_code == 429]
    assert len(rate_limited_responses) >= 1

    last_resp = rate_limited_responses[0]
    assert "Retry-After" in last_resp.headers
    error = last_resp.json()["error"]
    assert error["code"] == "RATE_LIMIT_EXCEEDED"
