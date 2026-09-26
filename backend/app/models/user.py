import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.common import TenantScoped

# MVP has exactly two roles (plan v2 Phase 2): admin absorbs authoring, pricing and score approval.
Role = Literal["candidate", "admin"]
ROLES: tuple = Role.__args__
UserStatus = Literal["active", "disabled"]


class OrientationIn(BaseModel):
    """Which published explainer video the visitor marked as watched (plan v2 Phase 3)."""

    video_key: str = Field(min_length=1, max_length=64)
    video_version: int = Field(ge=1)


class Orientation(OrientationIn):
    watched_at: datetime


class User(TenantScoped):
    email: str  # stored lower-cased
    full_name: str
    role: Role = "candidate"
    password_hash: Optional[str] = None  # None only for accounts created before password sign-in existed
    status: UserStatus = "active"
    # The single consent checkbox at registration (privacy + AI-assisted scoring), with its timestamp.
    consent_accepted_at: Optional[datetime] = None
    orientation: Optional[Orientation] = None
    last_login_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def _legacy_status(cls, v: str) -> str:
        # Accounts from the retired OTP design may be "pending_verification" — they can't sign in.
        return v if v in ("active", "disabled") else "disabled"

    def public(self) -> dict:
        return self.model_dump(include={"id", "email", "full_name", "role", "status", "consent_accepted_at", "orientation", "last_login_at", "created_at"})


def _clean_name(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 2:
        raise ValueError("Please enter your full name")
    return value


class _EmailBody(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class RegisterRequest(_EmailBody):
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    consent: bool
    # Set when the visitor marked the explainer video as watched before signing up.
    orientation: Optional[OrientationIn] = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean_name(v)

    @field_validator("password")
    @classmethod
    def _strong_enough(cls, v: str) -> str:
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("Password must contain at least one letter and one number")
        return v

    @field_validator("consent")
    @classmethod
    def _must_consent(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Please accept the privacy notice and AI-assisted scoring to create an account")
        return v


class LoginRequest(_EmailBody):
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        return _clean_name(v) if v is not None else v
