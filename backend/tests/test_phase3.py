import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.main import app
from scripts.seed_content import seed
from tests.conftest import default_tenant, make_user

BASE = "/v1/admin/content"
VIDEO = {"title": "Explainer", "provider": "youtube", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "transcript": "Hello."}
SIGNUP = {"email": "priya@example.com", "full_name": "Priya N", "password": "Consult1ng", "consent": True}


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin():
    _, headers = await make_user("admin@example.com", "admin")
    return headers


async def publish(client, admin, type_name, key, data, new=True):
    if new:
        assert (await client.post(f"{BASE}/{type_name}", json={"key": key, "data": data}, headers=admin)).status_code == 201
    else:
        await client.post(f"{BASE}/{type_name}/{key}/draft", headers=admin)
        await client.put(f"{BASE}/{type_name}/{key}/draft", json={"data": data}, headers=admin)
    r = await client.post(f"{BASE}/{type_name}/{key}/publish", headers=admin)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_seeded_landing_is_public_and_only_published_content_is_served(client, admin):
    summary = await seed()
    assert summary["site_content"] == {"created": 1, "updated": 0, "published": 1, "skipped": 0}
    assert summary["videos"] == {"created": 1, "updated": 0, "published": 0, "skipped": 0}  # needs a real URL first

    r = await client.get("/v1/site/landing")  # no token
    assert r.status_code == 200
    body = r.json()
    assert body["key"] == "landing" and body["version"] == 1 and body["headline"] and body["cta_label"]
    assert len(body["sections"]) == 3 and len(body["steps"]) == 4 and body["video"] is None

    # Drafts are never public.
    await client.post(f"{BASE}/site_content", json={"key": "pricing", "data": {"headline": "Draft"}}, headers=admin)
    assert (await client.get("/v1/site/pricing")).status_code == 404
    # Only site_content is reachable through /v1/site.
    assert (await client.get("/v1/site/explainer")).status_code == 404


@pytest.mark.asyncio
async def test_landing_serves_the_pinned_video_version(client, admin):
    await seed()
    # The seeded video can't be published until it has a real URL.
    r = await client.post(f"{BASE}/videos/explainer/publish", headers=admin)
    assert r.status_code == 422 and {"field": "url", "message": "is required"} in r.json()["errors"]

    landing = (await client.get(f"{BASE}/site_content/landing/current", headers=admin)).json()["data"]
    await publish(client, admin, "videos", "explainer", VIDEO, new=False)
    await publish(client, admin, "site_content", "landing", {**landing, "video_key": "explainer"}, new=False)

    video = (await client.get("/v1/site/landing")).json()["video"]
    assert video["key"] == "explainer" and video["version"] == 1  # the seeded draft, completed and published
    assert video["embed_url"].startswith("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
    assert video["transcript"] == "Hello."

    # A newer video version doesn't change the published page until the page is republished.
    await publish(client, admin, "videos", "explainer", {**VIDEO, "title": "New cut"}, new=False)
    assert (await client.get("/v1/site/landing")).json()["video"]["title"] == "Explainer"


@pytest.mark.asyncio
async def test_video_url_validation(client, admin):
    for url, message in [
        ("http://insecure.example.com/v.mp4", "must be a full https:// link"),
        ("https://vimeo.com/123", "is not a recognisable YouTube link (watch, youtu.be, shorts or embed URL)"),
    ]:
        key = f"v{len(message)}"
        await client.post(f"{BASE}/videos", json={"key": key, "data": {**VIDEO, "url": url}}, headers=admin)
        errors = (await client.post(f"{BASE}/videos/{key}/validate", headers=admin)).json()["errors"]
        assert {"field": "url", "message": message} in errors
    for ok in ("https://youtu.be/dQw4w9WgXcQ", "https://www.youtube.com/shorts/dQw4w9WgXcQ", "https://www.youtube.com/embed/dQw4w9WgXcQ"):
        await client.post(f"{BASE}/videos", json={"key": "ok", "data": {**VIDEO, "url": ok}}, headers=admin)
        assert (await client.post(f"{BASE}/videos/ok/validate", headers=admin)).json()["ok"] is True
        await client.delete(f"{BASE}/videos/ok/draft", headers=admin)

    mp4 = {"title": "Clip", "provider": "mp4", "url": "https://cdn.example.com/explainer.mp4", "captions_url": "https://cdn.example.com/en.vtt"}
    await publish(client, admin, "videos", "clip", mp4)

    await client.post(f"{BASE}/site_content", json={"key": "x", "data": {"headline": "H", "subheadline": "S", "cta_label": "Go", "steps": [{"title": "only"}]}}, headers=admin)
    errors = (await client.post(f"{BASE}/site_content/x/validate", headers=admin)).json()["errors"]
    assert errors == [{"field": "steps", "message": "item 1 is missing 'body'"}]


@pytest.mark.asyncio
async def test_watched_video_is_recorded_at_registration_or_later(client, admin):
    await publish(client, admin, "videos", "explainer", VIDEO)

    # Watched before signing up -> recorded with the account.
    r = await client.post("/v1/auth/register", json={**SIGNUP, "orientation": {"video_key": "explainer", "video_version": 1}})
    assert r.status_code == 201
    assert r.json()["user"]["orientation"]["video_key"] == "explainer" and r.json()["user"]["orientation"]["watched_at"]

    # An unknown / unpublished video version is refused.
    r = await client.post("/v1/auth/register", json={**SIGNUP, "email": "x@example.com", "orientation": {"video_key": "explainer", "video_version": 9}})
    assert r.status_code == 422 and await database.users().count_documents({"email": "x@example.com"}) == 0

    # Signed-in candidate who hadn't watched yet marks it later.
    r = await client.post("/v1/auth/register", json={**SIGNUP, "email": "later@example.com"})
    token = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert r.json()["user"]["orientation"] is None
    r = await client.post("/v1/candidates/me/orientation", json={"video_key": "explainer", "video_version": 1}, headers=token)
    assert r.status_code == 200 and r.json()["orientation"]["video_version"] == 1
    assert (await client.get("/v1/candidates/me", headers=token)).json()["orientation"]["video_key"] == "explainer"
    assert (await client.post("/v1/candidates/me/orientation", json={"video_key": "nope", "video_version": 1}, headers=token)).status_code == 422
    assert (await client.post("/v1/candidates/me/orientation", json={"video_key": "explainer", "video_version": 1})).status_code == 401
    assert (await client.post("/v1/candidates/me/orientation", json={"video_key": "explainer", "video_version": 1}, headers=admin)).status_code == 403

    actions = [e["action"] async for e in database.audit_events().find({"action": "orientation.video_watched"})]
    assert actions == ["orientation.video_watched"]
