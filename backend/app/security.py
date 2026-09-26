"""Token and secret primitives: JWT access/refresh tokens, bcrypt password hashing."""
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional

import jwt
from passlib.hash import bcrypt

from app.config import get_settings
from app.models.common import utcnow

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]

_password_hasher = bcrypt.using(rounds=12)
# Verified against when the email is unknown, so a login takes the same time either way.
_DUMMY_HASH = _password_hasher.hash("timing-equaliser-not-a-real-password")


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: Optional[str]) -> bool:
    try:
        return _password_hasher.verify(password, hashed or _DUMMY_HASH) and hashed is not None
    except ValueError:
        return False


def hash_ip(ip: Optional[str]) -> Optional[str]:
    """Keyed hash so client IPs are never stored in the clear."""
    if not ip:
        return None
    return hmac.new(get_settings().jwt_secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def create_token(token_type: TokenType, *, user_id: str, tenant_id: str, role: str, jti: Optional[str] = None) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at)."""
    settings = get_settings()
    now = utcnow()
    ttl = timedelta(minutes=settings.jwt_access_ttl_minutes) if token_type == "access" else timedelta(days=settings.jwt_refresh_ttl_days)
    expires_at = now + ttl
    jti = jti or uuid.uuid4().hex
    payload = {"sub": user_id, "tid": tenant_id, "role": role, "type": token_type, "jti": jti, "iat": now, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM), jti, expires_at


def decode_token(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM], options={"require": ["exp", "sub", "tid", "type", "jti"]})
    except jwt.ExpiredSignatureError:
        raise TokenError("token expired")
    except jwt.InvalidTokenError:
        raise TokenError("invalid token")
    if payload.get("type") != expected_type:
        raise TokenError("wrong token type")
    return payload
