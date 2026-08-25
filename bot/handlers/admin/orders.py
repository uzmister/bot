"""Admin — buyurtmalar, hisobot, murojaatlar, reklama."""
from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from bot.handlers.admin import kb, protect
from bot.services import orders as order_svc
from bot.states import AdminStates
from bot.texts import fmt_dt, money, render, service_label, status_label

router = Router(name="admin_orders")
protect(router)
PER_PAGE = 10
log = logging.getLogger("admin_orders")


# ══════════════════════════════════════════════════════════════
#  BUYURTMALAR
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("ad:olf"))
async def cb_orders_filter_menu(call: CallbackQuery):
    await call.message.edit_text("📋 Filtr:", reply_markup=kb.orders_filter_kb("all"))


@router.callback_query(F.data.startswith("ad:ol:"))
async def cb_orders_list(call: CallbackQuery):
    _, _, status, page = call.data.split(":")
    page = int(page or 0)
    if status in ("all", "", None):
        where, args = "1=1", []
    else:
        where, args = "status=%s", [status]
    total = int(await db.fetchval(
        f"SELECT COUNT(*) FROM orders WHERE {where}", args, 0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    rows = await db.fetchall(
        f"SELECT * FROM orders WHERE {where} ORDER BY id DESC LIMIT %s OFFSET %s",
        (*args, PER_PAGE, page * PER_PAGE),
    )
    text, ent = render(
        f"{'{orders}'} Buyurtmalar ({total}) — {status or 'all'}:\n"
        f"{'{info}'} Sahifa {page + 1}/{total_pages}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.orders_kb(rows, status, page, total_pages))


@router.callback_query(F.data.startswith("ad:ov:"))
async def cb_order_view(call: CallbackQuery):
    oid = int(call.data.split(":")[-1])
    o = await db.fetchone("SELECT * FROM orders WHERE id=%s", (oid,))
    if not o:
        return
    u = await db.fetchone("SELECT id, username, first_name FROM users WHERE id=%s", (o["user_id"],))
    text, ent = render(
        f"{'{doc}'} Buyurtma #{o['id']}\n\n"
        f"{'{box}'} Xizmat: {service_label(o['service'])}\n"
        f"{'{user}'} Foydalanuvchi: {u['first_name'] or u['username']} ({o['user_id']})\n"
        f"🎯 Maqsad: {o['target'] or '—'}\n"
        f"⭐ Stars: {o['stars'] or '—'}\n"
        f"{'{money}'} Narx: {money(o['price'])} so'm\n"
        f"{'{gear}'} Holat: {status_label(o['status'])}\n"
        f"{'{calendar}'} Yaratilgan: {fmt_dt(o['created_at'])}\n"
        + (f"Ref: {o['external_ref']}\n" if o.get("external_ref") else "")
        + (f"📱 Raqam: {o['number']}\n" if o.get("number") else "")
        + (f"Izoh: {o['admin_note']}\n" if o.get("admin_note") else "")
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.order_view_kb(o))


@router.callback_query(F.data.startswith("ad:onft:"))
async def cb_nft_result(call: CallbackQuery, state: FSMContext):
    oid = int(call.data.split(":")[-1])
    await state.set_state(AdminStates.setting_value)
    await state.update_data(skey=f"_nft_result:{oid}")
    await call.message.answer("✍️ NFT natijasini yozing (foydalanuvchiga yuboriladi):")


async def finish_nft(message: Message, order_id: int, result_text: str) -> None:
    order = await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))
    if not order or order["status"] == "success":
        await message.answer("❗ Buyurtma allaqachon bajarilgan yoki topilmadi")
        return
    try:
        await order_svc.success_order(order_id, details={"result": result_text[:2000]})
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
        return
    try:
        ok, ent = render(
            f"{'{check}'} NFT xaridingiz bajarildi!\n\n"
            f"{'{orders}'} Buyurtma: #{order_id}\n"
            f"📦 Natija:\n{result_text[:1500]}"
        )
        await message.bot.send_message(order["user_id"], ok, entities=ent)
    except Exception as e:
        log.warning("NFT natijasi yuborilmadi: %s", e)
    await message.answer(f"✅ #{order_id} bajarildi deb belgilandi va foydalanuvchiga yuborildi")


@router.callback_query(F.data.startswith("ad:ocancel:"))
async def cb_order_cancel(call: CallbackQuery):
    oid = int(call.data.split(":")[-1])
    order = await db.fetchone("SELECT * FROM orders WHERE id=%s", (oid,))
    if not order or order["status"] in ("success", "cancel"):
        await call.answer("Bekor qilib bo'lmaydi", show_alert=True)
        return
    await order_svc.cancel_order(oid, "Admin bekor qildi")
    try:
        nope, ent = render(
            f"{'{cross}'} Buyurtma #{oid} bekor qilindi.\n"
            f"Pulingiz balansga qaytarildi: {money(order['price'])} so'm"
        )
        await call.bot.send_message(order["user_id"], nope, entities=ent)
    except Exception:
        pass
    await call.answer("Bekor qilindi")
    await cb_orders_list(call)


# ══════════════════════════════════════════════════════════════
#  HISOBOT
# ══════════════════════════════════════════════════════════════
def period_where(period: str) -> str:
    if period == "today":
        return "DATE(created_at)=CURDATE()"
    if period == "week":
        return "created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    if period == "month":
        return "DATE_FORMAT(created_at,'%Y-%m')=DATE_FORMAT(NOW(),'%Y-%m')"
    return "1=1"


@router.callback_query(F.data.startswith("ad:rep:"))
async def cb_report(call: CallbackQuery):
    period = call.data.split(":")[-1]
    w = period_where(period)

    orders_total = float(await db.fetchval(
        f"SELECT COALESCE(SUM(price),0) FROM orders WHERE status='success' AND {w}", default=0) or 0)
    orders_cnt = int(await db.fetchval(
        f"SELECT COUNT(*) FROM orders WHERE status='success' AND {w}", default=0) or 0)
    deposits_total = float(await db.fetchval(
        f"SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='success' AND {w}", default=0) or 0)
    deposits_cnt = int(await db.fetchval(
        f"SELECT COUNT(*) FROM deposits WHERE status='success' AND {w}", default=0) or 0)
    new_users = int(await db.fetchval(
        f"SELECT COUNT(*) FROM users WHERE {w}", default=0) or 0)
    by_service = await db.fetchall(
        f"SELECT service, COUNT(*) c, COALESCE(SUM(price),0) s FROM orders "
        f"WHERE status='success' AND {w} GROUP BY service ORDER BY s DESC"
    )
    top = await db.fetchall(
        f"SELECT user_id, COUNT(*) c, SUM(price) s FROM orders WHERE status='success' AND {w} "
        f"GROUP BY user_id ORDER BY s DESC LIMIT 5"
    )
    lines = [
        f"{'{chart}'} Hisobot — {period}\n",
        f"{'{orders}'} Buyurtmalar: {orders_cnt} ta / {money(orders_total)} so'm",
        f"{'{history}'} To'lovlar: {deposits_cnt} ta / {money(deposits_total)} so'm",
        f"{'{user}'} Yangi foydalanuvchi: {new_users} ta",
        "",
        f"{'{box}'} Xizmatlar kesimida:",
    ]
    for r in by_service:
        lines.append(f"• {service_label(r['service'])}: {r['c']} ta — {money(r['s'])} so'm")
    if not by_service:
        lines.append("• —")
    lines.append("")
    lines.append(f"{'{trophy}'} Top xaridorlar:")
    for i, r in enumerate(top, 1):
        lines.append(f"{i}. {r['user_id']} — {money(r['s'])} so'm ({r['c']} ta)")
    if not top:
        lines.append("• —")
    text, ent = render("\n".join(lines))
    await call.message.edit_text(text, entities=ent, reply_markup=kb.reports_kb(period))


# ══════════════════════════════════════════════════════════════
#  MUROJAATLAR
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("ad:tk:"))
async def cb_tickets(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval("SELECT COUNT(*) FROM tickets", default=0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    rows = await db.fetchall(
        "SELECT * FROM tickets ORDER BY status='open' DESC, id DESC LIMIT %s OFFSET %s",
        (PER_PAGE, page * PER_PAGE),
    )
    text, ent = render(
        f"{'{support}'} Murojaatlar ({total}):\n"
        f"{'{info}'} Sahifa {page + 1}/{total_pages}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.tickets_kb(rows, page, total_pages))


@router.callback_query(F.data.startswith("ad:tkv:"))
async def cb_ticket_view(call: CallbackQuery):
    tid = int(call.data.split(":")[-1])
    t = await db.fetchone("SELECT * FROM tickets WHERE id=%s", (tid,))
    if not t:
        return
    text, ent = render(
        f"{'{doc}'} Murojaat #{t['id']}\n\n"
        f"👤 Foydalanuvchi: {t['user_id']}\n"
        f"💬 Xabar: {t['message'][:1000]}\n"
        + (f"📩 Javob: {t['answer'][:500]}\n" if t.get("answer") else "")
        + f"{'{clock}'} Yaratilgan: {fmt_dt(t['created_at'])}\n"
        f"{'{gear}'} Holat: {'Ochiq' if t['status'] == 'open' else 'Yopilgan'}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.ticket_view_kb(t))


@router.callback_query(F.data.startswith("ad:tkr:"))
async def cb_ticket_reply(call: CallbackQuery, state: FSMContext):
    tid = int(call.data.split(":")[-1])
    await state.set_state(AdminStates.setting_value)
    await state.update_data(skey=f"_ticket_reply:{tid}")
    await call.message.answer("✍️ Javob matnini yozing (foydalanuvchiga yuboriladi):")


async def answer_ticket(message: Message, ticket_id: int, answer_text: str) -> None:
    t = await db.fetchone("SELECT * FROM tickets WHERE id=%s", (ticket_id,))
    if not t:
        await message.answer("❗ Murojaat topilmadi")
        return
    await db.execute(
        "UPDATE tickets SET answer=%s, status='closed', answered_at=NOW() WHERE id=%s",
        (answer_text[:3000], ticket_id),
    )
    try:
        ok, ent = render(
            f"{'{support}'} Sizning murojaatingizga javob:\n\n{answer_text[:2000]}"
        )
        await message.bot.send_message(t["user_id"], ok, entities=ent)
    except Exception as e:
        log.warning("Javob yuborilmadi: %s", e)
    await message.answer(f"✅ #{ticket_id} murojaatiga javob yuborildi")


# ══════════════════════════════════════════════════════════════
#  REKLAMA
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "ad:bcast")
async def cb_broadcast(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.setting_value)
    await state.update_data(skey="_broadcast")
    total = int(await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE is_banned=0", default=0) or 0)
    await call.message.answer(
        f"📣 Reklama yuborish — {total} ta foydalanuvchiga.\n\n"
        "Yubormoqchi bo'lgan xabaringizni yozing (matn):"
    )


async def do_broadcast(message: Message, text: str) -> None:
    users = await db.fetchall("SELECT id FROM users WHERE is_banned=0")
    total = len(users)
    ok = 0
    fail = 0
    for u in users:
        try:
            await message.bot.send_message(u["id"], text)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
        if (ok + fail) % 25 == 0:
            await message.bot.send_message(
                message.chat.id, f"📊 Jarayon: {ok + fail}/{total} yuborildi"
            )
    await message.bot.send_message(
        message.chat.id,
        f"✅ Reklama tugadi. Muvaffaqiyatli: {ok}, xato: {fail}, jami: {total}",
    )
