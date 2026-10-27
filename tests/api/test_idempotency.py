"""API tests for request idempotency and conflict detection."""

from httpx import AsyncClient


async def test_idempotent_request_replay(client: AsyncClient) -> None:
    """Repeated request with identical payload and Idempotency-Key must replay cached response."""
    headers = {"Idempotency-Key": "test-key-alpha-1"}
    payload = {
        "email": "idempotent_user@example.com",
        "password": "Password123!",
        "full_name": "Idempotent User",
    }

    # 1. Initial request
    resp1 = await client.post("/api/v1/auth/register", headers=headers, json=payload)
    assert resp1.status_code == 201
    data1 = resp1.json()

    # 2. Retried request with identical key and payload
    resp2 = await client.post("/api/v1/auth/register", headers=headers, json=payload)
    assert resp2.status_code == 201
    assert resp2.headers.get("X-Cache-Lookup") == "HIT-IDEMPOTENT"
    data2 = resp2.json()
    assert data1["user"]["id"] == data2["user"]["id"]


async def test_idempotent_request_payload_conflict(client: AsyncClient) -> None:
    """Reusing same Idempotency-Key with different payload must return 409 IDEMPOTENCY_CONFLICT."""
    headers = {"Idempotency-Key": "test-key-conflict-2"}
    payload1 = {
        "email": "original@example.com",
        "password": "Password123!",
        "full_name": "Original",
    }
    payload2 = {
        "email": "altered@example.com",
        "password": "Password123!",
        "full_name": "Altered Payload",
    }

    # Initial request
    resp1 = await client.post("/api/v1/auth/register", headers=headers, json=payload1)
    assert resp1.status_code == 201

    # Conflict request with different payload
    resp2 = await client.post("/api/v1/auth/register", headers=headers, json=payload2)
    assert resp2.status_code == 409
    error = resp2.json()["error"]
    assert error["code"] == "IDEMPOTENCY_CONFLICT"
    assert "different request payload" in error["message"]
