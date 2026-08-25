"""Admin bosh panel va statistika."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import db
from bot.handlers.admin import kb, protect
from bot.texts import money, render

router = Router(name="admin_panel")
protect(router)


async def stats() -> dict:
    today = "DATE(created_at) = CURDATE()"
    return {
        "users": int(await db.fetchval("SELECT COUNT(*) FROM users", default=0) or 0),
        "today_users": int(await db.fetchval(
            f"SELECT COUNT(*) FROM users WHERE {today}", default=0) or 0),
        "balance_sum": float(await db.fetchval(
            "SELECT COALESCE(SUM(balance),0) FROM users", default=0) or 0),
        "pending_dep": int(await db.fetchval(
            "SELECT COUNT(*) FROM deposits WHERE status='pending'", default=0) or 0),
        "dep_today": float(await db.fetchval(
            f"SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='success' AND {today}",
            default=0) or 0),
        "ord_today": float(await db.fetchval(
            f"SELECT COALESCE(SUM(price),0) FROM orders WHERE status='success' AND {today}",
            default=0) or 0),
        "ord_count": int(await db.fetchval(
            f"SELECT COUNT(*) FROM orders WHERE {today}", default=0) or 0),
        "active_acc": int(await db.fetchval(
            "SELECT COUNT(*) FROM tg_accounts WHERE status='active'", default=0) or 0),
        "open_tickets": int(await db.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE status='open'", default=0) or 0),
    }


@router.callback_query(F.data == "ad:main")
async def cb_admin_main(call: CallbackQuery):
    s = await stats()
    text, ent = render(
        f"{'{admin}'} Admin panel\n\n"
        f"{'{user}'} Foydalanuvchilar: {s['users']} (bugun +{s['today_users']})\n"
        f"{'{wallet}'} Jami balans: {money(s['balance_sum'])} so'm\n"
        f"{'{history}'} Bugungi to'lovlar: {money(s['dep_today'])} so'm\n"
        f"{'{orders}'} Bugungi buyurtmalar: {s['ord_count']} ta ({money(s['ord_today'])} so'm)\n"
        f"{'{clock}'} Kutilayotgan depozitlar: {s['pending_dep']} ta\n"
        f"{'{key}'} Faol hisoblar: {s['active_acc']} ta\n"
        f"{'{bell}'} Ochiq murojaatlar: {s['open_tickets']} ta"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.main())


@router.callback_query(F.data == "ad:stats")
async def cb_admin_stats(call: CallbackQuery):
    s = await stats()
    text, ent = render(
        f"{'{chart}'} Statistika\n\n"
        f"{'{user}'} Foydalanuvchilar: {s['users']}\n"
        f"{'{rocket}'} Bugun yangi: {s['today_users']}\n"
        f"{'{wallet}'} Balanslar yig'indisi: {money(s['balance_sum'])} so'm\n"
        f"{'{history}'} Bugun to'lov: {money(s['dep_today'])} so'm\n"
        f"{'{orders}'} Bugun buyurtma: {s['ord_count']} ta ({money(s['ord_today'])} so'm)\n"
        f"{'{clock}'} Kutilayotgan depozit: {s['pending_dep']} ta\n"
        f"{'{bell}'} Ochiq murojaat: {s['open_tickets']} ta"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.stats_kb())
