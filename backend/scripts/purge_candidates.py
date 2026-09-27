"""Delete every candidate account and all candidate-generated data for the default tenant.

    python -m scripts.purge_candidates            # dry run — shows what WOULD be deleted
    python -m scripts.purge_candidates --yes       # actually delete

Keeps the tenant, all seeded content (products, questions, prompts, site content, support KB)
and every admin account. Removes candidates and everything tied to them: assessment attempts,
uploaded files (resumes/videos) records, evidence claims, scores, roadmaps, interviews,
entitlements, payments and their auth sessions.

Irreversible. Intended for clearing test/demo candidates so the admin view starts clean.
"""
import argparse
import asyncio

from app import database
from app.config import get_settings
from app.services.tenants import get_by_slug

# Collections that only ever hold candidate-generated data (scoped by tenant_id).
CANDIDATE_DATA = [
    ("attempts", database.attempts),
    ("files", database.files),
    ("evidence_claims", database.evidence_claims),
    ("scores", database.scores),
    ("roadmaps", database.roadmaps),
    ("interviews", database.interviews),
    ("entitlements", database.entitlements),
    ("payments", database.payments),
]


async def main(apply: bool) -> None:
    settings = get_settings()
    tenant = await get_by_slug(settings.default_tenant_slug)
    if tenant is None:
        raise SystemExit(f"No tenant '{settings.default_tenant_slug}'. Run: python -m scripts.seed_tenant")
    tid = tenant.id

    candidates = await database.users().find({"tenant_id": tid, "role": "candidate"}).to_list(None)
    candidate_ids = [u["_id"] for u in candidates]

    print(f"Tenant '{settings.default_tenant_slug}' ({tid}):")
    print(f"  candidate accounts: {len(candidate_ids)}")
    for name, accessor in CANDIDATE_DATA:
        n = await accessor().count_documents({"tenant_id": tid})
        print(f"  {name}: {n}")
    sessions = (
        await database.auth_sessions().count_documents({"tenant_id": tid, "user_id": {"$in": candidate_ids}})
        if candidate_ids
        else 0
    )
    print(f"  auth_sessions (candidate): {sessions}")

    if not candidate_ids:
        print("\nNothing to delete — no candidate accounts.")
        database.close_client()
        return

    if not apply:
        print("\nDRY RUN — nothing deleted. Re-run with --yes to delete the above.")
        database.close_client()
        return

    print("\nDeleting…")
    for name, accessor in CANDIDATE_DATA:
        res = await accessor().delete_many({"tenant_id": tid})
        print(f"  {name}: deleted {res.deleted_count}")
    res = await database.auth_sessions().delete_many({"tenant_id": tid, "user_id": {"$in": candidate_ids}})
    print(f"  auth_sessions: deleted {res.deleted_count}")
    res = await database.users().delete_many({"tenant_id": tid, "role": "candidate"})
    print(f"  candidate accounts: deleted {res.deleted_count}")
    print("\nDone. Admin accounts and seeded content were left untouched.")
    database.close_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="actually delete (without this it's a dry run)")
    asyncio.run(main(parser.parse_args().yes))
