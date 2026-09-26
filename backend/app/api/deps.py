"""Request dependencies: who is calling (JWT), what they may do (roles), which tenant they act in."""
from typing import Callable, Iterable, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import database
from app.config import get_settings
from app.models.tenant import Tenant
from app.models.user import ROLES, User
from app.security import TokenError, decode_token
from app.services.auth import get_user
from app.services.tenants import get_by_slug

_bearer = HTTPBearer(auto_error=False, description="Access token from /v1/auth/login, /register or /refresh")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


async def current_tenant() -> Tenant:
    """Tenant for *unauthenticated* requests (register / login).

    MVP runs single-tenant, so this is the configured default tenant.
    Authenticated requests use `require_tenant_scope` (tenant from the token) instead.
    """
    slug = get_settings().default_tenant_slug
    tenant = await get_by_slug(slug)
    if tenant is None:
        raise HTTPException(503, f"Tenant '{slug}' is not set up — run: python -m scripts.seed_tenant")
    return tenant


def client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized("Sign in required")
    try:
        claims = decode_token(creds.credentials, "access")
    except TokenError as exc:
        raise _unauthorized("Session expired — sign in again" if str(exc) == "token expired" else "Invalid access token")
    # Load the user every time so disabling an account or changing roles takes effect immediately.
    user = await get_user(claims["sub"])
    if user is None or user.tenant_id != claims["tid"]:
        raise _unauthorized("Invalid access token")
    if user.status != "active":
        raise HTTPException(403, "This account is not active")
    return user


def require_role(roles: Iterable[str]) -> Callable:
    """Dependency factory: the caller must hold at least one of `roles`."""
    allowed = set(roles)
    unknown = allowed - set(ROLES)
    if unknown:
        raise ValueError(f"Unknown roles: {sorted(unknown)}")

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(403, f"Requires role: {' or '.join(sorted(allowed))}")
        return user

    return dependency


async def require_tenant_scope(user: User = Depends(get_current_user)) -> Tenant:
    """The tenant the caller belongs to; every tenant-scoped query must filter on its id."""
    doc = await database.tenants().find_one({"_id": user.tenant_id})
    if doc is None or doc.get("status") != "active":
        raise HTTPException(403, "Your organisation's access is suspended")
    return Tenant.model_validate(doc)
