import asyncio
import os
from pathlib import Path
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://taskmaster:taskmaster@localhost:5433/taskmaster")

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        for path in sorted(Path("migrations").glob("*.sql")):
            if await conn.fetchval("SELECT 1 FROM schema_migrations WHERE filename=$1", path.name):
                continue
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute("INSERT INTO schema_migrations(filename) VALUES($1)", path.name)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
