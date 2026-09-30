from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware

from app.config import Settings
from app.repository import Repository


class ContextMiddleware(BaseMiddleware):
    def __init__(self, repo: Repository, settings: Settings):
        self.repo = repo
        self.settings = settings

    async def __call__(self, handler: Callable[[Any, dict[str, Any]], Awaitable[Any]], event: Any, data: dict[str, Any]) -> Any:
        data['repo'] = self.repo
        data['settings'] = self.settings
        tg_user = getattr(event, 'from_user', None)
        is_admin = bool(tg_user and tg_user.id in self.settings.admin_ids)
        data['is_admin'] = is_admin
        if tg_user and getattr(event, 'chat', None) and getattr(event.chat, 'type', None) == 'private':
            db_user = await self.repo.upsert_user(tg_user.id, tg_user.username, tg_user.full_name)
            data['db_user'] = db_user
            if db_user.is_blocked and not is_admin:
                if hasattr(event, 'answer'):
                    try:
                        await event.answer('🚫 Sizning botdan foydalanish huquqingiz vaqtincha cheklangan.')
                    except Exception:
                        pass
                return None
        return await handler(event, data)
