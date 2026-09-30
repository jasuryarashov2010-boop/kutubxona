from __future__ import annotations

from app.services.utils import safe_html, truncate

DEFAULT_HEADER = '╭━━━━━━━━━━━━━━━━━━━━╮\n      📚 <b>KITOB TAVSIYASI</b>\n╰━━━━━━━━━━━━━━━━━━━━╯'
DEFAULT_FOOTER = '📚 Siz ham o‘qigan kitobingizni tavsiya qiling.\n👉 @{bot}'


def render_recommendation(title: str, author: str, review: str, photo: bool = False) -> str:
    return (
        '📖 <b>' + safe_html(title) + '</b>\n\n'
        '✍️ <b>Muallif:</b> ' + safe_html(author) + '\n\n'
        '💭 <b>Kitobxon fikri:</b>\n'
        '<blockquote>' + safe_html(truncate(review, 900)) + '</blockquote>'
    )


def render_channel_post(title: str, author: str, review: str, header: str, footer: str, bot_username: str, show_recommender: bool = False, recommender: str | None = None) -> str:
    footer = footer.replace('{bot}', bot_username or 'kitobxon_bot')
    parts = [
        header.strip(),
        '',
        '📖 <b>' + safe_html(title) + '</b>',
        '✍️ <b>Muallif:</b> ' + safe_html(author),
        '',
        '💭 <b>Kitobxon fikri:</b>',
        '<blockquote>' + safe_html(truncate(review, 420)) + '</blockquote>',
    ]
    if show_recommender and recommender:
        parts.extend(['', '👤 <b>Tavsiya qilgan:</b> ' + safe_html(recommender)])
    if footer.strip():
        parts.extend(['', '━━━━━━━━━━━━━━━━━━━━', footer.strip()])
    return '\n'.join(parts).strip()


def render_channel_text(*args, **kwargs) -> str:
    return render_channel_post(*args, **kwargs)
