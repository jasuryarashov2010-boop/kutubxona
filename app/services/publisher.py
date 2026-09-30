from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ParseMode

from app.models import Recommendation, User
from app.repository import Repository
from app.services.formatting import DEFAULT_FOOTER, DEFAULT_HEADER, render_channel_post


async def get_design(repo: Repository) -> dict[str, str]:
    settings = await repo.settings()
    return {
        'header': settings.get('design_header', DEFAULT_HEADER),
        'footer': settings.get('design_footer', DEFAULT_FOOTER),
        'show_recommender': settings.get('design_show_recommender', 'false'),
    }


async def publish_recommendation(bot: Bot, repo: Repository, recommendation: Recommendation, user: User) -> int:
    target_raw = await repo.get_setting('target_channel_id')
    if not target_raw:
        raise RuntimeError('Post kanali hali sozlanmagan')
    target_id = int(target_raw)
    design = await get_design(repo)
    recommender = f'@{user.username}' if user.username else user.full_name
    caption = render_channel_post(
        recommendation.title,
        recommendation.author,
        recommendation.review,
        design['header'],
        design['footer'],
        (await repo.get_setting('bot_username') or ''),
        design['show_recommender'] == 'true',
        recommender,
    )
    if recommendation.photo_file_id:
        if len(caption) > 1024:
            caption = caption[:1000].rstrip() + '…'
        sent = await bot.send_photo(target_id, recommendation.photo_file_id, caption=caption, parse_mode=ParseMode.HTML)
    else:
        sent = await bot.send_message(target_id, caption, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    return sent.message_id
