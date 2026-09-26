"""Email + password auth. The refresh token lives only in an httpOnly cookie scoped to /v1/auth."""
from typing import Optional

from fastapi import APIRouter, Body, Depends, Request, Response, status

from app.api.deps import client_ip, current_tenant, get_current_user
from app.config import get_settings
from app.models.tenant import Tenant
from app.models.user import LoginRequest, RegisterRequest, User
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_path() -> str:
    return f"{get_settings().api_prefix}/auth"


def _session_response(session: auth.Session, response: Response) -> dict:
    s = get_settings()
    response.set_cookie(
        s.refresh_cookie_name,
        session.refresh_token,
        max_age=s.jwt_refresh_ttl_days * 86400,
        httponly=True,
        secure=not s.is_dev,
        samesite="lax",
        path=_cookie_path(),
    )
    return {
        "access_token": session.access_token,
        "token_type": "bearer",
        "expires_at": session.access_expires_at,
        "user": session.user.public(),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, response: Response, tenant: Tenant = Depends(current_tenant)) -> dict:
    """Create a candidate account (consent checkbox must be ticked) and sign in."""
    session = await auth.register(
        tenant.id, body.email, body.full_name, body.password, client_ip(request), request.headers.get("user-agent"), body.orientation
    )
    return _session_response(session, response)


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response, tenant: Tenant = Depends(current_tenant)) -> dict:
    session = await auth.login(tenant.id, body.email, body.password, client_ip(request), request.headers.get("user-agent"))
    return _session_response(session, response)


@router.post("/refresh")
async def refresh(request: Request, response: Response, refresh_token: Optional[str] = Body(None, embed=True)) -> dict:
    """Uses the httpOnly cookie; non-browser clients may send {"refresh_token": "..."} instead."""
    token = request.cookies.get(get_settings().refresh_cookie_name) or refresh_token
    session = await auth.refresh(token, client_ip(request), request.headers.get("user-agent"))
    return _session_response(session, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, refresh_token: Optional[str] = Body(None, embed=True)) -> Response:
    s = get_settings()
    await auth.logout(request.cookies.get(s.refresh_cookie_name) or refresh_token)
    response.delete_cookie(s.refresh_cookie_name, path=_cookie_path())
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return user.public()
