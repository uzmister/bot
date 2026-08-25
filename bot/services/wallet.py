"""Balans operatsiyalari — hisob yuritish, to'lov, qaytarish, referal."""
from __future__ import annotations

import logging
from decimal import Decimal

import aiomysql

import db

log = logging.getLogger("wallet")


class NoMoney(Exception):
    pass


async def _tx_update(conn, sql: str, args) -> None:
    async with conn.cursor() as cur:
        await cur.execute(sql, args)


async def change_balance(user_id: int, delta: float, tx_type: str, note: str = "") -> float:
    """Balansni o'zgartiradi va transaction yozadi. Yangi balansni qaytaradi."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            await _tx_update(conn, "UPDATE users SET balance = balance + %s WHERE id = %s", (delta, user_id))
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
                row = await cur.fetchone()
                new_balance = float(row["balance"]) if row else 0.0
            await _tx_update(
                conn,
                "INSERT INTO transactions (user_id, type, amount, balance_after, note) VALUES (%s,%s,%s,%s,%s)",
                (user_id, tx_type, delta, new_balance, note),
            )
            await conn.commit()
            return new_balance
        except Exception:
            await conn.rollback()
            raise


async def _get_pool() -> aiomysql.Pool:
    if db._pool is None:
        raise RuntimeError("DB tayyor emas")
    return db._pool


async def debit(user_id: int, amount: float, tx_type: str, note: str = "") -> float:
    """Balansdan pul olish. Yetmasa NoMoney."""
    if amount <= 0:
        raise NoMoney("Summa noto'g'ri")
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET balance = balance - %s WHERE id = %s AND balance >= %s",
                    (amount, user_id, amount),
                )
                if cur.rowcount == 0:
                    await conn.rollback()
                    raise NoMoney("Balansda mablag' yetarli emas")
                await cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
                row = await cur.fetchone()
                new_balance = float(row["balance"]) if row else 0.0
            await _tx_update(
                conn,
                "INSERT INTO transactions (user_id, type, amount, balance_after, note) VALUES (%s,%s,%s,%s,%s)",
                (user_id, tx_type, -amount, new_balance, note),
            )
            await conn.commit()
            return new_balance
        except NoMoney:
            raise
        except Exception:
            await conn.rollback()
            raise


async def credit(user_id: int, amount: float, tx_type: str, note: str = "") -> float:
    return await change_balance(user_id, amount, tx_type, note)


async def grant_referral_bonus(referrer_id: int, buyer_id: int, amount: float) -> float | None:
    """Referal bonus — xarid summasining foizi. Yangi qoldiq (yoki None)."""
    if not referrer_id or referrer_id == buyer_id:
        return None
    enabled = await db.get_setting("referral_enabled", "1") == "1"
    if not enabled:
        return None
    try:
        percent = float(await db.get_setting("referral_percent", "5"))
    except ValueError:
        percent = 5.0
    bonus = round(amount * percent / 100.0, 2)
    if bonus <= 0:
        return None
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET balance = balance + %s, ref_earned = ref_earned + %s WHERE id = %s",
                    (bonus, bonus, referrer_id),
                )
                if cur.rowcount == 0:
                    await conn.rollback()
                    return None
                await cur.execute("SELECT balance FROM users WHERE id = %s", (referrer_id,))
                row = await cur.fetchone()
                new_balance = float(row["balance"]) if row else 0.0
            await _tx_update(
                conn,
                "INSERT INTO transactions (user_id, type, amount, balance_after, note) "
                "VALUES (%s, 'ref_bonus', %s, %s, %s)",
                (referrer_id, bonus, new_balance, f"Referal bonus (foydalanuvchi #{buyer_id})"),
            )
            await conn.commit()
            return new_balance
        except Exception:
            await conn.rollback()
            raise


async def force_balance(user_id: int, new_balance: float, note: str = "") -> float:
    """Admin uchun — balansni to'g'ridan-to'g'ri o'zgartirish."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET balance = %s WHERE id = %s", (new_balance, user_id)
                )
            await _tx_update(
                conn,
                "INSERT INTO transactions (user_id, type, amount, balance_after, note) "
                "VALUES (%s, 'admin_fix', %s, %s, %s)",
                (user_id, 0, new_balance, note or "Admin tomonidan"),
            )
            await conn.commit()
            return new_balance
        except Exception:
            await conn.rollback()
            raise


async def add_balance(user_id: int, amount: float, note: str = "") -> float:
    delta = abs(amount)
    return await change_balance(user_id, delta, "admin_add", note or "Admin tomonidan qo'shildi")


async def sub_balance(user_id: int, amount: float, note: str = "") -> float:
    delta = abs(amount)
    try:
        return await debit(user_id, delta, "admin_sub", note or "Admin tomonidan yechildi")
    except NoMoney:
        return await change_balance(user_id, -delta, "admin_sub", note or "Admin tomonidan yechildi (manfiy)")
