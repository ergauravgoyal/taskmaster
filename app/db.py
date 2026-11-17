from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator
import asyncpg
from app.config import settings

pool: asyncpg.Pool | None = None

async def init_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return pool

async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None

@asynccontextmanager
async def connection() -> AsyncIterator[asyncpg.Connection]:
    active_pool = await init_pool()
    async with active_pool.acquire() as conn:
        yield conn

async def dependency_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    async with connection() as conn:
        yield conn
