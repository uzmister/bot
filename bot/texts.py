"""Umumiy matn yordamchilari — pullar, vaqt, t.me link, emoji render."""
from __future__ import annotations

import re
from datetime import datetime

import pytz

import config
from bot.emoji import E

UZS = "so'm"


def money(value: float | int | None) -> str:
    """12 345 678 so'm ko'rinishi."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    if v == int(v):
        return f"{int(v):,}".replace(",", " ")
    return f"{v:,.2f}".replace(",", " ")


def render(template: str) -> tuple[str, list]:
    return E.render(template)


def fmt_dt(dt: datetime | None, with_time: bool = True) -> str:
    if not dt:
        return "—"
    tz = pytz.timezone(config.TIMEZONE)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    dt = dt.astimezone(tz)
    return dt.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def clean_username(raw: str | None) -> str | None:
    """t.me link, @user yoki oddiy username -> username."""
    if not raw:
        return None
    s = raw.strip()
    m = re.search(r"(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{5,64})", s)
    if m:
        return m.group(1)
    s = s.strip().lstrip("@").strip("/").strip()
    if s and re.fullmatch(r"[a-zA-Z0-9_]{5,64}", s):
        return s
    return None


def normalize_phone(raw: str | None) -> str:
    return re.sub(r"\D", "", raw or "")


def shorten_text(text: str, limit: int = 100) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 3] + "..."


def status_label(status: str) -> str:
    return {
        "pending": "⏳ Kutilmoqda",
        "processing": "🔄 Jarayonda",
        "success": "✅ Bajarildi",
        "cancel": "❌ Bekor qilindi",
        "fail": "❌ Xatolik",
    }.get(status, status)


def service_label(service: str) -> str:
    return {
        "stars": "⭐️ Stars",
        "premium": "👑 Premium",
        "nft": "🖼 NFT",
        "gift": "🎁 Gift",
        "reaction": "🔥 Postga stars",
        "number_s1": "📱 Raqam (Server 1)",
        "number_s2": "📱 Raqam (Server 2)",
        "deposit": "💳 To'lov",
    }.get(service, service)
