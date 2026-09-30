from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base


def make_engine(url: str) -> AsyncEngine:
    if url.startswith('sqlite+'):
        Path('data').mkdir(parents=True, exist_ok=True)
    connect_args = {'check_same_thread': False} if url.startswith('sqlite+') else {}
    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
