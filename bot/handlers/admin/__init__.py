"""Admin panel — barcha bo'limlar."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Router
from aiogram.types import TelegramObject

import db
from bot.services.users import is_admin

log = logging.getLogger("admin")


class AdminOnly(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None) or (
            getattr(getattr(event, "message", None), "from_user", None)
        )
        if user is None:
            return None
        try:
            if not await is_admin(user.id):
                return None
        except Exception as e:
            log.error("Admin tekshiruvi xatosi: %s", e)
            return None
        return await handler(event, data)


admin_mw = AdminOnly()


def protect(router: Router) -> None:
    router.message.middleware(admin_mw)
    router.callback_query.middleware(admin_mw)
