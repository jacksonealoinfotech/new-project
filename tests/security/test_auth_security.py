"""Security tests for authentication breach detection, token family revocation, and privilege escalation."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.security import hash_password
from app.modules.users.models import User


async def test_refresh_token_reuse_triggers_family_revocation(
    client: AsyncClient, test_user: User
) -> None:
    """Security breach detection: presenting an already rotated/revoked refresh token

    must immediately revoke all active tokens in that session family.
    """
    # 1. Login to receive initial refresh token T1
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "Password123!"},
    )
    t1 = login_resp.json()["refresh_token"]

    # 2. Legitimate client rotates T1 -> receives T2 (T1 is now revoked)
    refresh1_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": t1})
    assert refresh1_resp.status_code == 200
    t2 = refresh1_resp.json()["refresh_token"]

    # 3. Adversary replays compromised/stolen T1
    adversary_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": t1})
    assert adversary_resp.status_code == 401
    assert "compromise detected" in adversary_resp.json()["error"]["message"].lower()

    # 4. Legitimate T2 must now ALSO be invalidated because the entire family was terminated
    subsequent_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": t2})
    assert subsequent_resp.status_code == 401


async def test_registration_prevents_privilege_escalation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Attempting to supply role='admin' in public registration must be ignored (mass assignment defense)."""
    payload = {
        "email": "hacker@example.com",
        "password": "Password123!",
        "full_name": "Privilege Escalation Attempt",
        "role": "admin",  # Attacker attempts to assign admin role
        "is_active": True,
        "is_verified": True,
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201

    # Check database model directly: user MUST have regular USER role
    stmt = select(User).where(User.email == "hacker@example.com")
    res = await db_session.execute(stmt)
    created_user = res.scalars().first()
    assert created_user is not None
    assert created_user.role == UserRole.USER


async def test_cross_user_resource_access_forbidden(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    user_auth_headers: dict[str, str],
) -> None:
    """A regular user must NOT be permitted to access another user's account details."""
    # Create another victim user
    victim = User(
        email="victim@example.com",
        hashed_password=hash_password("Victim123!"),
        full_name="Victim Account",
        role=UserRole.USER,
    )
    db_session.add(victim)
    await db_session.commit()
    await db_session.refresh(victim)

    # test_user attempts to access victim's profile
    resp = await client.get(f"/api/v1/users/{victim.id}", headers=user_auth_headers)
    assert resp.status_code == 403
    error = resp.json()["error"]
    assert error["code"] == "PERMISSION_DENIED"


async def test_forged_signature_token_rejected(client: AsyncClient) -> None:
    """Tokens signed with a forged or mismatched secret key must be rejected."""
    # Token signed with fake key
    import jwt

    fake_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "roles": ["admin"]},
        "fake-secret-key-12345678901234567890",
        algorithm="HS256",
    )
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {fake_token}"})
    assert resp.status_code == 401
