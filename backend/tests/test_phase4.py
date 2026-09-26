import hashlib
import hmac
import json
import time

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database, payments
from app.config import get_settings
from app.main import app
from scripts.seed_content import seed
from tests.conftest import default_tenant, make_user

BASE = "/v1/admin/content"
WEBHOOK_SECRET = "whsec_test_secret"


class FakeStripe:
    """Stands in for Stripe: records sessions; the test decides when one is paid."""

    def __init__(self):
        self.sessions = {}

    async def create_checkout_session(self, *, payment_id, product_name, description, amount_minor, currency, customer_email, metadata):
        sid = f"cs_test_{len(self.sessions) + 1:04d}"
        self.sessions[sid] = {"id": sid, "url": f"https://checkout.stripe.test/{sid}", "payment_status": "unpaid",
                              "amount_total": amount_minor, "currency": currency.lower(), "metadata": metadata,
                              "customer_email": customer_email, "product_name": product_name}
        return self.sessions[sid]

    async def retrieve_checkout_session(self, session_id):
        if session_id not in self.sessions:
            raise LookupError(session_id)
        return self.sessions[session_id]

    def pay(self, sid, amount=None):
        self.sessions[sid]["payment_status"] = "paid"
        if amount is not None:
            self.sessions[sid]["amount_total"] = amount
        return self.sessions[sid]


@pytest.fixture
def stripe_fake(monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(payments, "create_checkout_session", fake.create_checkout_session)
    monkeypatch.setattr(payments, "retrieve_checkout_session", fake.retrieve_checkout_session)
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", WEBHOOK_SECRET)
    # A configured Stripe test environment has a secret key, so checkout uses the (faked) gateway
    # rather than the dev "free enrolment" fallback.
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "sk_test_fake")
    return fake


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="buyer@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Buyer One", "password": "Consult1ng", "consent": True})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def signed(event: dict):
    payload = json.dumps(event)
    ts = int(time.time())
    sig = hmac.new(WEBHOOK_SECRET.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    return {"content": payload, "headers": {"Stripe-Signature": f"t={ts},v1={sig}", "Content-Type": "application/json"}}


async def publish_capability(client):
    """The seed publishes 'capability' with its sections; return admin headers for previews."""
    _, admin = await make_user("admin@example.com", "admin")
    return admin


@pytest.mark.asyncio
async def test_public_price_list(client):
    r = await client.get("/v1/products")  # no sign-in
    assert r.status_code == 200
    assert [(p["key"], p["price"], p["currency"]) for p in r.json()] == [
        ("consulting_assessment", 25, "USD"), ("personality_values", 25, "USD"), ("bundle", 40, "USD"), ("detailed_report", 250, "USD"),
    ]


@pytest.mark.asyncio
async def test_definition_of_done_paying_unlocks_and_unpaid_is_blocked(client, stripe_fake):
    admin = await publish_capability(client)
    h = await candidate(client)

    # Unpaid: blocked even calling the API directly (admins can preview).
    r = await client.get("/v1/assessments/capability", headers=h)
    assert r.status_code == 402 and "Management Consulting Assessment" in r.json()["detail"]
    assert (await client.get("/v1/assessments/capability", headers=admin)).status_code == 200

    r = await client.post("/v1/payments/checkout", json={"product_key": "consulting_assessment"}, headers=h)
    assert r.status_code == 200 and r.json()["checkout_url"].startswith("https://checkout.stripe.test/")
    sid = next(iter(stripe_fake.sessions))
    assert stripe_fake.sessions[sid]["amount_total"] == 2500 and stripe_fake.sessions[sid]["currency"] == "usd"

    # Checkout started but not paid -> still blocked, confirm reports pending.
    assert (await client.post("/v1/payments/confirm", json={"session_id": sid}, headers=h)).json()["status"] == "pending"
    assert (await client.get("/v1/assessments/capability", headers=h)).status_code == 402

    stripe_fake.pay(sid)
    r = await client.post("/v1/payments/confirm", json={"session_id": sid}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "paid"

    r = await client.get("/v1/assessments/capability", headers=h)
    first_q = r.json()["sections"][0]["questions"][0]
    assert r.status_code == 200 and first_q["key"] == "CAP-01"
    assert "scoring_rule" not in first_q and "competency_map" not in first_q  # never leak answer keys
    # Only what was bought is unlocked.
    assert (await client.get("/v1/assessments/talent_dna", headers=h)).status_code == 402

    me = (await client.get("/v1/entitlements/me", headers=h)).json()
    assert [p["key"] for p in me["products"]] == ["consulting_assessment"]
    assert me["assessment_keys"] == ["capability", "case_study", "motivation", "profile", "written_communication"]
    assert me["payments"][0]["status"] == "paid"


@pytest.mark.asyncio
async def test_webhook_fulfils_once_and_rejects_bad_signatures(client, stripe_fake):
    h = await candidate(client)
    await client.post("/v1/payments/checkout", json={"product_key": "personality_values"}, headers=h)
    sid = next(iter(stripe_fake.sessions))
    event = {"id": "evt_1", "type": "checkout.session.completed", "data": {"object": stripe_fake.pay(sid)}}

    bad = signed(event)
    bad["headers"]["Stripe-Signature"] = bad["headers"]["Stripe-Signature"][:-4] + "0000"
    assert (await client.post("/v1/payments/webhook", **bad)).status_code == 400
    assert await database.entitlements().count_documents({}) == 0

    for _ in range(2):  # Stripe retries deliveries — must be idempotent
        r = await client.post("/v1/payments/webhook", **signed(event))
        assert r.status_code == 200 and r.json() == {"received": "checkout.session.completed"}
    assert await database.entitlements().count_documents({"product_key": "personality_values"}) == 1
    assert await database.audit_events().count_documents({"action": "payment.paid"}) == 1
    # The success page confirming afterwards changes nothing.
    assert (await client.post("/v1/payments/confirm", json={"session_id": sid}, headers=h)).json()["status"] == "paid"
    assert await database.entitlements().count_documents({}) == 1


@pytest.mark.asyncio
async def test_amount_mismatch_is_not_fulfilled_and_expiry_is_recorded(client, stripe_fake):
    h = await candidate(client)
    await client.post("/v1/payments/checkout", json={"product_key": "consulting_assessment"}, headers=h)
    await client.post("/v1/payments/checkout", json={"product_key": "personality_values"}, headers=h)
    first, second = list(stripe_fake.sessions)

    stripe_fake.pay(first, amount=1)
    assert (await client.post("/v1/payments/confirm", json={"session_id": first}, headers=h)).json()["status"] == "amount_mismatch"
    assert await database.entitlements().count_documents({}) == 0

    await client.post("/v1/payments/webhook", **signed({"type": "checkout.session.expired", "data": {"object": {"id": second}}}))
    assert (await database.payments().find_one({"stripe_session_id": second}))["status"] == "expired"


@pytest.mark.asyncio
async def test_bundle_upgrade_and_ownership_rules(client, stripe_fake):
    h = await candidate(client)

    r = await client.post("/v1/payments/checkout", json={"product_key": "detailed_report"}, headers=h)
    assert r.status_code == 409 and r.json()["detail"].startswith("Buy Management Consulting Assessment or")
    assert (await client.post("/v1/payments/checkout", json={"product_key": "nope"}, headers=h)).status_code == 404

    await client.post("/v1/payments/checkout", json={"product_key": "bundle"}, headers=h)
    sid = next(iter(stripe_fake.sessions))
    stripe_fake.pay(sid)
    await client.post("/v1/payments/confirm", json={"session_id": sid}, headers=h)

    me = (await client.get("/v1/entitlements/me", headers=h)).json()
    assert sorted((p["key"], p["source"]) for p in me["products"]) == [
        ("bundle", "stripe"), ("consulting_assessment", "bundle:bundle"), ("personality_values", "bundle:bundle"),
    ]
    assert len(me["assessment_keys"]) == 7
    for owned in ("bundle", "consulting_assessment"):
        assert (await client.post("/v1/payments/checkout", json={"product_key": owned}, headers=h)).status_code == 409
    # The upgrade is now available.
    assert (await client.post("/v1/payments/checkout", json={"product_key": "detailed_report"}, headers=h)).status_code == 200
    assert list(stripe_fake.sessions.values())[-1]["amount_total"] == 25000


@pytest.mark.asyncio
async def test_access_rules_for_checkout_and_confirm(client, stripe_fake):
    _, admin = await make_user("admin@example.com", "admin")
    assert (await client.post("/v1/payments/checkout", json={"product_key": "bundle"}, headers=admin)).status_code == 403
    assert (await client.post("/v1/payments/checkout", json={"product_key": "bundle"})).status_code == 401
    assert (await client.get("/v1/entitlements/me")).status_code == 401

    a = await candidate(client, "a@example.com")
    b = await candidate(client, "b@example.com")
    await client.post("/v1/payments/checkout", json={"product_key": "bundle"}, headers=a)
    sid = next(iter(stripe_fake.sessions))
    stripe_fake.pay(sid)
    # Someone else's session can't be confirmed to your account.
    assert (await client.post("/v1/payments/confirm", json={"session_id": sid}, headers=b)).status_code == 404
    assert await database.entitlements().count_documents({}) == 0


@pytest.mark.asyncio
async def test_checkout_without_stripe_free_enrols_in_dev(client, monkeypatch):
    # No Stripe configured, local/dev environment → buying enrols for free so the app is fully usable.
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "")
    h = await candidate(client)
    r = await client.post("/v1/payments/checkout", json={"product_key": "consulting_assessment"}, headers=h)
    assert r.status_code == 200 and r.json()["free"] is True and r.json()["checkout_url"] is None
    # The entitlement is granted, so the included assessment opens.
    assert (await client.get("/v1/assessments/capability", headers=h)).status_code == 200
    # A bundle free-enrolment grants the bundled products too.
    h2 = await candidate(client, "freebundle@example.com")
    await client.post("/v1/payments/checkout", json={"product_key": "bundle"}, headers=h2)
    owned = {p["key"] for p in (await client.get("/v1/entitlements/me", headers=h2)).json()["products"]}
    assert {"bundle", "consulting_assessment", "personality_values"} <= owned


@pytest.mark.asyncio
async def test_checkout_without_stripe_in_production_is_a_clear_503(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "")
    monkeypatch.setattr(get_settings(), "environment", "prod")  # not dev → real payment required
    h = await candidate(client)
    r = await client.post("/v1/payments/checkout", json={"product_key": "bundle"}, headers=h)
    assert r.status_code == 503 and "STRIPE_SECRET_KEY" in r.json()["detail"]
    assert await database.payments().count_documents({}) == 0
