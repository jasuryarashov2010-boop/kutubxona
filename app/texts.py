from aiogram.enums import ParseMode

APP_TITLE = '📚 <b>KITOBXON</b>'
APP_SUBTITLE = 'Adabiyotga mehr. Kitobxonlar fikri. Yangi tavsiyalar.'

USER_MENU = {
    'recommend': '📖 Kitob tavsiya qilish',
    'my': '📚 Mening tavsiyalarim',
    'rules': 'ℹ️ Tavsiya qoidalari',
    'channel': '📢 Kanalimiz',
    'support': '💬 Adminga yozish',
    'admin': '👑 Admin panel',
    'cancel': '❌ Bekor qilish',
}

ADMIN_MENU = {
    'pending': '📥 Tavsiyalar',
    'support': '📨 Murojaatlar',
    'broadcast': '📣 Barchaga xabar',
    'design': '🎨 Post dizayni',
    'reaction': '🔥 Reaksiya',
    'channel': '📢 Kanal sozlamalari',
    'users': '👥 Foydalanuvchilar',
    'stats': '📊 Statistika',
    'system': '⚙️ Tizim',
    'home': '⬅️ Bosh menyu',
}


def main_home() -> str:
    return (
        f'╭━━━━━━━━━━━━━━━━━━━━╮\n'
        f'      {APP_TITLE}\n'
        f'╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        f'📖 <b>O‘qigan kitobingizni tavsiya qiling.</b>\n'
        f'💭 Fikringiz boshqalarga yangi kitob topishga yordam beradi.\n\n'
        f'✨ <i>Yaxshi kitob — yaxshi suhbatning boshlanishi.</i>'
    )


def admin_home() -> str:
    return (
        '╭━━━━━━━━━━━━━━━━━━━━╮\n'
        '        👑 <b>ADMIN PANEL</b>\n'
        '╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        '🛠 Barcha boshqaruv funksiyalari pastdagi tugmalarda.\n\n'
        '📥 Moderatsiya  •  📨 Murojaatlar\n'
        '🎨 Dizayn  •  🔥 Reaksiya\n'
        '📢 Kanal  •  👥 Foydalanuvchilar\n'
        '📊 Statistika  •  ⚙️ Tizim'
    )


def rules_text() -> str:
    return (
        '╭━━━━━━━━━━━━━━━━━━━━╮\n'
        '      ℹ️ <b>TAVSIYA QOIDALARI</b>\n'
        '╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        '📚 Haqiqatan o‘qigan kitobingizni yuboring.\n'
        '✍️ Kitob nomi va muallifini aniq yozing.\n'
        '💭 Fikringizni qisqa, mazmunli va o‘zingizning so‘zlaringiz bilan yozing.\n'
        '🚫 Reklama, spam va aloqasiz matn yubormang.\n\n'
        '✅ Har bir tavsiya avval admin tomonidan tekshiriladi.'
    )


def subscription_text() -> str:
    return (
        '🔐 <b>BOTDAN FOYDALANISH UCHUN OBUNA BO‘LING</b>\n\n'
        '📢 Avval kanalga qo‘shiling, keyin <b>✅ Obunani tekshirish</b> tugmasini bosing.'
    )
