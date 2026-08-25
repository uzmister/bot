"""Middleware'lar: foydalanuvchini ro'yxatga olish va admin tekshiruvi."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

import db
from bot.services.users import upsert_user

log = logging.getLogger("mw")


class UserMiddleware(BaseMiddleware):
    """Har bir update'da foydalanuvchini bazaga yozadi (bloklanganlarni tekshiradi)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Update):
            user = event.from_user
        elif hasattr(event, "from_user"):
            user = event.from_user
        if user is not None and not user.is_bot:
            try:
                ref_id = None
                if isinstance(event, Update):
                    ref_id = _parse_ref(event)
                row = await upsert_user(user, ref_id)
                data["db_user"] = row
                if row and row.get("is_banned"):
                    return None
            except Exception as e:
                log.error("User middleware xatosi: %s", e)
        return await handler(event, data)


def _parse_ref(event: Update) -> int | None:
    """/start 123 yoki /start?ref=123 ko'rinishini o'qydi."""
    try:
        msg = event.message
        if not (msg and msg.text and msg.text.startswith("/start")):
            return None
        arg = msg.text.split(maxsplit=1)[1].strip() if " " in msg.text else ""
        arg = arg.split("?ref=")[-1].split("&")[0].strip()
        if arg.isdigit():
            return int(arg)
    except Exception:
        pass
    return None
