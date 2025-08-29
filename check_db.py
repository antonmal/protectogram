import os
import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

def normalize_url(raw: str):
    if raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[12:]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[14:]
    
    parts = urlsplit(raw)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "sslmode" in q:
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

async def test():
    try:
        url, ca = normalize_url(os.environ['POSTGRES_URL'])
        eng = create_async_engine(url, connect_args=ca)
        
        async with eng.begin() as conn:
            # Check users
            result = await conn.execute(sa.text("SELECT COUNT(*) FROM users"))
            users_count = result.scalar()
            print(f'Users: {users_count}')
            
            # Check incidents
            result = await conn.execute(sa.text("SELECT COUNT(*) FROM incidents"))
            incidents_count = result.scalar()
            print(f'Incidents: {incidents_count}')
            
            # Check member_links
            result = await conn.execute(sa.text("SELECT COUNT(*) FROM member_links"))
            links_count = result.scalar()
            print(f'Member Links: {links_count}')
            
            # Check call_attempts
            result = await conn.execute(sa.text("SELECT COUNT(*) FROM call_attempts"))
            calls_count = result.scalar()
            print(f'Call Attempts: {calls_count}')
            
            # Check inbox_events
            result = await conn.execute(sa.text("SELECT COUNT(*) FROM inbox_events"))
            inbox_count = result.scalar()
            print(f'Inbox Events: {inbox_count}')
            
            # Check outbox_messages
            result = await conn.execute(sa.text("SELECT COUNT(*) FROM outbox_messages"))
            outbox_count = result.scalar()
            print(f'Outbox Messages: {outbox_count}')
        
        await eng.dispose()
        
    except Exception as e:
        print('Error:', e)

if __name__ == "__main__":
    asyncio.run(test())
