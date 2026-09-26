"""Create an admin in the default tenant, or promote an existing user to admin and set their password.

    python -m scripts.create_admin --email you@company.com --name "Your Name"

The password is asked for interactively (not echoed). For automation you may pass --password.
"""
import argparse
import asyncio
import getpass

from pydantic import ValidationError
from pymongo import ReturnDocument

from app import database
from app.config import get_settings
from app.models.common import utcnow
from app.models.tenant import TenantCreate
from app.models.user import RegisterRequest, User
from app.security import hash_password
from app.services import audit
from app.services.tenants import create_tenant


async def main(email: str, name: str, password: str) -> None:
    settings = get_settings()
    await database.ensure_indexes()
    tenant, _ = await create_tenant(TenantCreate(slug=settings.default_tenant_slug, name=settings.default_tenant_name))
    now = utcnow()
    existing = await database.users().find_one({"tenant_id": tenant.id, "email": email})
    if existing:
        doc = await database.users().find_one_and_update(
            {"_id": existing["_id"]},
            {"$set": {"role": "admin", "status": "active", "password_hash": hash_password(password), "updated_at": now},
             "$unset": {"roles": "", "email_verified_at": "", "locale": ""}},  # fields from the retired OTP design
            return_document=ReturnDocument.AFTER,
        )
        user, action = User.model_validate(doc), "user.promoted_to_admin"
    else:
        user = User(tenant_id=tenant.id, email=email, full_name=name, role="admin", password_hash=hash_password(password))
        await database.users().insert_one(user.to_mongo())
        action = "user.created"
    await audit.record(tenant_id=tenant.id, actor_id="system", entity_type="user", entity_id=user.id, action=action, metadata={"role": "admin"})
    print(f"{'Updated' if existing else 'Created'} admin {user.email} — sign in at http://localhost:3000/login")
    database.close_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", help="omit to be prompted")
    args = parser.parse_args()
    password = args.password or getpass.getpass("Password (8+ chars, a letter and a number): ")
    try:
        body = RegisterRequest(email=args.email, full_name=args.name, password=password, consent=True)  # same rules as sign-up
    except ValidationError as exc:
        raise SystemExit("; ".join(e["msg"].replace("Value error, ", "") for e in exc.errors()))
    asyncio.run(main(body.email, body.full_name, body.password))
