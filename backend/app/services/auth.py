"""Email + password authentication, JWT sessions with refresh-token rotation.

- register: creates a candidate (consent checkbox required, timestamped) and signs them in.
- login: rate-limited per email and per IP; the error never says which part was wrong.
- refresh: rotates the refresh token; presenting an already-rotated token revokes every session of that user.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app import database
from app.config import get_settings
from app.models.common import utcnow
from app.models.user import Orientation, OrientationIn, User
from app.security import TokenError, create_token, decode_token, hash_ip, hash_password, verify_password
from app.services import audit, orientation as orientation_svc, rate_limit


class AuthError(Exception):
    def __init__(self, status_code: int, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.retry_after = retry_after


@dataclass
class Session:
    user: User
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


async def get_user(user_id: str) -> Optional[User]:
    doc = await database.users().find_one({"_id": user_id})
    return User.model_validate(doc) if doc else None


async def get_user_by_email(tenant_id: str, email_addr: str) -> Optional[User]:
    doc = await database.users().find_one({"tenant_id": tenant_id, "email": email_addr})
    return User.model_validate(doc) if doc else None


def _human(seconds: int) -> str:
    return f"{seconds} seconds" if seconds < 90 else f"{round(seconds / 60)} minutes"


async def _limit(email_addr: str, ip: Optional[str]) -> None:
    s = get_settings()
    try:
        await rate_limit.hit("login", f"email:{email_addr}", s.auth_rate_limit_per_email, s.auth_rate_window_seconds)
        if ip:
            await rate_limit.hit("login", f"ip:{hash_ip(ip)}", s.auth_rate_limit_per_ip, s.auth_rate_window_seconds)
    except rate_limit.RateLimited as exc:
        raise AuthError(429, f"Too many sign-in attempts — try again in {_human(exc.retry_after)}", exc.retry_after)


async def register(
    tenant_id: str,
    email_addr: str,
    full_name: str,
    password: str,
    ip: Optional[str],
    user_agent: Optional[str],
    orientation: Optional[OrientationIn] = None,
) -> Session:
    if await get_user_by_email(tenant_id, email_addr):
        raise AuthError(409, "This email is already registered — sign in instead")
    if orientation:
        await orientation_svc.check_video(tenant_id, orientation)
    now = utcnow()
    user = User(
        tenant_id=tenant_id,
        email=email_addr,
        full_name=full_name,
        password_hash=hash_password(password),
        consent_accepted_at=now,
        orientation=Orientation(**orientation.model_dump(), watched_at=now) if orientation else None,
        last_login_at=now,
    )
    try:
        await database.users().insert_one(user.to_mongo())
    except DuplicateKeyError:
        raise AuthError(409, "This email is already registered — sign in instead")
    await audit.record(
        tenant_id=tenant_id, actor_id=user.id, candidate_id=user.id, entity_type="user", entity_id=user.id,
        action="user.registered",
        metadata={"consent_accepted_at": now.isoformat(), "orientation": orientation.model_dump() if orientation else None},
    )
    return await _start_session(user, ip, user_agent)


async def login(tenant_id: str, email_addr: str, password: str, ip: Optional[str], user_agent: Optional[str]) -> Session:
    await _limit(email_addr, ip)
    user = await get_user_by_email(tenant_id, email_addr)
    if not verify_password(password, user.password_hash if user else None):
        raise AuthError(401, "Incorrect email or password")
    if user.status != "active":
        raise AuthError(403, "This account is disabled — contact support")
    await rate_limit.reset("login", f"email:{email_addr}")
    doc = await database.users().find_one_and_update(
        {"_id": user.id}, {"$set": {"last_login_at": utcnow()}}, return_document=ReturnDocument.AFTER
    )
    user = User.model_validate(doc)
    await audit.record(tenant_id=tenant_id, actor_id=user.id, entity_type="user", entity_id=user.id, action="auth.login")
    return await _start_session(user, ip, user_agent)


async def _start_session(user: User, ip: Optional[str], user_agent: Optional[str]) -> Session:
    access, _, access_exp = create_token("access", user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    refresh, jti, refresh_exp = create_token("refresh", user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    await database.auth_sessions().insert_one(
        {
            "_id": jti,
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "created_at": utcnow(),
            "expires_at": refresh_exp,
            "revoked_at": None,
            "ip_hash": hash_ip(ip),
            "user_agent": (user_agent or "")[:300],
        }
    )
    return Session(user, access, access_exp, refresh, refresh_exp)


async def refresh(refresh_token: Optional[str], ip: Optional[str], user_agent: Optional[str]) -> Session:
    if not refresh_token:
        raise AuthError(401, "Not signed in")
    try:
        claims = decode_token(refresh_token, "refresh")
    except TokenError:
        raise AuthError(401, "Session expired — sign in again")
    now = utcnow()
    # Atomically revoke the presented token; if it was already revoked, it's being replayed.
    session = await database.auth_sessions().find_one_and_update(
        {"_id": claims["jti"], "revoked_at": None}, {"$set": {"revoked_at": now, "revoked_reason": "rotated"}}
    )
    if session is None:
        if await database.auth_sessions().find_one({"_id": claims["jti"]}, projection={"_id": 1}):
            await revoke_all(claims["sub"], "refresh_token_reuse")
        raise AuthError(401, "Session expired — sign in again")
    user = await get_user(session["user_id"])
    if user is None or user.status != "active":
        raise AuthError(401, "Session expired — sign in again")
    return await _start_session(user, ip, user_agent)


async def logout(refresh_token: Optional[str]) -> None:
    if not refresh_token:
        return
    try:
        claims = decode_token(refresh_token, "refresh")
    except TokenError:
        return
    result = await database.auth_sessions().update_one(
        {"_id": claims["jti"], "revoked_at": None}, {"$set": {"revoked_at": utcnow(), "revoked_reason": "logout"}}
    )
    if result.modified_count:
        await audit.record(tenant_id=claims["tid"], actor_id=claims["sub"], entity_type="user", entity_id=claims["sub"], action="auth.logout")


async def revoke_all(user_id: str, reason: str) -> None:
    await database.auth_sessions().update_many(
        {"user_id": user_id, "revoked_at": None}, {"$set": {"revoked_at": utcnow(), "revoked_reason": reason}}
    )
