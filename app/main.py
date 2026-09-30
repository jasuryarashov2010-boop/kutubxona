from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Header, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import Settings
from app.db import init_db, make_engine, make_session_factory
from app.handlers import admin, channel, common, user
from app.middlewares import ContextMiddleware
from app.repository import Repository
from app.services.formatting import DEFAULT_FOOTER, DEFAULT_HEADER

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger('kitobxon')

settings = Settings.from_env()
engine = make_engine(settings.database_url)
session_factory = make_session_factory(engine)
repo = Repository(session_factory)
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
storage = RedisStorage(redis_client, state_ttl=60 * 60, data_ttl=60 * 60 * 2)
bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)
dp.include_router(channel.router)
dp.include_router(admin.router)
dp.include_router(common.router)
dp.include_router(user.router)
dp.update.outer_middleware(ContextMiddleware(repo, settings))


async def seed_defaults() -> None:
    defaults = {
        'force_subscription': 'true',
        'reaction_enabled': 'true',
        'reaction_emoji': '🔥',
        'design_header': DEFAULT_HEADER,
        'design_footer': DEFAULT_FOOTER,
        'design_show_recommender': 'false',
        'bot_username': settings.bot_username,
        'target_channel_id': '',
        'target_channel_url': '',
        'subscription_channel_id': '',
        'subscription_channel_url': '',
    }
    for key, value in defaults.items():
        if await repo.get_setting(key) is None:
            await repo.set_setting(key, value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(engine)
    await seed_defaults()
    await redis_client.ping()
    me = await bot.get_me()
    await bot.set_my_commands([
        BotCommand(command='start', description='Bosh menyu'),
        BotCommand(command='cancel', description='Joriy amalni bekor qilish'),
    ])
    logger.info('Bot authenticated as @%s (%s)', me.username, me.id)
    if settings.webhook_base_url:
        webhook = settings.webhook_base_url.rstrip('/') + '/telegram/webhook'
        await bot.set_webhook(webhook, secret_token=settings.webhook_secret or None, allowed_updates=dp.resolve_used_update_types())
        logger.info('Webhook: %s', webhook)
    else:
        global polling_task
        logger.info('Local mode: polling')
        await bot.delete_webhook(drop_pending_updates=False)
        polling_task = asyncio.create_task(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))
    try:
        yield
    finally:
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
        if settings.webhook_base_url:
            try:
                await bot.delete_webhook(drop_pending_updates=False)
            except Exception:
                logger.exception('Webhook cleanup failed')
        await storage.close()
        await redis_client.aclose()
        await bot.session.close()
        await engine.dispose()


polling_task: asyncio.Task | None = None


app = FastAPI(title='Kitobxon Tavsiya Bot', version='3.0.0', lifespan=lifespan)


@app.get('/')
async def root():
    return {'service': 'kitobxon', 'status': 'ok', 'version': '3.0.0'}


@app.get('/health')
async def health():
    try:
        await redis_client.ping()
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        return {'status': 'ok'}
    except Exception:
        raise HTTPException(status_code=503, detail='dependency unavailable')


@app.post('/telegram/webhook')
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail='forbidden')
    from aiogram.types import Update
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {'ok': True}
