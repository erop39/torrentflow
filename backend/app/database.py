import os
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("TORRENTFLOW_DATABASE_URL", "sqlite+aiosqlite:///./data/torrentflow.db")
if DATABASE_URL == "sqlite+aiosqlite:///./data/torrentflow.db":
    Path("data").mkdir(exist_ok=True)

engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
