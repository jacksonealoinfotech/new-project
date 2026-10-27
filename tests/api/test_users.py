"""API tests for User domain endpoints, RBAC, and pagination."""

from httpx import AsyncClient

from app.modules.users.models import User


async def test_get_current_user_profile(
    client: AsyncClient, test_user: User, user_auth_headers: dict[str, str]
) -> None:
    """Authenticated user must successfully access their /users/me profile."""
    resp = await client.get("/api/v1/users/me", headers=user_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert "hashed_password" not in data


async def test_update_current_user_profile(
    client: AsyncClient, test_user: User, user_auth_headers: dict[str, str]
) -> None:
    """User can update their own profile name."""
    resp = await client.patch(
        "/api/v1/users/me",
        headers=user_auth_headers,
        json={"full_name": "Updated User Name"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Updated User Name"


async def test_unauthenticated_request_rejected(client: AsyncClient) -> None:
    """Unauthenticated requests to protected endpoints must return 401."""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["code"] == "AUTHENTICATION_FAILED"


async def test_non_admin_listing_forbidden(
    client: AsyncClient, user_auth_headers: dict[str, str]
) -> None:
    """Regular users must be forbidden from listing all users."""
    resp = await client.get("/api/v1/users/", headers=user_auth_headers)
    assert resp.status_code == 403
    error = resp.json()["error"]
    assert error["code"] == "PERMISSION_DENIED"


async def test_admin_listing_paginated(
    client: AsyncClient, test_admin: User, admin_auth_headers: dict[str, str]
) -> None:
    """Administrators can retrieve paginated user lists with metadata."""
    resp = await client.get("/api/v1/users/?page=1&page_size=10", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "meta" in data
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 10
    assert data["meta"]["total_items"] >= 1
    assert isinstance(data["items"], list)


async def test_admin_create_and_delete_user(
    client: AsyncClient, admin_auth_headers: dict[str, str]
) -> None:
    """Administrators can create users with designated roles and soft-delete them."""
    create_payload = {
        "email": "manager@example.com",
        "password": "ManagerPassword123!",
        "full_name": "Manager Account",
        "role": "admin",
        "is_active": True,
        "is_verified": True,
    }
    create_resp = await client.post(
        "/api/v1/users/", headers=admin_auth_headers, json=create_payload
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]

    # Deactivate / Soft delete
    del_resp = await client.delete(f"/api/v1/users/{created_id}", headers=admin_auth_headers)
    assert del_resp.status_code == 200
    assert "deactivated" in del_resp.json()["message"]
