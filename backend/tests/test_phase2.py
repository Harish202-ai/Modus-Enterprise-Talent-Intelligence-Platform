from datetime import timedelta

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.api.deps import require_role
from app.config import get_settings
from app.main import app
from app.models.common import utcnow
from tests.conftest import default_tenant, make_user

EMAIL = "asha.rao@example.com"
PASSWORD = "Consult1ng!"
SIGNUP = {"email": EMAIL, "full_name": "Asha Rao", "password": PASSWORD, "consent": True}


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_definition_of_done_register_login_me_and_admin_403(client):
    # Register (consent checkbox ticked) -> signed in straight away.
    r = await client.post("/v1/auth/register", json={**SIGNUP, "email": " Asha.Rao@Example.com ", "full_name": "  Asha   Rao "})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "bearer" and body["user"]["role"] == "candidate" and body["user"]["email"] == EMAIL
    assert body["user"]["full_name"] == "Asha Rao" and body["user"]["consent_accepted_at"]
    assert "password_hash" not in body["user"] and "refresh_token" not in body
    cookie = r.headers["set-cookie"]
    assert "meti_refresh=" in cookie and "HttpOnly" in cookie and "Path=/v1/auth" in cookie

    stored = await database.users().find_one({"email": EMAIL})
    assert stored["password_hash"].startswith("$2") and PASSWORD not in str(stored)

    # Log in with email + password.
    r = await client.post("/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]

    # Protected candidate endpoint.
    r = await client.get("/v1/candidates/me", headers=bearer(token))
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL and r.json()["role"] == "candidate" and r.json()["tenant"]["slug"] == get_settings().default_tenant_slug

    # Admin routes are 403 for candidates.
    for method, path in [("GET", "/v1/admin/content/types"), ("GET", "/v1/admin/content/questions"), ("POST", "/v1/admin/content/questions/Q1/publish")]:
        r = await client.request(method, path, headers=bearer(token))
        assert r.status_code == 403, (path, r.text)
        assert r.json()["detail"] == "Requires role: admin"

    actions = [e["action"] async for e in database.audit_events().find({"entity_id": stored["_id"]}).sort("timestamp", 1)]
    assert actions == ["user.registered", "auth.login"]


@pytest.mark.asyncio
async def test_register_requires_consent_strong_password_and_unique_email(client):
    r = await client.post("/v1/auth/register", json={**SIGNUP, "consent": False})
    assert r.status_code == 422 and "accept the privacy notice" in r.text
    r = await client.post("/v1/auth/register", json={k: v for k, v in SIGNUP.items() if k != "consent"})
    assert r.status_code == 422
    assert (await client.post("/v1/auth/register", json={**SIGNUP, "password": "short1"})).status_code == 422
    r = await client.post("/v1/auth/register", json={**SIGNUP, "password": "lettersonly"})
    assert r.status_code == 422 and "letter and one number" in r.text
    assert await database.users().count_documents({}) == 0

    assert (await client.post("/v1/auth/register", json=SIGNUP)).status_code == 201
    r = await client.post("/v1/auth/register", json={**SIGNUP, "email": EMAIL.upper()})
    assert r.status_code == 409 and "sign in" in r.json()["detail"]


@pytest.mark.asyncio
async def test_login_failures_are_generic_and_rate_limited(client):
    await client.post("/v1/auth/register", json=SIGNUP)
    wrong_pw = await client.post("/v1/auth/login", json={"email": EMAIL, "password": "Wrong123"})
    no_user = await client.post("/v1/auth/login", json={"email": "nobody@example.com", "password": "Wrong123"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json() == {"detail": "Incorrect email or password"}

    s = get_settings()
    for _ in range(s.auth_rate_limit_per_email - 1):  # one attempt already used above
        assert (await client.post("/v1/auth/login", json={"email": EMAIL, "password": "Wrong123"})).status_code == 401
    r = await client.post("/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 429 and 0 < int(r.headers["Retry-After"]) <= s.auth_rate_window_seconds
    # Other accounts are unaffected.
    _, _ = await make_user("other@example.com", "candidate")
    assert (await client.post("/v1/auth/login", json={"email": "other@example.com", "password": "Passw0rd!"})).status_code == 200


@pytest.mark.asyncio
async def test_successful_login_resets_the_counter(client):
    await client.post("/v1/auth/register", json=SIGNUP)
    for _ in range(get_settings().auth_rate_limit_per_email - 1):
        await client.post("/v1/auth/login", json={"email": EMAIL, "password": "Wrong123"})
    assert (await client.post("/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})).status_code == 200
    assert (await client.post("/v1/auth/login", json={"email": EMAIL, "password": "Wrong123"})).status_code == 401  # not 429


@pytest.mark.asyncio
async def test_protected_endpoints_reject_missing_invalid_and_expired_tokens(client):
    assert (await client.get("/v1/candidates/me")).status_code == 401
    assert (await client.get("/v1/candidates/me", headers=bearer("not-a-jwt"))).status_code == 401
    assert (await client.get("/v1/admin/content/types")).status_code == 401
    assert (await client.get("/v1/assessments/case_study")).status_code == 401

    user, _ = await make_user("x@example.com", "candidate")
    s = get_settings()
    claims = {"sub": user.id, "tid": user.tenant_id, "role": "candidate", "type": "access", "jti": "j"}
    expired = jwt.encode({**claims, "exp": utcnow() - timedelta(minutes=1)}, s.jwt_secret, algorithm="HS256")
    r = await client.get("/v1/candidates/me", headers=bearer(expired))
    assert r.status_code == 401 and r.json()["detail"] == "Session expired — sign in again"

    # A token signed with another key — even claiming admin — is rejected.
    forged = jwt.encode({**claims, "role": "admin", "exp": utcnow() + timedelta(minutes=5)}, "wrong-secret", algorithm="HS256")
    assert (await client.get("/v1/admin/content/types", headers=bearer(forged))).status_code == 401

    # A refresh token can't be used as an access token.
    await client.post("/v1/auth/register", json=SIGNUP)
    assert (await client.get("/v1/candidates/me", headers=bearer(client.cookies.get("meti_refresh")))).status_code == 401


@pytest.mark.asyncio
async def test_role_comes_from_the_database_not_the_token(client):
    _, admin = await make_user("admin@example.com", "admin")
    assert (await client.get("/v1/admin/content/types", headers=admin)).status_code == 200
    assert (await client.get("/v1/candidates/me", headers=admin)).status_code == 403

    user, headers = await make_user("c@example.com", "candidate")
    await database.users().update_one({"_id": user.id}, {"$set": {"role": "admin"}})
    assert (await client.get("/v1/admin/content/types", headers=headers)).status_code == 200  # promoted -> immediate

    _, disabled = await make_user("gone@example.com", "candidate", status="disabled")
    assert (await client.get("/v1/candidates/me", headers=disabled)).status_code == 403
    r = await client.post("/v1/auth/login", json={"email": "gone@example.com", "password": "Passw0rd!"})
    assert r.status_code == 403

    with pytest.raises(ValueError):
        require_role(["mentor"])  # only candidate + admin exist


@pytest.mark.asyncio
async def test_tenant_scope_blocks_suspended_tenant(client):
    user, headers = await make_user("c@example.com", "candidate")
    assert (await client.get("/v1/candidates/me", headers=headers)).status_code == 200
    await database.tenants().update_one({"_id": user.tenant_id}, {"$set": {"status": "suspended"}})
    r = await client.get("/v1/candidates/me", headers=headers)
    assert r.status_code == 403 and "suspended" in r.json()["detail"]


@pytest.mark.asyncio
async def test_profile_update(client):
    token = (await client.post("/v1/auth/register", json=SIGNUP)).json()["access_token"]
    r = await client.put("/v1/candidates/me", json={"full_name": "  Asha  R. Rao "}, headers=bearer(token))
    assert r.status_code == 200 and r.json()["full_name"] == "Asha R. Rao"
    assert (await client.put("/v1/candidates/me", json={"role": "admin"}, headers=bearer(token))).json()["role"] == "candidate"


@pytest.mark.asyncio
async def test_refresh_rotates_and_reuse_revokes_all_sessions(client):
    first = (await client.post("/v1/auth/register", json=SIGNUP)).json()
    old_refresh = client.cookies.get("meti_refresh")

    r = await client.post("/v1/auth/refresh")
    assert r.status_code == 200
    new_refresh = client.cookies.get("meti_refresh")
    assert new_refresh != old_refresh and r.json()["access_token"] != first["access_token"]
    assert (await client.get("/v1/auth/me", headers=bearer(r.json()["access_token"]))).json()["email"] == EMAIL

    # Replaying the rotated token is treated as theft: every session of the user is revoked.
    client.cookies.clear()
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})).status_code == 401
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": new_refresh})).status_code == 401
    assert await database.auth_sessions().count_documents({"revoked_at": None}) == 0


@pytest.mark.asyncio
async def test_logout_ends_session(client):
    await client.post("/v1/auth/register", json=SIGNUP)
    r = await client.post("/v1/auth/logout")
    assert r.status_code == 204
    assert "meti_refresh" not in client.cookies
    assert (await client.post("/v1/auth/refresh")).status_code == 401
