from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.keyboards import subscribe_keyboard
from app.repository import Repository
from app.texts import subscription_text


async def check_membership(bot: Bot, user_id: int, repo: Repository) -> bool | None:
    force = (await repo.get_setting('force_subscription', 'true')) == 'true'
    channel_id = await repo.get_setting('subscription_channel_id')
    if not force or not channel_id:
        return True
    try:
        member = await bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return None
    if member.status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
        return True
    if member.status == ChatMemberStatus.RESTRICTED and getattr(member, 'is_member', False):
        return True
    return False


async def ensure_access(message, bot: Bot, repo: Repository, is_admin: bool) -> bool:
    if is_admin:
        return True
    result = await check_membership(bot, message.from_user.id, repo)
    if result is True:
        return True
    channel_url = await repo.get_setting('subscription_channel_url')
    if result is None:
        await message.answer('⚠️ Obuna holatini tekshirishda Telegram xatosi yuz berdi. Kanal sozlamalari to‘g‘ri ekanini tekshiring va qayta urinib ko‘ring.')
        return False
    if not channel_url:
        await message.answer('⚠️ Obuna kanali hali sozlanmagan.')
        return False
    await message.answer(subscription_text(), reply_markup=subscribe_keyboard(channel_url))
    return False
