"""Stripe gateway — the only module that talks to Stripe (test mode in the MVP).

Kept tiny and swappable so tests can replace it; everything else works with plain dicts.
"""
import asyncio
import json
from typing import Optional

import stripe

from app.config import get_settings


class PaymentsUnavailable(Exception):
    pass


class InvalidWebhook(Exception):
    pass


def _client() -> stripe.StripeClient:
    key = get_settings().stripe_secret_key
    if not key:
        raise PaymentsUnavailable("Payments aren't configured yet — add STRIPE_SECRET_KEY to backend/.env")
    return stripe.StripeClient(key)


def _plain(obj) -> dict:
    """Stripe objects -> plain nested dicts (via their JSON form, the SDK's public representation)."""
    return json.loads(str(obj))


def _create(params: dict) -> dict:
    return _plain(_client().checkout.sessions.create(params=params))


def _retrieve(session_id: str) -> dict:
    return _plain(_client().checkout.sessions.retrieve(session_id))


async def create_checkout_session(
    *, payment_id: str, product_name: str, description: Optional[str], amount_minor: int, currency: str, customer_email: str, metadata: dict
) -> dict:
    s = get_settings()
    params = {
        "mode": "payment",
        "client_reference_id": payment_id,
        "customer_email": customer_email,
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": currency.lower(),
                    "unit_amount": amount_minor,
                    "product_data": {"name": product_name, **({"description": description} if description else {})},
                },
            }
        ],
        "metadata": metadata,
        "success_url": f"{s.frontend_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{s.frontend_url}/pricing?cancelled=1",
    }
    try:
        return await asyncio.to_thread(_create, params)
    except stripe.StripeError as exc:
        raise PaymentsUnavailable(f"Stripe refused the checkout: {exc.user_message or exc}") from exc


async def retrieve_checkout_session(session_id: str) -> dict:
    try:
        return await asyncio.to_thread(_retrieve, session_id)
    except stripe.InvalidRequestError as exc:
        raise LookupError("Unknown checkout session") from exc
    except stripe.StripeError as exc:
        raise PaymentsUnavailable(f"Couldn't reach Stripe: {exc.user_message or exc}") from exc


def parse_webhook(payload: bytes, signature: Optional[str]) -> dict:
    secret = get_settings().stripe_webhook_secret
    if not secret:
        raise PaymentsUnavailable("Webhook secret not configured — set STRIPE_WEBHOOK_SECRET")
    try:
        return _plain(stripe.Webhook.construct_event(payload, signature or "", secret))
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhook("Invalid Stripe signature") from exc
