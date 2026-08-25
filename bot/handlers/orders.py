"""Foydalanuvchi buyurtmalari."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import db
from bot import keyboards as kb
from bot.keyboards import M_MAIN
from bot.texts import fmt_dt, money, render, service_label, status_label

router = Router(name="orders")
PER_PAGE = 8


@router.callback_query(F.data.startswith("o:list:"))
async def cb_orders_list(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval(
        "SELECT COUNT(*) FROM orders WHERE user_id=%s", (call.from_user.id,), 0
    ) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    rows = await db.fetchall(
        "SELECT * FROM orders WHERE user_id=%s ORDER BY id DESC LIMIT %s OFFSET %s",
        (call.from_user.id, PER_PAGE, page * PER_PAGE),
    )
    lines = [f"{'{orders}'} Buyurtmalarim (sahifa {page + 1}/{total_pages}):\n"]
    if not rows:
        lines.append("{info} Hozircha buyurtmalar yo'q")
    for o in rows:
        lines.append(
            f"{'{doc}'} #{o['id']} · {service_label(o['service'])}\n"
            f"   💰 {money(o['price'])} so'm · {status_label(o['status'])}\n"
            f"   🕘 {fmt_dt(o['created_at'])}"
        )
    text, ent = render("\n".join(lines))
    await call.message.edit_text(
        text, entities=ent,
        reply_markup=kb.orders_kb(page, total_pages, [o["id"] for o in rows]),
    )


@router.callback_query(F.data.startswith("o:v:"))
async def cb_order_view(call: CallbackQuery):
    order_id = int(call.data.split(":")[-1])
    o = await db.fetchone(
        "SELECT * FROM orders WHERE id=%s AND user_id=%s", (order_id, call.from_user.id)
    )
    if not o:
        await call.answer("Buyurtma topilmadi", show_alert=True)
        return
    can_code = o["service"] == "number_s1" and o["status"] == "success" and bool(o.get("number"))
    text, ent = render(
        f"{'{doc}'} Buyurtma #{o['id']}\n\n"
        f"{'{box}'} Xizmat: {service_label(o['service'])}\n"
        f"🎯 Maqsad: {o['target'] or '—'}\n"
        f"{'{money}'} Narx: {money(o['price'])} so'm\n"
        f"{'{gear}'} Holat: {status_label(o['status'])}\n"
        f"{'{clock}'} Yaratilgan: {fmt_dt(o['created_at'])}\n"
        + (
            f"\n📱 Raqam: {o['number']}\n"
            f"{'{code}'} Kodni olish mumkin" if can_code else ""
        )
        + (
            f"\n\n{'{info}'} Izoh: {o['admin_note']}" if o.get("admin_note") else ""
        )
    )
    await call.message.edit_text(
        text, entities=ent,
        reply_markup=kb.order_view_kb(o["id"], o.get("number"), can_code),
    )


@router.callback_query(F.data == "o:ok")
async def cb_order_ok(call: CallbackQuery):
    await call.message.edit_text("✅ OK", reply_markup=kb.back("o:list:0"))
