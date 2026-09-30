from __future__ import annotations

import html
import re


def safe_html(value: str | None) -> str:
    return html.escape(value or '', quote=False)


def normalize_key(title: str, author: str) -> str:
    text = f'{title.lower()} {author.lower()}'
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
    return text.strip()


def truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + '…'


def status_label(status: str) -> str:
    return {
        'pending': '🟡 Ko‘rib chiqilmoqda',
        'publishing': '🟠 Kanalga chiqarilmoqda',
        'published': '🟢 Kanalga joylangan',
        'rejected': '🔴 Rad etilgan',
    }.get(status, status)
