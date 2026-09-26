"""Create all collections + indexes. Safe to run repeatedly.

    python -m scripts.bootstrap_indexes
"""
import asyncio

from app import database
from app.config import get_settings


async def main() -> None:
    created = await database.ensure_indexes()
    print(f"Database '{get_settings().mongo_db}':")
    for name, indexes in created.items():
        print(f"  {name}: {', '.join(indexes)}")
    database.close_client()


if __name__ == "__main__":
    asyncio.run(main())
