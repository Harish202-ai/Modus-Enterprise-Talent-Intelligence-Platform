"""Remove every authored content version, and the collections the reduced MVP no longer uses, so seed_content starts clean.

    python -m scripts.reset_content

Shows what will be removed and asks you to type RESET. Keeps tenants, users, sessions and
the audit trail. Irreversible. Works with an Atlas `readWriteAnyDatabase` user (drops collections).
"""
import asyncio

from app import database
from app.config import get_settings
from app.content.registry import CONTENT_TYPES

# Collections from the pre-v4 build (22 forms, 20 agents, price book, OTP login, versioned consent).
RETIRED = ("assessment_definitions", "prompt_versions", "price_book", "consent_policies", "consent_records", "otp_codes")


async def main() -> None:
    db = database.get_db()
    existing = set(await db.list_collection_names())
    targets = [n for n in (*CONTENT_TYPES, *RETIRED) if n in existing]
    print(f"Database '{get_settings().mongo_db}' — these collections will be dropped:")
    total = 0
    for name in targets:
        count = await db[name].count_documents({})
        total += count
        print(f"  {name}: {count} documents{'  (retired)' if name in RETIRED else ''}")
    if not targets:
        print("  (nothing to remove)")
        return
    if input(f"\nPermanently delete these {total} documents? Type RESET to confirm: ").strip() != "RESET":
        print("Cancelled — nothing was deleted.")
        return
    for name in targets:
        await db.drop_collection(name)
    print("Done. Now run: python -m scripts.seed_content")
    database.close_client()


if __name__ == "__main__":
    asyncio.run(main())
