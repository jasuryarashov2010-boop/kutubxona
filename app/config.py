from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def parse_admin_ids(value: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in (value or '').split(','):
        part = part.strip()
        if part:
            ids.add(int(part))
    if len(ids) != 2:
        raise RuntimeError('ADMIN_IDS must contain exactly 2 numeric Telegram IDs')
    return frozenset(ids)


def normalize_database_url(value: str) -> str:
    value = value.strip()
    if value.startswith('postgres://'):
        return 'postgresql+asyncpg://' + value[len('postgres://'):]
    if value.startswith('postgresql://'):
        return 'postgresql+asyncpg://' + value[len('postgresql://'):]
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    bot_username: str
    database_url: str
    redis_url: str
    webhook_base_url: str
    webhook_secret: str
    port: int

    @classmethod
    def from_env(cls) -> 'Settings':
        token = os.getenv('BOT_TOKEN', '').strip()
        if not token:
            raise RuntimeError('BOT_TOKEN is required')
        database_url = normalize_database_url(os.getenv('DATABASE_URL', '').strip())
        if not database_url:
            database_url = 'sqlite+aiosqlite:///./data/kitobxon.db'
        redis_url = os.getenv('REDIS_URL', '').strip()
        if not redis_url:
            redis_url = 'redis://localhost:6379/0'
        return cls(
            bot_token=token,
            admin_ids=parse_admin_ids(os.getenv('ADMIN_IDS', '')),
            bot_username=os.getenv('BOT_USERNAME', '').strip().lstrip('@'),
            database_url=database_url,
            redis_url=redis_url,
            webhook_base_url=(os.getenv('WEBHOOK_BASE_URL', '').strip() or os.getenv('RENDER_EXTERNAL_URL', '').strip()),
            webhook_secret=os.getenv('WEBHOOK_SECRET', '').strip(),
            port=int(os.getenv('PORT', '10000')),
        )
