from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import admin_keyboard, user_keyboard
from app.repository import Repository
from app.services.subscription import check_membership, ensure_access
from app.texts import USER_MENU, main_home

router = Router()


@router.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext,
    repo: Repository,
    is_admin: bool,
    db_user=None,
):
    await state.clear()

    if db_user is not None and db_user.is_blocked and not is_admin:
        await message.answer(
            "🚫 <b>Foydalanish cheklangan</b>\n\n"
            "Sizning botdan foydalanish huquqingiz admin tomonidan "
            "vaqtincha cheklangan.",
            reply_markup=user_keyboard(False),
        )
        return

    # Admin uchun majburiy obuna tekshirilmaydi
    if not is_admin:
        access = await ensure_access(
            message,
            message.bot,
            repo,
            is_admin=False,
        )
        if not access:
            return

    await message.answer(
        main_home(),
        reply_markup=admin_keyboard() if is_admin else user_keyboard(False),
    )


@router.message(F.text == USER_MENU["cancel"])
@router.message(Command("cancel"))
async def cancel(
    message: Message,
    state: FSMContext,
    is_admin: bool,
):
    await state.clear()

    if is_admin:
        await message.answer(
            "↩️ Amal bekor qilindi.",
            reply_markup=admin_keyboard(),
        )
    else:
        await message.answer(
            "↩️ Amal bekor qilindi.",
            reply_markup=user_keyboard(False),
        )


@router.callback_query(F.data == "sub:check")
async def subscription_check(
    call: CallbackQuery,
    repo: Repository,
    is_admin: bool,
):
    if is_admin:
        await call.answer("✅ Admin uchun obuna tekshirilmaydi.")
        await call.message.answer(
            main_home(),
            reply_markup=admin_keyboard(),
        )
        return

    ok = await check_membership(
        call.bot,
        call.from_user.id,
        repo,
    )

    if ok is None:
        await call.answer(
            "⚠️ Obunani tekshirishda xatolik yuz berdi.",
            show_alert=True,
        )
        return

    if ok:
        await call.answer("✅ Obuna tasdiqlandi!")
        await call.message.answer(
            main_home(),
            reply_markup=user_keyboard(False),
        )
        try:
            await call.message.delete()
        except Exception:
            pass
    else:
        await call.answer(
            "❌ Avval kanalga obuna bo‘ling.",
            show_alert=True,
        )
