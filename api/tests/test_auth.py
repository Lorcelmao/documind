from conftest import register_and_login
from sqlalchemy import text

from app.auth.security import hash_refresh_token


async def test_register_returns_user(client):
    res = await client.post(
        "/auth/register", json={"email": "new@example.com", "password": "password123"}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@example.com"
    assert "password" not in body and "password_hash" not in body


async def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    res = await client.post("/auth/register", json=payload)
    assert res.status_code == 409


async def test_register_rejects_short_password(client):
    res = await client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert res.status_code == 422


async def test_login_sets_refresh_cookie_and_returns_access_token(client):
    headers = await register_and_login(client)
    assert headers["Authorization"].startswith("Bearer ")
    assert client.cookies.get("refresh_token") is not None


async def test_login_wrong_password_unauthorized(client):
    await register_and_login(client)
    res = await client.post(
        "/auth/login", json={"email": "user@example.com", "password": "wrong-password"}
    )
    assert res.status_code == 401


async def test_me_returns_current_user(client):
    headers = await register_and_login(client)
    res = await client.get("/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "user@example.com"


async def test_me_without_token_unauthorized(client):
    res = await client.get("/auth/me")
    assert res.status_code == 401


async def test_me_with_garbage_token_unauthorized(client):
    res = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


async def test_refresh_rotates_token(client):
    await register_and_login(client)
    old_token = client.cookies.get("refresh_token")

    res = await client.post("/auth/refresh")
    assert res.status_code == 200
    assert res.json()["access_token"]
    assert client.cookies.get("refresh_token") != old_token


async def test_refresh_reuse_within_grace_keeps_current_session(client):
    await register_and_login(client)
    old_token = client.cookies.get("refresh_token")

    res = await client.post("/auth/refresh")
    assert res.status_code == 200
    current_token = client.cookies.get("refresh_token")

    # an immediate replay looks like a benign client race: rejected, no nuke
    client.cookies.set("refresh_token", old_token)
    res = await client.post("/auth/refresh")
    assert res.status_code == 401

    client.cookies.set("refresh_token", current_token)
    res = await client.post("/auth/refresh")
    assert res.status_code == 200


async def test_refresh_reuse_after_grace_revokes_all_sessions(client, db_engine):
    await register_and_login(client)
    old_token = client.cookies.get("refresh_token")

    res = await client.post("/auth/refresh")
    assert res.status_code == 200
    current_token = client.cookies.get("refresh_token")

    # age the revocation past the grace window, then the replay counts as theft
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE refresh_tokens"
                " SET revoked_at = revoked_at - interval '60 seconds'"
                " WHERE token_hash = :token_hash"
            ),
            {"token_hash": hash_refresh_token(old_token)},
        )

    client.cookies.set("refresh_token", old_token)
    res = await client.post("/auth/refresh")
    assert res.status_code == 401

    client.cookies.set("refresh_token", current_token)
    res = await client.post("/auth/refresh")
    assert res.status_code == 401


async def test_logout_revokes_refresh_token(client):
    await register_and_login(client)
    token = client.cookies.get("refresh_token")

    res = await client.post("/auth/logout")
    assert res.status_code == 204

    client.cookies.set("refresh_token", token)
    res = await client.post("/auth/refresh")
    assert res.status_code == 401
