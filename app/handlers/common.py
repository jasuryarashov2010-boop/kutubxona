from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import admin_keyboard, user_keyboard
from app.repository import Repository
from app.services.subscription import check_membership, ensure_access
from app.texts import ADMIN_MENU, USER_MENU, main_home, subscription_text

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    await state.clear()
    if not await ensure_access(message, message.bot, repo, is_admin):
        return
    await message.answer(main_home(), reply_markup=user_keyboard(is_admin))


@router.message(Command('cancel'))
@router.message(F.text == USER_MENU['cancel'])
async def cancel(message: Message, state: FSMContext, is_admin: bool):
    await state.clear()
    await message.answer('↩️ Amal bekor qilindi.', reply_markup=admin_keyboard() if is_admin else user_keyboard(False))

@router.callback_query(F.data == 'sub:check')
async def subscription_check(call: CallbackQuery, repo: Repository, is_admin: bool):
    if is_admin:
        await call.message.answer('✅ Admin uchun majburiy obuna tekshiruvi o‘tkazilmaydi.')
        await call.answer()
        return
    ok = await check_membership(call.bot, call.from_user.id, repo)
    if ok is None:
        await call.answer('⚠️ Tekshirishda Telegram xatosi. Keyinroq qayta urinib ko‘ring.', show_alert=True)
        return
    if ok:
        await call.message.answer(main_home(), reply_markup=user_keyboard(False))
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await call.answer('✅ Obuna tasdiqlandi!')
    else:
        await call.answer('❌ Hali obuna bo‘lmagansiz.', show_alert=True)
