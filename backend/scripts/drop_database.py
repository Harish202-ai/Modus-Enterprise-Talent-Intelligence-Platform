"""Drop one database on the cluster in MONGO_URI, after showing what's in it and asking to confirm.

    python -m scripts.drop_database METI

Irreversible. Asks you to type the database name before deleting anything.
Drops every collection (works with readWriteAnyDatabase, which cannot dropDatabase).
"""
import argparse
import asyncio

from app import database


async def main(name: str) -> None:
    client = database.get_client()
    names = await client.list_database_names()
    if name not in names:
        print(f"No database named '{name}'. Databases on this cluster: {', '.join(names)}")
        return
    db = client[name]
    print(f"Database '{name}' contains:")
    for coll in sorted(await db.list_collection_names()):
        print(f"  {coll}: {await db[coll].count_documents({})} documents")
    answer = input(f"\nThis permanently deletes '{name}'. Type the database name to confirm: ").strip()
    if answer != name:
        print("Cancelled — nothing was deleted.")
        return
    # Drop collection by collection: Atlas' readWriteAnyDatabase role allows dropCollection but not
    # dropDatabase, and a database with no collections left disappears on its own.
    for coll in await db.list_collection_names():
        await db.drop_collection(coll)
        print(f"  dropped {coll}")
    remaining = await client.list_database_names()
    state = "still exists" if name in remaining else "is gone"
    print(f"'{name}' {state}. Databases now: {', '.join(remaining)}")
    database.close_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="database to drop (case-sensitive)")
    asyncio.run(main(parser.parse_args().name))
