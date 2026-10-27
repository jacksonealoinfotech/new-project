"""API tests for authentication endpoints."""

from httpx import AsyncClient

from app.modules.users.models import User


async def test_register_creates_account_and_tokens(client: AsyncClient) -> None:
    """Registering a new account must return 201 with user profile and token pair."""
    payload = {
        "email": "newuser@example.com",
        "password": "ValidPassword123!",
        "full_name": "New Registered User",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["user"]["email"] == "newuser@example.com"
    assert "hashed_password" not in data["user"]
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]
    assert data["tokens"]["token_type"] == "bearer"


async def test_register_duplicate_email_conflict(client: AsyncClient, test_user: User) -> None:
    """Registering an already registered email must return 409 RESOURCE_CONFLICT."""
    payload = {
        "email": test_user.email,
        "password": "Password123!",
        "full_name": "Duplicate Attempt",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    error = resp.json()["error"]
    assert error["code"] == "RESOURCE_CONFLICT"
    assert "already exists" in error["message"]


async def test_login_valid_credentials(client: AsyncClient, test_user: User) -> None:
    """Valid login credentials must return 200 with JWT and refresh token."""
    payload = {
        "email": test_user.email,
        "password": "Password123!",
    }
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_invalid_password_returns_401(client: AsyncClient, test_user: User) -> None:
    """Invalid password must return 401 AUTHENTICATION_FAILED with generic message."""
    payload = {
        "email": test_user.email,
        "password": "WrongPassword!",
    }
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["code"] == "AUTHENTICATION_FAILED"
    assert error["message"] == "Invalid email or password."


async def test_refresh_token_rotation(client: AsyncClient, test_user: User) -> None:
    """Refreshing tokens must rotate the refresh token and produce a new access token."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "Password123!"},
    )
    tokens = login_resp.json()
    first_refresh = tokens["refresh_token"]

    # Exchange for new tokens
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != first_refresh


async def test_logout_revokes_token(client: AsyncClient, test_user: User) -> None:
    """Logging out must revoke refresh token, preventing subsequent refresh."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "Password123!"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 200

    # Attempt refresh with revoked token should fail
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401


async def test_change_password(
    client: AsyncClient, test_user: User, user_auth_headers: dict[str, str]
) -> None:
    """Password change must verify current password, apply update, and revoke existing sessions."""
    # Obtain a refresh token before password change
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "Password123!"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Change password
    change_resp = await client.post(
        "/api/v1/auth/change-password",
        headers=user_auth_headers,
        json={"current_password": "Password123!", "new_password": "NewSecretPassword999!"},
    )
    assert change_resp.status_code == 200

    # Old password no longer works
    login_old = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "Password123!"},
    )
    assert login_old.status_code == 401

    # Prior session refresh token is also revoked
    revoked_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert revoked_refresh.status_code == 401

    # New password succeeds
    login_new = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "NewSecretPassword999!"},
    )
    assert login_new.status_code == 200
