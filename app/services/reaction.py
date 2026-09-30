from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import ReactionTypeEmoji

from app.repository import Repository

logger = logging.getLogger('kitobxon.reaction')


def normalize_reaction(value: str) -> str:
    return value.strip()


async def apply_reaction(bot: Bot, repo: Repository, chat_id: int, message_id: int) -> bool:
    enabled = (await repo.get_setting('reaction_enabled', 'true')) == 'true'
    emoji = normalize_reaction(await repo.get_setting('reaction_emoji', '🔥') or '🔥')
    if not enabled or not emoji:
        return False
    try:
        await bot.set_message_reaction(chat_id=chat_id, message_id=message_id, reaction=[ReactionTypeEmoji(emoji=emoji)])
        return True
    except Exception as exc:
        logger.warning('Reaction failed chat=%s message=%s: %s', chat_id, message_id, exc)
        return False
