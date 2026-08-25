"""
Custom emoji dvigateli.

Admin panelda har bir kalit uchun haqiqiy custom emoji ID (document_id) kiritilishi
mumkin. ID berilgan bo'lsa — MessageEntityCustomEmoji ishlatiladi (haqiqiy custom
emoji ko'rinadi), aks holda oddiy Unicode emoji (fallback) ishlatiladi.

Matnlarda {kalit} ko'rinishida yoziladi. Misol: "Salom {star}".
"""
from __future__ import annotations

import logging
from typing import Optional

from aiogram.types import MessageEntity

import db

log = logging.getLogger("emoji")

# Kalit -> oddiy emoji (fallback). Barcha tugma/matn emojilari shu yerda.
FALLBACK: dict[str, str] = {
    "star": "⭐", "stars": "⭐️", "premium": "👑", "nft": "🖼", "gift": "🎁",
    "fire": "🔥", "phone": "📱", "money": "💰", "wallet": "👛", "cart": "🛒",
    "ref": "👥", "support": "🎧", "admin": "🛠", "orders": "📦", "back": "⬅️",
    "check": "✅", "cross": "❌", "warn": "⚠️", "info": "ℹ️", "edit": "✏️",
    "delete": "🗑", "plus": "➕", "minus": "➖", "refresh": "🔄", "clock": "⏱",
    "doc": "📄", "chart": "📊", "lock": "🔒", "key": "🔑", "user": "👤",
    "search": "🔍", "mail": "📨", "bank": "🏦", "card": "💳", "gear": "⚙️",
    "home": "🏠", "rocket": "🚀", "coupon": "🎟", "history": "🕘", "cancel": "🚫",
    "import": "📥", "export": "📤", "megaphone": "📣", "sos": "🆘", "hammer": "🔨",
    "eye": "👁", "diamond": "💎", "shield": "🛡", "bolt": "⚡️", "crown": "👑",
    "medal": "🏅", "trophy": "🏆", "ship": "🚚", "box": "📦", "list": "📋",
    "link": "🔗", "ok": "👍", "thumbs": "👍", "heart": "❤️", "star_face": "🤩",
    "wallet2": "💼", "coin": "🪙", "camera": "📷", "headset": "🎧", "flag": "🚩",
    "target": "🎯", "spark": "✨", "gift2": "🎀", "globe": "🌍", "server": "🖥",
    "code": "🔢", "signal": "📶", "sale": "🏷", "calendar": "📅", "time": "⏰",
    "chat": "💬", "quote": "💬", "bell": "🔔", "on": "🟢", "off": "🔴",
}

# Haqiqiy custom emoji ID lar (document_id, string). Admin paneIdan to'ldiriladi.
EMOJI_IDS: dict[str, str] = {}


class EmojiEngine:
    """{kalit} tokenlarini custom emoji / fallback emojiga aylantiradi."""

    def __init__(self) -> None:
        self.ids: dict[str, str] = {}

    async def reload(self) -> None:
        raw = await db.get_setting_json("emoji_ids", {})
        self.ids = {str(k): str(v) for k, v in raw.items() if v} if isinstance(raw, dict) else {}

    def emoji(self, key: str) -> str:
        return FALLBACK.get(key, "")

    def render(self, template: str) -> tuple[str, list[MessageEntity]]:
        """Matnni render qiladi. (text, entities) qaytaradi."""
        if "{" not in template:
            return template, []
        entities: list[MessageEntity] = []
        out: list[str] = []
        i = 0
        while i < len(template):
            ch = template[i]
            if ch == "{":
                end = template.find("}", i + 1)
                if end != -1:
                    key = template[i + 1:end]
                    if key in FALLBACK:
                        fallback = FALLBACK[key]
                        out.append(fallback)
                        emoji_id = self.ids.get(key)
                        if emoji_id and emoji_id.isdigit():
                            offset = sum(len(s) for s in out) - len(fallback)
                            entities.append(MessageEntity(
                                type="custom_emoji",
                                offset=offset,
                                length=len(fallback),
                                document_id=int(emoji_id),
                            ))
                        i = end + 1
                        continue
            out.append(ch)
            i += 1
        return "".join(out), entities


E = EmojiEngine()


def text(template: str) -> tuple[str, list[MessageEntity]]:
    """Qisqa yordamchi — handlerlarda: t, ent = text("...")"""
    return E.render(template)


async def reload_emojis() -> None:
    await E.reload()
