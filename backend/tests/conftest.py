"""Tests run against the real MongoDB Atlas cluster + Redis, in a separate `meti_test` database.

The Atlas user may not have dropDatabase, so cleanup empties every collection
instead (indexes stay, and ensure_indexes() is idempotent).
"""
import os
from pathlib import Path

os.environ["MONGO_DB"] = "meti_test"
os.environ["ENVIRONMENT"] = "local"
os.environ["UPLOADS_DIR"] = str(Path(__file__).resolve().parent.parent / "uploads_test")
# AI is faked per test (tests replace app.ai.provider._call); never call a real provider from tests.
os.environ["AI_PROVIDER"] = ""

import pytest_asyncio  # noqa: E402

from app import cache, database  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models.tenant import TenantCreate  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security import create_token, hash_password  # noqa: E402
from app.services import rate_limit  # noqa: E402
from app.services.tenants import create_tenant  # noqa: E402


async def _empty_test_db() -> None:
    db = database.get_db()
    assert db.name == "meti_test", "refusing to clean a non-test database"
    for name in await db.list_collection_names():
        await db[name].delete_many({})
    await rate_limit.clear_all()


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    database.close_client()
    await _empty_test_db()
    yield
    await _empty_test_db()
    database.close_client()
    await cache.close_redis()


async def default_tenant():
    s = get_settings()
    tenant, _ = await create_tenant(TenantCreate(slug=s.default_tenant_slug, name=s.default_tenant_name))
    return tenant


_HASH = hash_password("Passw0rd!")  # hashing is slow on purpose — do it once


async def make_user(email: str, role: str, status: str = "active") -> tuple[User, dict]:
    """Insert a user directly (password "Passw0rd!") and return (user, Authorization headers)."""
    tenant = await default_tenant()
    user = User(tenant_id=tenant.id, email=email, full_name="Test User", role=role, password_hash=_HASH, status=status)
    await database.users().insert_one(user.to_mongo())
    token, _, _ = create_token("access", user_id=user.id, tenant_id=tenant.id, role=role)
    return user, {"Authorization": f"Bearer {token}"}
