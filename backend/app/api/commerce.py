from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app import database, payments as gateway
from app.api.deps import current_tenant, require_role, require_tenant_scope
from app.config import get_settings
from app.content.registry import get_type
from app.models.tenant import Tenant
from app.models.user import User
from app.services import commerce
from app.services.content import get_version

router = APIRouter(tags=["commerce"])
candidate = require_role(["candidate"])


class CheckoutRequest(BaseModel):
    product_key: str = Field(min_length=1, max_length=64)


class ConfirmRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=255)


@router.get("/products")
async def list_products(tenant: Tenant = Depends(current_tenant)) -> list:
    """Public price list — published products only."""
    return await commerce.catalogue(tenant.id)


@router.get("/commerce/config")
async def commerce_config() -> dict:
    """Public commerce flags so the UI can render the right pricing/CTA state."""
    settings = get_settings()
    return {"free_access": settings.free_access, "payments_enabled": settings.payments_configured}


@router.post("/payments/checkout")
async def checkout(body: CheckoutRequest, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return await commerce.start_checkout(tenant.id, user, body.product_key)


@router.post("/payments/confirm")
async def confirm(body: ConfirmRequest, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return await commerce.confirm(tenant.id, user, body.session_id)


@router.post("/payments/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)) -> dict:
    try:
        event = gateway.parse_webhook(await request.body(), stripe_signature)
    except gateway.InvalidWebhook:
        raise HTTPException(400, "Invalid signature")
    return {"received": await commerce.handle_event(event)}


@router.get("/entitlements/me")
async def my_entitlements(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    ptype = get_type("products")
    owned = []
    for ent in await commerce.active_entitlements(tenant.id, user.id):
        product = await get_version(ptype, tenant.id, ent["product_key"], ent["product_version"])
        owned.append({**commerce.product_out(product.model_dump(by_alias=True)), "granted_at": ent["granted_at"], "source": ent["source"]})
    history = await database.payments().find({"tenant_id": tenant.id, "user_id": user.id}).sort("created_at", -1).to_list(50)
    return {
        "products": owned,
        "assessment_keys": sorted(await commerce.accessible_assessments(tenant.id, user.id)),
        "payments": [commerce.payment_out(p) for p in history],
    }
