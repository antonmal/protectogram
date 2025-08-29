import asyncio
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine


def normalize_url(raw):
    if raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[12:]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[13:]

    p = urlsplit(raw)
    q = dict(parse_qsl(p.query))
    q.pop("sslmode", None)

    host = p.hostname.lower()
    if (
        host.endswith(".internal")
        or host.endswith(".flycast")
        or host.startswith("fdaa:")
    ):
        q["ssl"] = "disable"
        ca = {}
    else:
        q["ssl"] = "require"
        ca = {"ssl": "require"}

    raw = urlunsplit(p._replace(query=urlencode(q)))
    return raw, ca


async def test():
    try:
        url, ca = normalize_url(os.environ["POSTGRES_URL"])
        eng = create_async_engine(url, connect_args=ca)
        async with eng.begin() as conn:
            result = await conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
                )
            )
            tables = [row[0] for row in result.fetchall()]
            print("Tables in database:")
            for table in tables:
                print(f"  - {table}")

            result = await conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables WHERE table_name = 'alembic_version'"
                )
            )
            alembic_exists = result.fetchone() is not None
            print(f"\nAlembic version table exists: {alembic_exists}")

            if alembic_exists:
                result = await conn.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                )
                version = result.scalar()
                print(f"Current migration version: {version}")
        await eng.dispose()
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    asyncio.run(test())
