import pytest
from httpx import ASGITransport, AsyncClient

from app import database
from app.main import app
from app.models.tenant import TenantCreate
from app.services.tenants import create_tenant


@pytest.mark.asyncio
async def test_health_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"mongo": "up", "redis": "up"}
    assert resp.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_indexes_bootstrap():
    await database.ensure_indexes()
    db = database.get_db()
    assert {"tenants", "users", "audit_events"} <= set(await db.list_collection_names())
    tenant_ix = await database.tenants().index_information()
    assert tenant_ix["uq_slug"]["unique"] is True
    user_ix = await database.users().index_information()
    assert user_ix["uq_tenant_email"]["key"] == [("tenant_id", 1), ("email", 1)]


@pytest.mark.asyncio
async def test_seed_tenant_is_idempotent_and_audited():
    await database.ensure_indexes()
    first, created = await create_tenant(TenantCreate(slug="acme", name="Acme"))
    again, created_again = await create_tenant(TenantCreate(slug="acme", name="Acme"))
    assert created is True and created_again is False
    assert first.id == again.id
    assert await database.tenants().count_documents({"slug": "acme"}) == 1
    event = await database.audit_events().find_one({"entity_id": first.id})
    assert event["action"] == "tenant.created"
    assert event["tenant_id"] == first.id
