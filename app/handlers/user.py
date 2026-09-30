from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.keyboards import cancel_keyboard, recommendation_edit_keyboard, recommendation_preview_keyboard, user_keyboard
from app.models import RecommendationStatus
from app.repository import Repository
from app.services.formatting import render_recommendation
from app.services.subscription import ensure_access
from app.services.utils import normalize_key, safe_html, status_label
from app.states import RecommendationFlow, SupportFlow
from app.texts import USER_MENU, rules_text

router = Router()


async def delete_prompt(bot, chat_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    prompt_id = data.get('prompt_id')
    if prompt_id:
        try:
            await bot.delete_message(chat_id, prompt_id)
        except Exception:
            pass


async def ask(message: Message, state: FSMContext, text: str, is_admin: bool, photo_step: bool = False) -> Message:
    await delete_prompt(message.bot, message.chat.id, state)
    sent = await message.answer(text, reply_markup=cancel_keyboard(is_admin, photo_step=photo_step), parse_mode=ParseMode.HTML)
    await state.update_data(prompt_id=sent.message_id)
    return sent


async def show_recommendation_preview(message: Message, state: FSMContext, is_admin: bool) -> None:
    data = await state.get_data()
    text = (
        '╭━━━━━━━━━━━━━━━━━━━━╮\n'
        '       👀 <b>OLDINDAN KO‘RISH</b>\n'
        '╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        + render_recommendation(data['title'], data['author'], data['review'])
    )
    if data.get('photo_file_id'):
        sent = await message.answer_photo(data['photo_file_id'], caption=text[:1024], parse_mode=ParseMode.HTML, reply_markup=recommendation_preview_keyboard())
    else:
        sent = await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=recommendation_preview_keyboard())
    old_preview = data.get('preview_id')
    if old_preview:
        try:
            await message.bot.delete_message(message.chat.id, old_preview)
        except Exception:
            pass
    await state.set_state(RecommendationFlow.preview)
    await state.update_data(preview_id=sent.message_id)


@router.message(F.text == USER_MENU['recommend'])
async def recommendation_start(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not await ensure_access(message, message.bot, repo, is_admin):
        return
    await state.clear()
    await state.set_state(RecommendationFlow.title)
    await ask(message, state, '📖 <b>Kitob nomini kiriting:</b>\n\nMasalan: <i>Ikki eshik orasi</i>', is_admin)


@router.message(RecommendationFlow.title, F.text)
async def recommendation_title(message: Message, state: FSMContext, is_admin: bool):
    value = message.text.strip()
    if not 2 <= len(value) <= 180:
        await ask(message, state, '⚠️ Kitob nomi 2–180 belgidan iborat bo‘lsin.\n\n📖 Qaytadan kiriting:', is_admin)
        return
    await state.update_data(title=value)
    await state.set_state(RecommendationFlow.author)
    await ask(message, state, '✍️ <b>Muallif nomini kiriting:</b>', is_admin)


@router.message(RecommendationFlow.author, F.text)
async def recommendation_author(message: Message, state: FSMContext, is_admin: bool):
    value = message.text.strip()
    if not 2 <= len(value) <= 140:
        await ask(message, state, '⚠️ Muallif nomi 2–140 belgidan iborat bo‘lsin.\n\n✍️ Qaytadan kiriting:', is_admin)
        return
    await state.update_data(author=value)
    await state.set_state(RecommendationFlow.review)
    await ask(message, state, '💭 <b>Kitob haqidagi fikringizni yozing:</b>\n\n📝 Nima uchun boshqalarga tavsiya qilasiz?', is_admin)


@router.message(RecommendationFlow.review, F.text)
async def recommendation_review(message: Message, state: FSMContext, is_admin: bool):
    value = message.text.strip()
    if not 20 <= len(value) <= 1500:
        await ask(message, state, '⚠️ Fikr 20–1500 belgi oralig‘ida bo‘lsin.\n\n💭 Qaytadan yozing:', is_admin)
        return
    await state.update_data(review=value)
    await state.set_state(RecommendationFlow.photo)
    await ask(message, state, '🖼 <b>Kitob rasmini yuboring.</b>\n\nRasm bo‘lmasa, pastdagi <b>⏭ Rasm yo‘q</b> tugmasini bosing.', is_admin, photo_step=True)


@router.message(RecommendationFlow.photo, F.photo)
async def recommendation_photo(message: Message, state: FSMContext, is_admin: bool):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await show_recommendation_preview(message, state, is_admin)


@router.message(RecommendationFlow.photo, F.text.casefold() == '⏭ rasm yo‘q')
async def recommendation_no_photo(message: Message, state: FSMContext, is_admin: bool):
    await state.update_data(photo_file_id=None)
    await show_recommendation_preview(message, state, is_admin)


@router.message(RecommendationFlow.photo, F.text)
async def recommendation_photo_invalid(message: Message, state: FSMContext, is_admin: bool):
    await ask(message, state, '🖼 Rasm yuboring yoki <b>⏭ Rasm yo‘q</b> deb yozing.', is_admin)


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:cancel')
async def recommendation_cancel_callback(call: CallbackQuery, state: FSMContext, is_admin: bool):
    data = await state.get_data()
    if data.get('preview_id'):
        try:
            await call.bot.delete_message(call.message.chat.id, int(data['preview_id']))
        except Exception:
            pass
    await state.clear()
    await call.message.answer('🗑 Tavsiya bekor qilindi.', reply_markup=user_keyboard(is_admin))
    await call.answer()


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:edit')
async def recommendation_edit_menu(call: CallbackQuery):
    await call.message.answer('✏️ <b>Qaysi qismini o‘zgartirmoqchisiz?</b>', parse_mode=ParseMode.HTML, reply_markup=recommendation_edit_keyboard())
    await call.answer()


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:edit:title')
async def edit_title_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(RecommendationFlow.edit_title)
    await call.message.answer('📖 Yangi kitob nomini kiriting:')
    await call.answer()


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:edit:author')
async def edit_author_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(RecommendationFlow.edit_author)
    await call.message.answer('✍️ Yangi muallif nomini kiriting:')
    await call.answer()


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:edit:review')
async def edit_review_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(RecommendationFlow.edit_review)
    await call.message.answer('💭 Yangi fikringizni kiriting:')
    await call.answer()


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:edit:photo')
async def edit_photo_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(RecommendationFlow.edit_photo)
    await call.message.answer('🖼 Yangi rasm yuboring yoki <b>⏭ Rasm yo‘q</b> deb yozing.', parse_mode=ParseMode.HTML)
    await call.answer()


async def rerender_preview(message: Message, state: FSMContext, is_admin: bool):
    await show_recommendation_preview(message, state, is_admin)


@router.message(RecommendationFlow.edit_title, F.text)
async def edit_title_finish(message: Message, state: FSMContext, is_admin: bool):
    value = message.text.strip()
    if not 2 <= len(value) <= 180:
        await message.answer('⚠️ Noto‘g‘ri uzunlik. 2–180 belgi.')
        return
    await state.update_data(title=value)
    await state.set_state(RecommendationFlow.preview)
    await rerender_preview(message, state, is_admin)


@router.message(RecommendationFlow.edit_author, F.text)
async def edit_author_finish(message: Message, state: FSMContext, is_admin: bool):
    value = message.text.strip()
    if not 2 <= len(value) <= 140:
        await message.answer('⚠️ Noto‘g‘ri uzunlik. 2–140 belgi.')
        return
    await state.update_data(author=value)
    await state.set_state(RecommendationFlow.preview)
    await rerender_preview(message, state, is_admin)


@router.message(RecommendationFlow.edit_review, F.text)
async def edit_review_finish(message: Message, state: FSMContext, is_admin: bool):
    value = message.text.strip()
    if not 20 <= len(value) <= 1500:
        await message.answer('⚠️ Fikr 20–1500 belgi bo‘lsin.')
        return
    await state.update_data(review=value)
    await state.set_state(RecommendationFlow.preview)
    await rerender_preview(message, state, is_admin)


@router.message(RecommendationFlow.edit_photo, F.photo)
async def edit_photo_finish(message: Message, state: FSMContext, is_admin: bool):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(RecommendationFlow.preview)
    await rerender_preview(message, state, is_admin)


@router.message(RecommendationFlow.edit_photo, F.text.casefold() == '⏭ rasm yo‘q')
async def remove_photo_finish(message: Message, state: FSMContext, is_admin: bool):
    await state.update_data(photo_file_id=None)
    await state.set_state(RecommendationFlow.preview)
    await rerender_preview(message, state, is_admin)


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:preview')
async def recommendation_preview_again(call: CallbackQuery, state: FSMContext, is_admin: bool):
    await show_recommendation_preview(call.message, state, is_admin)
    await call.answer()


@router.callback_query(RecommendationFlow.preview, F.data == 'rec:submit')
async def recommendation_submit(call: CallbackQuery, state: FSMContext, repo: Repository, is_admin: bool):
    data = await state.get_data()
    user = await repo.get_user_by_tg(call.from_user.id)
    if not user:
        await call.answer('Foydalanuvchi topilmadi.', show_alert=True)
        return
    key = normalize_key(data['title'], data['author'])
    duplicate = await repo.find_duplicate(key)
    rec = await repo.create_recommendation(user.id, data['title'], data['author'], data['review'], data.get('photo_file_id'), key, duplicate.id if duplicate else None)
    await state.clear()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    warning = '\n⚠️ <b>O‘xshash tavsiya mavjud:</b> #' + str(duplicate.id) if duplicate else ''
    await call.message.answer(
        f'╭━━━━━━━━━━━━━━━━━━━━╮\n      ✅ <b>TAVSIYA QABUL QILINDI</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'🆔 <b>#{rec.id}</b>\n'
        f'📖 {safe_html(rec.title)}\n'
        f'✍️ {safe_html(rec.author)}\n\n'
        f'🟡 Holati: <b>Ko‘rib chiqilmoqda</b>{warning}',
        parse_mode=ParseMode.HTML,
        reply_markup=user_keyboard(is_admin),
    )
    await call.answer('✅ Yuborildi!')


@router.message(F.text == USER_MENU['my'])
async def my_recommendations(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not await ensure_access(message, message.bot, repo, is_admin):
        return
    await state.clear()
    user = await repo.get_user_by_tg(message.from_user.id)
    rows = await repo.list_user_recommendations(user.id if user else 0)
    if not rows:
        await message.answer('📚 Hali tavsiya yubormagansiz.')
        return
    parts = ['╭━━━━━━━━━━━━━━━━━━━━╮', '      📚 <b>MENING TAVSIYALARIM</b>', '╰━━━━━━━━━━━━━━━━━━━━╯', '']
    for row in rows:
        parts.append(f'🆔 <b>#{row.id}</b>  •  {status_label(row.status)}')
        parts.append(f'📖 {safe_html(row.title)} — {safe_html(row.author)}')
        if row.status == RecommendationStatus.REJECTED.value and row.rejection_reason:
            parts.append(f'💬 Sabab: {safe_html(row.rejection_reason)}')
        parts.append('')
    await message.answer('\n'.join(parts), parse_mode=ParseMode.HTML)


@router.message(F.text == USER_MENU['rules'])
async def rules(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if await ensure_access(message, message.bot, repo, is_admin):
        await state.clear()
        await message.answer(rules_text(), parse_mode=ParseMode.HTML)


@router.message(F.text == USER_MENU['channel'])
async def channel_link(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not await ensure_access(message, message.bot, repo, is_admin):
        return
    await state.clear()
    url = await repo.get_setting('target_channel_url')
    if url:
        await message.answer(f'📢 <b>Kanalimiz</b>\n\n👉 {safe_html(url)}', parse_mode=ParseMode.HTML)
    else:
        await message.answer('📢 Kanal havolasi hali sozlanmagan.')


@router.message(F.text == USER_MENU['support'])
async def support_start(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not await ensure_access(message, message.bot, repo, is_admin):
        return
    if is_admin:
        await message.answer('ℹ️ Admin sifatida foydalanuvchi murojaatini `📨 Murojaatlar` bo‘limidan boshqarasiz.', parse_mode=ParseMode.MARKDOWN)
        return
    await state.set_state(SupportFlow.waiting_message)
    await ask(message, state, '💬 <b>Adminga xabaringizni yozing:</b>\n\n📌 Savol, taklif yoki muammoni batafsil yozishingiz mumkin.', False)


@router.message(SupportFlow.waiting_message, F.text)
async def support_finish(message: Message, state: FSMContext, repo: Repository, settings):
    text = message.text.strip()
    if len(text) < 2:
        await message.answer('⚠️ Xabar juda qisqa.')
        return
    user = await repo.get_user_by_tg(message.from_user.id)
    if not user:
        await state.clear()
        return
    ticket = await repo.create_support(user.id, text)
    await state.clear()
    await message.answer('✅ <b>Xabaringiz adminga yuborildi.</b>\n\n📨 Javob kelganda shu yerga yuboriladi.', parse_mode=ParseMode.HTML, reply_markup=user_keyboard(False))
    from app.keyboards import support_actions
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f'╭━━━━━━━━━━━━━━━━━━━━╮\n     📨 <b>YANGI MUROJAAT #{ticket.id}</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
                f'👤 <b>{safe_html(user.full_name)}</b> ' + (f'(@{safe_html(user.username)})' if user.username else '') + '\n'
                f'🆔 <code>{user.telegram_id}</code>\n\n'
                f'💬 {safe_html(text)}',
                parse_mode=ParseMode.HTML,
                reply_markup=support_actions(ticket.id),
            )
        except Exception:
            pass
