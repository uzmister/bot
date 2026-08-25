"""Foydalanuvchi bilan ishlash: ro'yxatga olish, admin tekshiruvi."""
from __future__ import annotations

import logging
from typing import Optional

from aiogram.types import User

import config
import db

log = logging.getLogger("users")


async def upsert_user(user: User, ref_id: Optional[int] = None) -> dict:
    """Foydalanuvchini ro'yxatga oladi / yangilaydi. ref — bir marta yoziladi."""
    existing = await db.fetchone("SELECT * FROM users WHERE id=%s", (user.id,))
    if existing:
        await db.execute(
            "UPDATE users SET username=%s, first_name=%s, last_name=%s, "
            "last_seen=NOW() WHERE id=%s",
            (user.username, user.first_name, user.last_name, user.id),
        )
        return await db.fetchone("SELECT * FROM users WHERE id=%s", (user.id,))

    ref_id = ref_id if ref_id and ref_id != user.id else None
    await db.execute(
        "INSERT INTO users (id, username, first_name, last_name, ref_by) "
        "VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE last_seen=NOW()",
        (user.id, user.username, user.first_name, user.last_name, ref_id),
    )
    if ref_id:
        try:
            await db.execute(
                "INSERT INTO transactions (user_id, type, amount, balance_after, note) "
                "VALUES (%s,'ref_signup',0,0,'Yangi referal')",
                (ref_id,),
            )
        except Exception as e:
            log.warning("Referal signup log xatosi: %s", e)
    return await db.fetchone("SELECT * FROM users WHERE id=%s", (user.id,))


async def get_user(user_id: int) -> Optional[dict]:
    return await db.fetchone("SELECT * FROM users WHERE id=%s", (user_id,))


async def is_admin(user_id: int) -> bool:
    if user_id in config.ADMIN_IDS:
        return True
    row = await db.fetchone("SELECT user_id FROM admins WHERE user_id=%s", (user_id,))
    return bool(row)


async def set_banned(user_id: int, banned: bool) -> None:
    await db.execute("UPDATE users SET is_banned=%s WHERE id=%s", (1 if banned else 0, user_id))


async def count_users() -> int:
    return int(await db.fetchval("SELECT COUNT(*) FROM users", default=0) or 0)


async def count_referrals(user_id: int) -> int:
    return int(await db.fetchval("SELECT COUNT(*) FROM users WHERE ref_by=%s", (user_id,), 0) or 0)


async def referral_list(user_id: int, limit: int = 50) -> list[dict]:
    return await db.fetchall(
        "SELECT id, username, first_name, created_at FROM users WHERE ref_by=%s "
        "ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    )
