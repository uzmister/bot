"""Raqam olish handlerlari: Server 1 (spider) va Server 2 (zaxira raqamlar)."""
from __future__ import annotations

import os

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

import db
from bot import keyboards as kb
from bot.keyboards import M_MAIN
from bot.services import orders
from bot.services.orders import OrderError
from bot.texts import money, render

router = Router(name="numbers")


@router.callback_query(F.data == "svc:number")
async def cb_numbers(call: CallbackQuery):
    s1 = (await db.get_setting("number_s1_enabled", "1")) == "1"
    s2 = (await db.get_setting("number_s2_enabled", "1")) == "1"
    bal = await db.fetchval("SELECT balance FROM users WHERE id=%s", (call.from_user.id,), 0)
    text, ent = render(
        f"{'{phone}'} Raqam olish\n\n"
        f"{'{server}'} Server 1 — Spider API orqali virtual raqam\n"
        f"{'{server}'} Server 2 — Tayyor hisoblar (sessiya bilan)\n\n"
        f"{'{wallet}'} Balansingiz: {money(bal)} so'm"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.number_menu(s1, s2))


# ══════════════════════════════════════════════════════════════
#  SERVER 1
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "n:s1")
async def cb_s1_countries(call: CallbackQuery):
    countries = await db.fetchall(
        "SELECT * FROM number_s1_countries WHERE enabled=1 ORDER BY country_name"
    )
    if not countries:
        text, ent = render("{warn} Hozircha davlatlar qo'shilmagan")
        await call.message.edit_text(text, entities=ent, reply_markup=kb.back("svc:number"))
        return
    text, ent = render("{globe} Mamlakatni tanlang:")
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s1_countries(countries))


@router.callback_query(F.data.startswith("n:s1c:"))
async def cb_s1_country(call: CallbackQuery):
    country = call.data.split(":")[-1]
    row = await db.fetchone(
        "SELECT * FROM number_s1_countries WHERE country=%s AND enabled=1", (country,)
    )
    if not row:
        await call.answer("Bu davlat o'chirilgan")
        return
    text, ent = render(
        f"{'{globe}'} Mamlakat: {row['country_name'] or row['country']}\n"
        f"{'{money}'} Narx: {money(row['price'])} so'm\n\n"
        f"{'{info}'} Raqam olingach, telefon raqami va SMS kod ko'rsatiladi."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s1_buy_kb(row["country"]))


@router.callback_query(F.data.startswith("n:s1b:"))
async def cb_s1_buy(call: CallbackQuery):
    country = call.data.split(":")[-1]
    await call.answer("Raqam olinmoqda...")
    try:
        order = await orders.order_number_s1(call.from_user.id, country)
        text, ent = render(
            f"{'{check}'} Raqam olindi!\n\n"
            f"{'{orders}'} Buyurtma: #{order['id']}\n"
            f"📱 Raqam: <code>{order['number']}</code>\n"
            f"{'{money}'} Narx: {money(order['price'])} so'm\n\n"
            f"{'{code}'} Kodni olish tugmasini bosing."
        )
        text = text.replace("<code>", "").replace("</code>", "")
        await call.message.edit_text(text, entities=ent, reply_markup=kb.s1_code_kb(order["id"]))
    except OrderError as e:
        await call.message.edit_text(f"❌ Xatolik: {e.message}", reply_markup=kb.back("n:s1"))


@router.callback_query(F.data.startswith("n:s1code:"))
async def cb_s1_code(call: CallbackQuery):
    order_id = int(call.data.split(":")[-1])
    await call.answer("Kod so'ralmoqda...")
    try:
        code = await orders.number_s1_code(order_id)
        text, ent = render(
            f"{'{code}'} SMS kod: <code>{code}</code>\n\n"
            f"{'{warn}'} Kodni darhol ishlating!"
        )
        text = text.replace("<code>", "").replace("</code>", "")
        await call.message.edit_text(text, entities=ent, reply_markup=kb.back("o:list:0"))
    except OrderError as e:
        await call.answer(e.message, show_alert=True)
    except Exception as e:
        await call.answer(f"Kod olishda xato: {e}", show_alert=True)


# ══════════════════════════════════════════════════════════════
#  SERVER 2
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "n:s2")
async def cb_s2_stock(call: CallbackQuery):
    numbers = await db.fetchall(
        "SELECT * FROM number_stock WHERE status='available' ORDER BY price ASC LIMIT 50"
    )
    if not numbers:
        text, ent = render("{warn} Hozircha sotuvda raqamlar yo'q")
        await call.message.edit_text(text, entities=ent, reply_markup=kb.back("svc:number"))
        return
    text, ent = render(
        f"{'{phone}'}' Raqamlar:\n\n"
        f"{'{info}'} Raqamni tanlang — to'lovdan keyin sessiya kodi ko'rsatiladi."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s2_stock(numbers))


@router.callback_query(F.data.startswith("n:s2b:"))
async def cb_s2_buy(call: CallbackQuery):
    stock_id = int(call.data.split(":")[-1])
    stock = await db.fetchone("SELECT * FROM number_stock WHERE id=%s", (stock_id,))
    if not stock or stock["status"] != "available":
        await call.answer("Bu raqam allaqachon sotilgan", show_alert=True)
        return
    await call.answer("Raqam olinmoqda...")
    try:
        order = await orders.order_number_s2(call.from_user.id, stock_id)
        stock = await db.fetchone("SELECT * FROM number_stock WHERE id=%s", (stock_id,))
        text, ent = render(
            f"{'{check}'} Raqam sotib olindi!\n\n"
            f"📱 Raqam: {stock['phone']}\n"
            f"{'{key}'} Parol: {stock['twofa'] or '—'}\n"
            f"{'{money}'} Narx: {money(order['price'])} so'm\n\n"
            f"{'{warn}'} Sessiya fayli yuborilmoqda..."
        )
        await call.message.edit_text(text, entities=ent)
        if stock.get("session_file") and os.path.exists(stock["session_file"]):
            try:
                await call.message.answer_document(
                    FSInputFile(stock["session_file"]),
                    caption="🔑 Sessiya fayli — Telethon / Telegram Desktop ga ulang.",
                )
            except Exception:
                pass
    except OrderError as e:
        await call.message.edit_text(f"❌ Xatolik: {e.message}", reply_markup=kb.back("n:s2"))
