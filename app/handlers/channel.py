from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

from app.repository import Repository
from app.services.reaction import apply_reaction

router = Router()
logger = logging.getLogger('kitobxon.channel')


@router.channel_post()
async def channel_post(message: Message, repo: Repository):
    target = await repo.get_setting('target_channel_id')
    if not target:
        return
    try:
        if int(target) != int(message.chat.id):
            return
    except (TypeError, ValueError):
        return
    await apply_reaction(message.bot, repo, message.chat.id, message.message_id)
