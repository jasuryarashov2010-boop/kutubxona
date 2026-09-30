from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import Settings
from app.keyboards import admin_edit_fields, admin_keyboard, admin_recommendation_actions, design_settings_keyboard, reaction_settings_keyboard, sub_settings_keyboard, support_actions, user_keyboard, user_result_actions, broadcast_confirm
from app.models import RecommendationStatus, TicketStatus
from app.repository import Repository
from app.services.formatting import DEFAULT_FOOTER, DEFAULT_HEADER, render_channel_post, render_recommendation
from app.services.publisher import get_design, publish_recommendation
from app.services.utils import normalize_key, safe_html, status_label
from app.states import AdminEditFlow, BroadcastFlow, ChannelFlow, DesignFlow, ReactionFlow, RejectFlow, SupportReplyFlow, UserSearchFlow
from app.texts import ADMIN_MENU, USER_MENU, admin_home

router = Router()


def denied(call: CallbackQuery):
    return call.answer('🚫 Ruxsat yo‘q.', show_alert=True)


@router.message(F.text == USER_MENU['admin'])
async def admin_panel(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    await message.answer(admin_home(), parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())


@router.message(F.text == ADMIN_MENU['home'])
async def admin_home_back(message: Message, is_admin: bool):
    if is_admin:
        await message.answer('🏠 Bosh menyu', reply_markup=user_keyboard(True))


@router.message(F.text == ADMIN_MENU['pending'])
async def pending_list(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    stale = await repo.reset_stale_publishing()
    rows = await repo.pending_with_users(20)
    header = f'📥 <b>TAKLIFLAR</b>\n\n🟡 Navbatda: <b>{len(rows)}</b>'
    if stale:
        header += f'\n🧹 Qaytarildi: <b>{stale}</b>'
    await message.answer(header, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
    if not rows:
        await message.answer('✨ Hozircha yangi tavsiya yo‘q.', reply_markup=admin_keyboard())
        return
    for rec, user in rows:
        duplicate_note = f'\n⚠️ <b>O‘xshash tavsiya:</b> #{rec.duplicate_of_id}' if rec.duplicate_of_id else ''
        text = (
            f'╭━━━━━━━━━━━━━━━━━━━━╮\n'
            f'      📥 <b>YANGI TAVSIYA #{rec.id}</b>\n'
            f'╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
            f'📖 <b>{safe_html(rec.title)}</b>\n'
            f'✍️ {safe_html(rec.author)}\n\n'
            f'💭 <b>Fikr:</b>\n<blockquote>{safe_html(rec.review[:800])}</blockquote>\n'
            f'👤 {safe_html(user.full_name)}' + (f'  •  @{safe_html(user.username)}' if user.username else '') +
            f'\n🆔 <code>{user.telegram_id}</code>{duplicate_note}'
        )
        kb = admin_recommendation_actions(rec.id)
        try:
            if rec.photo_file_id:
                await message.answer_photo(rec.photo_file_id, caption=text[:1024], parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data.startswith('admin:preview:'))
async def admin_preview(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    rec_id = int(call.data.rsplit(':', 1)[1])
    rec = await repo.get_recommendation(rec_id)
    if not rec or not rec.user:
        await call.answer('Tavsiya topilmadi.', show_alert=True)
        return
    design = await get_design(repo)
    recommender = f'@{rec.user.username}' if rec.user.username else rec.user.full_name
    text = render_channel_post(rec.title, rec.author, rec.review, design['header'], design['footer'], await repo.get_setting('bot_username', '') or '', design['show_recommender'] == 'true', recommender)
    if rec.photo_file_id:
        if len(text) > 1024:
            text = text[:1000].rstrip() + '…'
        await call.message.answer_photo(rec.photo_file_id, caption=text, parse_mode=ParseMode.HTML)
    else:
        await call.message.answer(text, parse_mode=ParseMode.HTML)
    await call.answer('👀 Preview')


@router.callback_query(F.data.startswith('admin:publish:'))
async def admin_publish(call: CallbackQuery, repo: Repository, settings: Settings, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    rec_id = int(call.data.rsplit(':', 1)[1])
    if not await repo.get_setting('target_channel_id'):
        await call.answer('📢 Avval post kanalini sozlang.', show_alert=True)
        return
    if not await repo.claim_publish(rec_id):
        await call.answer('⚠️ Bu tavsiya allaqachon qayta ishlangan.', show_alert=True)
        return
    rec = await repo.get_recommendation(rec_id)
    if not rec or not rec.user:
        await repo.release_publish(rec_id)
        await call.answer('Tavsiya topilmadi.', show_alert=True)
        return
    try:
        msg_id = await publish_recommendation(call.bot, repo, rec, rec.user)
        await repo.mark_published(rec_id, msg_id)
        await repo.audit(call.from_user.id, 'recommendation_published', 'recommendation', rec_id)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await call.answer('✅ Kanalga joylandi!', show_alert=False)
        try:
            await call.bot.send_message(rec.user.telegram_id, f'🟢 <b>#{rec_id}</b> tavsiyangiz kanalga joylandi.\n\n📖 {safe_html(rec.title)}', parse_mode=ParseMode.HTML)
        except Exception:
            pass
    except Exception as exc:
        await repo.release_publish(rec_id)
        await call.answer('❌ Joylashda xatolik. Kanal sozlamalarini tekshiring.', show_alert=True)
        try:
            await call.bot.send_message(call.from_user.id, f'⚠️ <code>{safe_html(str(exc)[:700])}</code>', parse_mode=ParseMode.HTML)
        except Exception:
            pass


@router.callback_query(F.data.regexp(r'^admin:reject:\d+$'))
async def admin_reject_start(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    if call.data.endswith(':cancel'):
        return
    rec_id = int(call.data.rsplit(':', 1)[1])
    await state.set_state(RejectFlow.waiting_reason)
    await state.update_data(rec_id=rec_id)
    await call.message.answer('❌ <b>Rad etish sababini yozing:</b>\n\nMasalan: kitob ma’lumoti yetarli emas.', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
    await call.answer()


@router.message(RejectFlow.waiting_reason, F.text)
async def admin_reject_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    reason = message.text.strip()
    if len(reason) < 3:
        await message.answer('⚠️ Sababni biroz aniqroq yozing.', reply_markup=admin_keyboard())
        return
    data = await state.get_data()
    rec_id = int(data['rec_id'])
    rec = await repo.get_recommendation(rec_id)
    ok = await repo.reject(rec_id, reason)
    await state.clear()
    if not ok or not rec or not rec.user:
        await message.answer('⚠️ Bu tavsiya allaqachon qayta ishlangan.', reply_markup=admin_keyboard())
        return
    await repo.audit(message.from_user.id, 'recommendation_rejected', 'recommendation', rec_id, reason)
    try:
        await message.bot.send_message(rec.user.telegram_id, f'🔴 <b>#{rec_id} tavsiyangiz rad etildi.</b>\n\n💬 Sabab: {safe_html(reason)}', parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await message.answer('✅ Tavsiya rad etildi.', reply_markup=admin_keyboard())


@router.callback_query(F.data == 'admin:reject:cancel')
async def admin_reject_cancel(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if is_admin:
        await state.clear()
        await call.message.answer('↩️ Bekor qilindi.', reply_markup=admin_keyboard())
        await call.answer()


@router.callback_query(F.data.startswith('admin:edit:'))
async def admin_edit_start(call: CallbackQuery, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    rec_id = int(call.data.rsplit(':', 1)[1])
    await call.message.answer('✏️ <b>O‘zgartirmoqchi bo‘lgan qismni tanlang.</b>', parse_mode=ParseMode.HTML, reply_markup=admin_edit_fields(rec_id))
    await call.answer()


@router.callback_query(F.data.startswith('adminedit:'))
async def admin_edit_choose(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    _, field, rec_id_raw = call.data.split(':')
    rec_id = int(rec_id_raw)
    labels = {'title': ('📖', 'Yangi kitob nomini yozing:', AdminEditFlow.title), 'author': ('✍️', 'Yangi muallif nomini yozing:', AdminEditFlow.author), 'review': ('💭', 'Yangi fikrni yozing:', AdminEditFlow.review)}
    _, prompt, state_value = labels[field]
    await state.set_state(state_value)
    await state.update_data(rec_id=rec_id, field=field)
    await call.message.answer(prompt, reply_markup=admin_keyboard())
    await call.answer()


async def complete_admin_edit(message: Message, state: FSMContext, repo: Repository):
    data = await state.get_data()
    rec_id = int(data['rec_id'])
    field = data['field']
    value = message.text.strip()
    if field == 'title' and not 2 <= len(value) <= 180:
        await message.answer('⚠️ Kitob nomi 2–180 belgi.')
        return
    if field == 'author' and not 2 <= len(value) <= 140:
        await message.answer('⚠️ Muallif 2–140 belgi.')
        return
    if field == 'review' and not 20 <= len(value) <= 1500:
        await message.answer('⚠️ Fikr 20–1500 belgi.')
        return
    current = await repo.get_recommendation(rec_id)
    if not current:
        await state.clear()
        await message.answer('⚠️ Tavsiya topilmadi.', reply_markup=admin_keyboard())
        return
    fields = {'title': value, 'author': value, 'review': value}
    await repo.edit_recommendation(rec_id, **{field: fields[field]})
    await repo.audit(message.from_user.id, 'recommendation_edited', 'recommendation', rec_id, field)
    await state.clear()
    await message.answer('✅ O‘zgarish saqlandi.', reply_markup=admin_keyboard())


@router.message(AdminEditFlow.title, F.text)
@router.message(AdminEditFlow.author, F.text)
@router.message(AdminEditFlow.review, F.text)
async def admin_edit_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if is_admin:
        await complete_admin_edit(message, state, repo)


@router.message(F.text == ADMIN_MENU['support'])
async def support_list(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    tickets = await repo.open_support_tickets(20)
    await message.answer(f'📨 <b>OCHIQ MUROJAATLAR: {len(tickets)}</b>', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
    if not tickets:
        await message.answer('✨ Hozircha yangi murojaat yo‘q.')
        return
    for ticket in tickets:
        user = ticket.user
        text = (
            f'📨 <b>Murojaat #{ticket.id}</b>\n\n'
            f'👤 {safe_html(user.full_name)}' + (f'  •  @{safe_html(user.username)}' if user.username else '') +
            f'\n🆔 <code>{user.telegram_id}</code>\n\n'
            f'💬 {safe_html(ticket.message_text[:1500])}'
        )
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=support_actions(ticket.id))


@router.callback_query(F.data.startswith('support:reply:'))
async def support_reply_start(call: CallbackQuery, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    ticket_id = int(call.data.rsplit(':', 1)[1])
    if not await repo.claim_support(ticket_id):
        await call.answer('⚠️ Bu murojaat boshqa admin tomonidan olinmoqda yoki yopilgan.', show_alert=True)
        return
    await state.set_state(SupportReplyFlow.waiting_message)
    await state.update_data(ticket_id=ticket_id)
    await call.message.answer(f'↩️ <b>#{ticket_id}</b> uchun javobni yozing:', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
    await call.answer()


@router.message(SupportReplyFlow.waiting_message, F.text)
async def support_reply_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    text = message.text.strip()
    data = await state.get_data()
    ticket_id = int(data['ticket_id'])
    ticket = await repo.get_support(ticket_id)
    if not ticket or not ticket.user:
        await state.clear()
        await message.answer('⚠️ Murojaat topilmadi.', reply_markup=admin_keyboard())
        return
    await repo.close_support(ticket_id, message.from_user.id, text)
    await repo.audit(message.from_user.id, 'support_replied', 'ticket', ticket_id)
    await state.clear()
    try:
        await message.bot.send_message(ticket.user.telegram_id, f'📨 <b>Admin javobi</b>\n\n{safe_html(text)}', parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await message.answer('✅ Javob yuborildi.', reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith('support:close:'))
async def support_close(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    ticket_id = int(call.data.rsplit(':', 1)[1])
    await repo.close_support(ticket_id, call.from_user.id)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer('✅ Murojaat yopildi.')


@router.message(F.text == ADMIN_MENU['broadcast'])
async def broadcast_start(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await state.set_state(BroadcastFlow.waiting_text)
    await message.answer('📣 <b>Barchaga yuboriladigan xabarni yozing:</b>\n\n⚠️ Xabar yuborilishidan oldin sizga preview ko‘rsatiladi.', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())


@router.message(BroadcastFlow.waiting_text, F.text)
async def broadcast_preview(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    text = message.text.strip()
    if len(text) < 2:
        await message.answer('⚠️ Xabar juda qisqa.')
        return
    await state.update_data(text=text)
    await message.answer(
        '╭━━━━━━━━━━━━━━━━━━━━╮\n      👀 <b>XABAR PREVIEW</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n' + safe_html(text),
        parse_mode=ParseMode.HTML,
        reply_markup=broadcast_confirm(),
    )


@router.callback_query(F.data == 'broadcast:cancel')
async def broadcast_cancel(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if is_admin:
        await state.clear()
        await call.message.answer('↩️ Broadcast bekor qilindi.', reply_markup=admin_keyboard())
        await call.answer()


@router.callback_query(F.data == 'broadcast:send')
async def broadcast_send(call: CallbackQuery, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    data = await state.get_data()
    text = data.get('text', '').strip()
    await state.clear()
    if not text:
        await call.answer('Xabar topilmadi.', show_alert=True)
        return
    user_ids = await repo.all_user_ids()
    sent = failed = 0
    status_msg = await call.message.answer(f'📣 Yuborish boshlandi…\n\n👥 Jami: <b>{len(user_ids)}</b>', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
    for user_id in user_ids:
        try:
            await call.bot.send_message(user_id, safe_html(text), parse_mode=ParseMode.HTML)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await call.bot.send_message(user_id, safe_html(text), parse_mode=ParseMode.HTML)
                sent += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await repo.audit(call.from_user.id, 'broadcast_sent', details=f'sent={sent},failed={failed}')
    try:
        await status_msg.edit_text(f'📣 <b>Broadcast yakunlandi</b>\n\n✅ Yetkazildi: <b>{sent}</b>\n❌ Xatolik: <b>{failed}</b>', parse_mode=ParseMode.HTML)
    except Exception:
        await call.message.answer(f'📣 Yakunlandi: ✅ {sent} / ❌ {failed}')
    await call.answer('✅ Tugadi')


@router.message(F.text == ADMIN_MENU['reaction'])
async def reaction_menu(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    enabled = (await repo.get_setting('reaction_enabled', 'true')) == 'true'
    emoji = await repo.get_setting('reaction_emoji', '🔥') or '🔥'
    await message.answer(
        f'╭━━━━━━━━━━━━━━━━━━━━╮\n      🔥 <b>REAKSIYA</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'Holat: <b>{"✅ Yoqilgan" if enabled else "❌ O‘chirilgan"}</b>\n'
        f'Emoji: <b>{safe_html(emoji)}</b>\n\n'
        '📌 Bot target kanaldagi yangi postlarga shu reactionni qo‘yadi.',
        parse_mode=ParseMode.HTML,
        reply_markup=reaction_settings_keyboard(enabled),
    )


@router.callback_query(F.data == 'reaction:set')
async def reaction_set(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    await state.set_state(ReactionFlow.waiting_emoji)
    await call.message.answer('✍️ <b>Bitta emoji yuboring.</b>\n\nMasalan: 🔥 yoki ❤️', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
    await call.answer()


@router.message(ReactionFlow.waiting_emoji, F.text)
async def reaction_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    value = message.text.strip()
    aliases = {'❤️': '❤', '♥️': '♥'}
    value = aliases.get(value, value)
    allowed = {
        '❤','👍','👎','🔥','🥰','👏','😁','🤔','🤯','😱','🤬','😢','🎉','🤩','🤮','💩','🙏','👌','🕊','🤡','🥱','🥴','😍','🐳','🌚','🌭','💯','🤣','⚡','🍌','🏆','💔','🤨','😐','🍓','🍾','💋','🖕','😈','😴','😭','🤓','👻','👨‍💻','👀','🎃','🙈','😇','😨','🤝','✍','🤗','🫡','🎅','🎄','☃','💅','🤪','🗿','🆒','💘','🙉','🦄','😘','💊','🙊','😎','👾','🤷‍♂','🤷','🤷‍♀','😡','❤‍🔥'
    }
    if value not in allowed:
        await message.answer('⚠️ Telegram botlari uchun ruxsat etilgan oddiy reaction emoji yuboring. Masalan: 🔥, ❤, 👍, 👏')
        return
    await repo.set_setting('reaction_emoji', value)
    await repo.set_setting('reaction_enabled', 'true')
    await repo.audit(message.from_user.id, 'reaction_changed', details=value)
    await state.clear()
    await message.answer(f'✅ Yangi reaction: {safe_html(value)}', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())


@router.callback_query(F.data == 'reaction:toggle')
async def reaction_toggle(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    enabled = (await repo.get_setting('reaction_enabled', 'true')) == 'true'
    await repo.set_setting('reaction_enabled', 'false' if enabled else 'true')
    await call.message.edit_reply_markup(reply_markup=reaction_settings_keyboard(not enabled))
    await call.answer('✅ Sozlama saqlandi.')


@router.message(F.text == ADMIN_MENU['design'])
async def design_menu(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    design = await get_design(repo)
    await message.answer(
        '╭━━━━━━━━━━━━━━━━━━━━╮\n      🎨 <b>POST DIZAYNI</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'📝 Sarlavha: <code>{safe_html(design["header"][:180])}</code>\n'
        f'🔚 Pastki matn: <code>{safe_html(design["footer"][:180])}</code>',
        parse_mode=ParseMode.HTML,
        reply_markup=design_settings_keyboard(),
    )


@router.callback_query(F.data == 'design:header')
async def design_header_start(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    await state.set_state(DesignFlow.waiting_header)
    await call.message.answer('📝 Yangi sarlavhani oddiy matn ko‘rinishida yuboring. Emoji ishlatishingiz mumkin.', reply_markup=admin_keyboard())
    await call.answer()


@router.message(DesignFlow.waiting_header, F.text)
async def design_header_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    value = message.text.strip()
    if not value:
        return
    await repo.set_setting('design_header', safe_html(value))
    await repo.audit(message.from_user.id, 'design_header_changed')
    await state.clear()
    await message.answer('✅ Sarlavha saqlandi.', reply_markup=admin_keyboard())


@router.callback_query(F.data == 'design:footer')
async def design_footer_start(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    await state.set_state(DesignFlow.waiting_footer)
    await call.message.answer('🔚 Pastki matnni yuboring. `{bot}` yozsangiz bot username o‘rniga qo‘yiladi.', parse_mode=ParseMode.MARKDOWN, reply_markup=admin_keyboard())
    await call.answer()


@router.message(DesignFlow.waiting_footer, F.text)
async def design_footer_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    await repo.set_setting('design_footer', safe_html(message.text.strip()))
    await repo.audit(message.from_user.id, 'design_footer_changed')
    await state.clear()
    await message.answer('✅ Pastki matn saqlandi.', reply_markup=admin_keyboard())


@router.callback_query(F.data == 'design:preview')
async def design_preview(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    design = await get_design(repo)
    text = render_channel_post('Ikki eshik orasi', 'O‘tkir Hoshimov', 'Inson hayoti, tanlovlari va taqdir haqida o‘ylashga undaydigan ta’sirli asar.', design['header'], design['footer'], await repo.get_setting('bot_username', '') or '', False, None)
    await call.message.answer(text, parse_mode=ParseMode.HTML)
    await call.answer()


@router.callback_query(F.data == 'design:reset')
async def design_reset(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    await repo.set_setting('design_header', DEFAULT_HEADER)
    await repo.set_setting('design_footer', DEFAULT_FOOTER)
    await repo.set_setting('design_show_recommender', 'false')
    await call.answer('♻️ Standart dizayn tiklandi.', show_alert=True)


@router.message(F.text == ADMIN_MENU['channel'])
async def channel_settings(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    settings = await repo.settings()
    force = settings.get('force_subscription', 'true') == 'true'
    target = settings.get('target_channel_id', '—')
    sub = settings.get('subscription_channel_id', '—')
    await message.answer(
        f'╭━━━━━━━━━━━━━━━━━━━━╮\n      📢 <b>KANAL SOZLAMALARI</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'🎯 Post kanali: <code>{safe_html(target)}</code>\n'
        f'🔐 Obuna kanali: <code>{safe_html(sub)}</code>\n'
        f'🔒 Majburiy obuna: <b>{"✅ ON" if force else "❌ OFF"}</b>\n\n'
        '📌 ID maydoni uchun `-100...` formatidan foydalaning.',
        parse_mode=ParseMode.HTML,
        reply_markup=sub_settings_keyboard(force),
    )


@router.callback_query(F.data.startswith('channel:set:'))
async def channel_set_start(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    field = call.data.rsplit(':', 1)[1]
    mapping = {
        'target_id': (ChannelFlow.waiting_target_id, '🎯 Post kanali ID sini yuboring. Masalan: `-1001234567890`'),
        'target_url': (ChannelFlow.waiting_target_url, '🔗 Post kanal havolasini yuboring. Masalan: `https://t.me/...`'),
        'sub_id': (ChannelFlow.waiting_sub_id, '🔐 Majburiy obuna kanalining ID sini yuboring. Masalan: `-1001234567890`'),
        'sub_url': (ChannelFlow.waiting_sub_url, '🔗 Majburiy obuna kanalining havolasini yuboring.'),
    }
    state_value, prompt = mapping[field]
    await state.set_state(state_value)
    await state.update_data(channel_field=field)
    await call.message.answer(prompt, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_keyboard())
    await call.answer()


@router.message(ChannelFlow.waiting_target_id, F.text)
@router.message(ChannelFlow.waiting_sub_id, F.text)
async def channel_id_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    raw = message.text.strip()
    try:
        int(raw)
    except ValueError:
        await message.answer('⚠️ ID noto‘g‘ri. `-100...` formatida yuboring.', parse_mode=ParseMode.MARKDOWN)
        return
    current = await state.get_state()
    key = 'target_channel_id' if current == ChannelFlow.waiting_target_id.state else 'subscription_channel_id'
    await repo.set_setting(key, raw)
    await state.clear()
    await repo.audit(message.from_user.id, 'channel_setting_changed', details=key)
    await message.answer('✅ Saqlandi.', reply_markup=admin_keyboard())


@router.message(ChannelFlow.waiting_target_url, F.text)
@router.message(ChannelFlow.waiting_sub_url, F.text)
async def channel_url_finish(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    value = message.text.strip()
    if not value.startswith('https://t.me/'):
        await message.answer('⚠️ Havola `https://t.me/...` ko‘rinishida bo‘lsin.')
        return
    current = await state.get_state()
    key = 'target_channel_url' if current == ChannelFlow.waiting_target_url.state else 'subscription_channel_url'
    await repo.set_setting(key, value)
    await state.clear()
    await repo.audit(message.from_user.id, 'channel_setting_changed', details=key)
    await message.answer('✅ Saqlandi.', reply_markup=admin_keyboard())


@router.callback_query(F.data == 'channel:toggle:sub')
async def channel_toggle_subscription(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    force = (await repo.get_setting('force_subscription', 'true')) == 'true'
    new_value = not force
    await repo.set_setting('force_subscription', 'true' if new_value else 'false')
    await call.message.edit_reply_markup(reply_markup=sub_settings_keyboard(new_value))
    await call.answer('✅ Sozlama saqlandi.')


@router.callback_query(F.data == 'channel:reset')
async def channel_reset(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    for key in ('target_channel_id', 'target_channel_url', 'subscription_channel_id', 'subscription_channel_url'):
        await repo.set_setting(key, '')
    await repo.set_setting('force_subscription', 'true')
    await call.answer('♻️ Kanal sozlamalari tozalandi.', show_alert=True)


@router.callback_query(F.data == 'channel:test')
async def channel_test(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    target = await repo.get_setting('target_channel_id')
    sub = await repo.get_setting('subscription_channel_id')
    missing = []
    if not target:
        missing.append('🎯 Post kanali ID')
    if (await repo.get_setting('force_subscription', 'true')) == 'true' and not sub:
        missing.append('🔐 Obuna kanali ID')
    if missing:
        await call.answer('⚠️ Yetishmayapti: ' + ', '.join(missing), show_alert=True)
        return
    try:
        chat = await call.bot.get_chat(int(target))
        await call.message.answer(f'✅ Post kanali topildi: <b>{safe_html(chat.title or str(chat.id))}</b>', parse_mode=ParseMode.HTML)
        if sub:
            subchat = await call.bot.get_chat(int(sub))
            await call.message.answer(f'✅ Obuna kanali topildi: <b>{safe_html(subchat.title or str(subchat.id))}</b>', parse_mode=ParseMode.HTML)
    except Exception as exc:
        await call.message.answer(f'❌ Kanal tekshiruvi xato berdi:\n<code>{safe_html(str(exc)[:700])}</code>', parse_mode=ParseMode.HTML)
    await call.answer()


@router.message(F.text == ADMIN_MENU['users'])
async def users_start(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    await state.set_state(UserSearchFlow.waiting_query)
    await message.answer('🔎 <b>Foydalanuvchini qidiring:</b>\n\nID, @username yoki ism yuboring.', parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())


@router.message(UserSearchFlow.waiting_query, F.text)
async def users_search(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    query = message.text.strip()
    rows = await repo.search_users(query)
    if not rows:
        await message.answer('🔎 Hech narsa topilmadi.')
        return
    await state.clear()
    for user in rows:
        text = f'👤 <b>{safe_html(user.full_name)}</b>\n🆔 <code>{user.telegram_id}</code>\n'
        if user.username:
            text += f'🔗 @{safe_html(user.username)}\n'
        text += f'Holat: {"🚫 Bloklangan" if user.is_blocked else "✅ Faol"}'
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=user_result_actions(user.id, user.is_blocked))
    await message.answer('👥 Boshqaruv menyusiga qaytdingiz.', reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith('user:block:'))
@router.callback_query(F.data.startswith('user:unblock:'))
async def user_block_toggle(call: CallbackQuery, repo: Repository, is_admin: bool):
    if not is_admin:
        await denied(call)
        return
    action, user_id_raw = call.data.split(':')[1:]
    user_id = int(user_id_raw)
    blocked = action == 'block'
    await repo.set_blocked(user_id, blocked)
    await repo.audit(call.from_user.id, 'user_block_toggle', 'user', user_id, str(blocked))
    await call.answer('✅ Holat o‘zgartirildi.')
    try:
        user = await repo.get_user_by_id(user_id)
        if user:
            await call.message.edit_reply_markup(reply_markup=user_result_actions(user.id, user.is_blocked))
    except Exception:
        pass


@router.message(F.text == ADMIN_MENU['stats'])
async def stats(message: Message, state: FSMContext, repo: Repository, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    s = await repo.stats()
    text = (
        '╭━━━━━━━━━━━━━━━━━━━━╮\n'
        '        📊 <b>STATISTIKA</b>\n'
        '╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'👥 Foydalanuvchilar: <b>{s["users"]}</b>\n'
        f'📚 Jami tavsiyalar: <b>{s["recommendations"]}</b>\n'
        f'🟡 Kutilmoqda: <b>{s["pending"]}</b>\n'
        f'🟢 Joylangan: <b>{s["published"]}</b>\n'
        f'🔴 Rad etilgan: <b>{s["rejected"]}</b>\n'
        f'📨 Ochiq murojaatlar: <b>{s["open_support"]}</b>\n'
        f'🚫 Bloklangan: <b>{s["blocked"]}</b>'
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())


@router.message(F.text == ADMIN_MENU['system'])
async def system_status(message: Message, state: FSMContext, repo: Repository, settings: Settings, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    stats_data = await repo.stats()
    configured = all([
        await repo.get_setting('target_channel_id'),
        await repo.get_setting('target_channel_url'),
    ])
    await message.answer(
        '╭━━━━━━━━━━━━━━━━━━━━╮\n'
        '         ⚙️ <b>TIZIM</b>\n'
        '╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'🤖 Bot: <b>{safe_html(settings.bot_username or "username belgilanmagan")}</b>\n'
        f'👑 Adminlar: <b>{len(settings.admin_ids)}/2</b>\n'
        f'📢 Post kanali: <b>{"✅" if configured else "⚠️ Sozlanmagan"}</b>\n'
        f'📚 Users: <b>{stats_data["users"]}</b>\n\n'
        '✅ DB va Redis startup vaqtida tekshiriladi.\n'
        '🧹 Publishing lock 15 daqiqadan oshsa pendingga qaytariladi.',
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard(),
    )
