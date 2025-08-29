#!/usr/bin/env python3
"""Check incidents table and fix enum issue."""

import os
import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def normalize_url(raw: str):
    """Normalize URL for asyncpg."""
    if raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[12:]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[13:]
    
    parts = urlsplit(raw)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.pop("sslmode", None)
    
    host = (parts.hostname or "").lower()
    is_internal = host.endswith(".internal") or host.endswith(".flycast") or host.startswith("fdaa:")
    
    if is_internal:
        q["ssl"] = "disable"
        connect_args = {}
    else:
        q["ssl"] = "require"
        connect_args = {"ssl": "require"}
    
    raw = urlunsplit(parts._replace(query=urlencode(q)))
    return raw, connect_args


async def main():
    """Check and fix incidents table."""
    try:
        url, ca = normalize_url(os.environ["POSTGRES_URL"])
        eng = create_async_engine(url, connect_args=ca)
        
        async with eng.begin() as conn:
            # Check current column type
            result = await conn.execute(sa.text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'incidents' AND column_name = 'status'"
            ))
            row = result.fetchone()
            print(f"Current status column: {row}")
            
            # Check if enum type exists
            result = await conn.execute(sa.text(
                "SELECT typname FROM pg_type WHERE typname = 'incident_status'"
            ))
            enum_exists = result.fetchone()
            print(f"Enum type exists: {bool(enum_exists)}")
            
            # Fix the column type if needed
            if row and row[1] != "USER-DEFINED":
                print("Fixing status column type...")
                await conn.execute(sa.text("""
                    DO $$ BEGIN
                        CREATE TYPE incident_status AS ENUM ('active', 'acknowledged', 'canceled', 'exhausted');
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """))
                
                await conn.execute(sa.text("""
                    ALTER TABLE incidents 
                    ALTER COLUMN status TYPE incident_status 
                    USING status::incident_status
                """))
                print("Status column fixed!")
            
            # Verify the fix
            result = await conn.execute(sa.text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'incidents' AND column_name = 'status'"
            ))
            row = result.fetchone()
            print(f"After fix - status column: {row}")
            
        await eng.dispose()
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
