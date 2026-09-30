from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.texts import ADMIN_MENU, USER_MENU


def user_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=USER_MENU['recommend'])],
        [KeyboardButton(text=USER_MENU['my']), KeyboardButton(text=USER_MENU['rules'])],
        [KeyboardButton(text=USER_MENU['channel']), KeyboardButton(text=USER_MENU['support'])],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=USER_MENU['admin'])])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True, one_time_keyboard=False, input_field_placeholder='Bo‘limni tanlang…')


def cancel_keyboard(is_admin: bool, photo_step: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=USER_MENU['recommend'])],
        [KeyboardButton(text=USER_MENU['my']), KeyboardButton(text=USER_MENU['rules'])],
        [KeyboardButton(text=USER_MENU['channel']), KeyboardButton(text=USER_MENU['support'])],
    ]
    if photo_step:
        rows.append([KeyboardButton(text='⏭ Rasm yo‘q')])
    rows.append([KeyboardButton(text=USER_MENU['cancel'])])
    if is_admin:
        rows.append([KeyboardButton(text=USER_MENU['admin'])])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True, one_time_keyboard=False, input_field_placeholder='Javobingizni yozing…')


def admin_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=ADMIN_MENU['pending']), KeyboardButton(text=ADMIN_MENU['support'])],
        [KeyboardButton(text=ADMIN_MENU['broadcast']), KeyboardButton(text=ADMIN_MENU['design'])],
        [KeyboardButton(text=ADMIN_MENU['reaction']), KeyboardButton(text=ADMIN_MENU['channel'])],
        [KeyboardButton(text=ADMIN_MENU['users']), KeyboardButton(text=ADMIN_MENU['stats'])],
        [KeyboardButton(text=ADMIN_MENU['system']), KeyboardButton(text=ADMIN_MENU['home'])],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True, one_time_keyboard=False, input_field_placeholder='Admin bo‘limini tanlang…')


def subscribe_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📢 Kanalga qo‘shilish', url=channel_url)],
        [InlineKeyboardButton(text='✅ Obunani tekshirish', callback_data='sub:check')],
    ])


def recommendation_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Yuborish', callback_data='rec:submit')],
        [InlineKeyboardButton(text='✏️ Tahrirlash', callback_data='rec:edit')],
        [InlineKeyboardButton(text='❌ Bekor qilish', callback_data='rec:cancel')],
    ])


def recommendation_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📖 Kitob nomi', callback_data='rec:edit:title'), InlineKeyboardButton(text='✍️ Muallif', callback_data='rec:edit:author')],
        [InlineKeyboardButton(text='💭 Fikr', callback_data='rec:edit:review'), InlineKeyboardButton(text='🖼 Rasm', callback_data='rec:edit:photo')],
        [InlineKeyboardButton(text='⬅️ Preview', callback_data='rec:preview')],
    ])


def admin_recommendation_actions(rec_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Kanalga joylash', callback_data=f'admin:publish:{rec_id}'), InlineKeyboardButton(text='❌ Rad etish', callback_data=f'admin:reject:{rec_id}')],
        [InlineKeyboardButton(text='👀 Preview', callback_data=f'admin:preview:{rec_id}'), InlineKeyboardButton(text='✏️ Tahrirlash', callback_data=f'admin:edit:{rec_id}')],
    ])


def reject_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Bekor qilish', callback_data='admin:reject:cancel')]])


def admin_edit_fields(rec_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📖 Kitob', callback_data=f'adminedit:title:{rec_id}'), InlineKeyboardButton(text='✍️ Muallif', callback_data=f'adminedit:author:{rec_id}')],
        [InlineKeyboardButton(text='💭 Fikr', callback_data=f'adminedit:review:{rec_id}')],
    ])


def support_actions(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Javob berish', callback_data=f'support:reply:{ticket_id}'), InlineKeyboardButton(text='✅ Yopish', callback_data=f'support:close:{ticket_id}')],
    ])


def broadcast_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Yuborish', callback_data='broadcast:send'), InlineKeyboardButton(text='❌ Bekor qilish', callback_data='broadcast:cancel')],
    ])


def sub_settings_keyboard(force: bool) -> InlineKeyboardMarkup:
    state = '✅ Majburiy obuna: YOQILGAN' if force else '❌ Majburiy obuna: O‘CHIRILGAN'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎯 Post kanali ID', callback_data='channel:set:target_id'), InlineKeyboardButton(text='🔐 Obuna kanali ID', callback_data='channel:set:sub_id')],
        [InlineKeyboardButton(text='🔗 Post kanal linki', callback_data='channel:set:target_url'), InlineKeyboardButton(text='🔗 Obuna kanal linki', callback_data='channel:set:sub_url')],
        [InlineKeyboardButton(text=state, callback_data='channel:toggle:sub')],
        [InlineKeyboardButton(text='🧪 Holatni tekshirish', callback_data='channel:test'), InlineKeyboardButton(text='♻️ Standartlarni tiklash', callback_data='channel:reset')],
    ])


def reaction_settings_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✍️ Emoji yozish', callback_data='reaction:set')],
        [InlineKeyboardButton(text='✅ Yoqish' if not enabled else '❌ O‘chirish', callback_data='reaction:toggle')],
    ])


def design_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📝 Sarlavhani o‘zgartirish', callback_data='design:header')],
        [InlineKeyboardButton(text='🔚 Pastki matnni o‘zgartirish', callback_data='design:footer')],
        [InlineKeyboardButton(text='👀 Namuna ko‘rish', callback_data='design:preview')],
        [InlineKeyboardButton(text='♻️ Standart dizayn', callback_data='design:reset')],
    ])


def user_result_actions(user_id: int, blocked: bool) -> InlineKeyboardMarkup:
    label = '✅ Blokdan chiqarish' if blocked else '🚫 Bloklash'
    action = 'unblock' if blocked else 'block'
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f'user:{action}:{user_id}')]])


def admin_flow_keyboard() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=ADMIN_MENU['pending']), KeyboardButton(text=ADMIN_MENU['support'])], [KeyboardButton(text=ADMIN_MENU['broadcast']), KeyboardButton(text=ADMIN_MENU['design'])], [KeyboardButton(text=ADMIN_MENU['reaction']), KeyboardButton(text=ADMIN_MENU['channel'])], [KeyboardButton(text=ADMIN_MENU['users']), KeyboardButton(text=ADMIN_MENU['stats'])], [KeyboardButton(text=ADMIN_MENU['system']), KeyboardButton(text=ADMIN_MENU['home'])], [KeyboardButton(text=USER_MENU['cancel'])]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True, one_time_keyboard=False, input_field_placeholder='Javobingizni yozing…')
