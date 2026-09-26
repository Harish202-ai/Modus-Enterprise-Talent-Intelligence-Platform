"""AI video interview — questions/config, recording upload with proctoring metadata, admin visibility.
(The webcam capture + face-away detection run in the browser and are verified there, not here.)"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.main import app
from app.models.common import new_id, utcnow
from scripts.seed_content import seed
from tests.conftest import default_tenant, make_user
from tests.fixture_files import MP4_BYTES


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="iv@example.com", product="bundle"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Vic Video", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if product:
        user = await database.users().find_one({"email": email})
        products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
        for key in [product, *products[product].get("bundled_product_keys", [])]:
            await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                      "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                      "granted_at": utcnow(), "revoked_at": None})
    return h


@pytest.mark.asyncio
async def test_interview_config_lists_timed_questions(client):
    h = await candidate(client)
    cfg = (await client.get("/v1/me/interview", headers=h)).json()
    assert cfg["max_warnings"] == 5 and len(cfg["questions"]) == 5
    assert all("prompt" in q and q["seconds"] >= 15 for q in cfg["questions"])
    assert [q["key"] for q in cfg["questions"]] == ["IV-01", "IV-02", "IV-03", "IV-04", "IV-05"]  # ordered


@pytest.mark.asyncio
async def test_submit_recording_with_proctoring_metadata_and_admin_review(client):
    h = await candidate(client)
    files = {"file": ("interview.mp4", MP4_BYTES, "video/mp4")}
    data = {"warnings": "5", "auto_submitted": "true", "answered": "4", "duration_seconds": "312"}
    r = await client.post("/v1/me/interview", headers=h, files=files, data=data)
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["warnings"] == 5 and rec["auto_submitted"] is True and rec["answered"] == 4 and rec["file"]["kind"] == "mp4"

    assert (await client.get("/v1/me/interview/latest", headers=h)).json()["interview"]["id"] == rec["id"]

    # Admin sees the interview (with warnings) on the candidate dashboard, and can fetch the video.
    user = await database.users().find_one({"email": "iv@example.com"})
    _, admin = await make_user("admin@example.com", "admin")
    detail = (await client.get(f"/v1/admin/candidates/{user['_id']}", headers=admin)).json()
    assert len(detail["interviews"]) == 1 and detail["interviews"][0]["auto_submitted"] is True
    file_id = detail["interviews"][0]["file"]["id"]
    got = await client.get(f"/v1/files/{file_id}", headers=admin)
    assert got.status_code == 200 and got.content[:4] == MP4_BYTES[:4]


@pytest.mark.asyncio
async def test_interview_requires_the_assessment(client):
    none = await candidate(client, "noiv@example.com", product=None)
    assert (await client.get("/v1/me/interview", headers=none)).status_code == 402
    files = {"file": ("interview.mp4", MP4_BYTES, "video/mp4")}
    assert (await client.post("/v1/me/interview", headers=none, files=files, data={"warnings": "0"})).status_code == 402
