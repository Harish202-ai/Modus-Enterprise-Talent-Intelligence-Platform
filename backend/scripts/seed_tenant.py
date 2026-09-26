"""Create a tenant (idempotent on slug).

    python -m scripts.seed_tenant                       # default tenant from DEFAULT_TENANT_SLUG
    python -m scripts.seed_tenant --slug acme --name "Acme Consulting"
"""
import argparse
import asyncio

from app import database
from app.config import get_settings
from app.models.tenant import TenantCreate
from app.services.tenants import create_tenant


async def main(slug: str, name: str) -> None:
    await database.ensure_indexes()
    tenant, created = await create_tenant(TenantCreate(slug=slug, name=name))
    state = "created" if created else "already exists"
    print(f"Tenant {state}: id={tenant.id} slug={tenant.slug} name={tenant.name!r} status={tenant.status}")
    database.close_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", default=get_settings().default_tenant_slug)
    parser.add_argument("--name", default=get_settings().default_tenant_name)
    args = parser.parse_args()
    asyncio.run(main(args.slug, args.name))
