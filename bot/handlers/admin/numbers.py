"""Admin — raqam xizmatlari: Server 1 (Spider) va Server 2 (hisoblar)."""
from __future__ import annotations

import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, Message

import db
from bot.handlers.admin import kb, protect
from bot.states import AdminStates
from bot.texts import fmt_dt, money, render
from bot.utils import spider, tg_client
from bot.utils.spider import SpiderError

router = Router(name="admin_numbers")
protect(router)
PER_PAGE = 10


@router.callback_query(F.data == "ad:num")
async def cb_numbers_menu(call: CallbackQuery):
    text, ent = render(
        "{'server'} Raqam xizmatlari boshqaruvi\n\n"
        "{'info'} Server 1 — Spider API; Server 2 — zaxira hisoblar (sotish)."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.numbers_menu())


# ══════════════════════════════════════════════════════════════
#  SERVER 1
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "ad:num:s1")
async def cb_s1_menu(call: CallbackQuery):
    key = await db.get_setting("spider_api_key", "")
    text, ent = render(
        f"{'{server}'} Server 1 (Spider API)\n\n"
        f"{'{lock}'} API key: {'✔ kiritilgan' if key else '✖ kiritilmagan'}\n\n"
        f"{'{info}'} 'Davlatlarni yangilash' — API'dan davlatlar ro'yxatini oladi "
        f"(narxlar saqlanib qoladi)."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s1_menu())


@router.callback_query(F.data == "ad:nsync")
async def cb_sync_countries(call: CallbackQuery):
    await call.answer("Yuklanmoqda...")
    try:
        countries = await spider.get_countries()
    except SpiderError as e:
        text, ent = render(f"{'{warn}'} Xatolik: {e}\n\n{'{info}'} API kalitni tekshiring (Sozlamalar → Spider API).")
        await call.message.edit_text(text, entities=ent)
        return
    if not countries:
        await call.message.edit_text("❌ Davlatlar ro'yxati bo'sh keldi", reply_markup=kb.back_kb())
        return
    for c in countries:
        await db.execute(
            "INSERT INTO number_s1_countries (country, country_name) VALUES (%s,%s) "
            "ON DUPLICATE KEY UPDATE country_name=VALUES(country_name)",
            (c["country"], c["name"]),
        )
    await call.message.edit_text(
        f"✅ {len(countries)} ta davlat yangilandi", reply_markup=kb.back_kb("ad:num:s1")
    )


@router.callback_query(F.data.startswith("ad:ncl:"))
async def cb_country_list(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval("SELECT COUNT(*) FROM number_s1_countries", default=0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    rows = await db.fetchall(
        "SELECT * FROM number_s1_countries ORDER BY country_name LIMIT %s OFFSET %s",
        (PER_PAGE, page * PER_PAGE),
    )
    text, ent = render(
        f"{'{globe}'} Davlatlar ({total}):\n"
        f"{'{info}'} Narxni o'zgartirish uchun bosing. Sahifa {page + 1}/{total_pages}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s1_countries_kb(rows, page, total_pages))


@router.callback_query(F.data.startswith("ad:ncp:"))
async def cb_country_price(call: CallbackQuery, state: FSMContext):
    country = call.data.split(":")[-1]
    row = await db.fetchone("SELECT * FROM number_s1_countries WHERE country=%s", (country,))
    if not row:
        return
    await state.update_data(country=country)
    await state.set_state(AdminStates.country_price)
    text, ent = render(
        f"{'{edit}'} {row['country']} ({row['country_name']}) uchun narxni kiriting (so'm):\n"
        f"{'{info}'} Joriy: {money(row['price'])} so'm"
    )
    await call.message.answer(text, entities=ent)


@router.message(AdminStates.country_price, F.text)
async def msg_country_price(message: Message, state: FSMContext):
    from bot.utils.misc import parse_amount
    price = parse_amount(message.text)
    data = await state.get_data()
    country = data.get("country", "")
    await state.clear()
    if price <= 0:
        await message.answer("❗ Noto'g'ri narx")
        return
    await db.execute(
        "UPDATE number_s1_countries SET price=%s, enabled=1, updated_at=NOW() WHERE country=%s",
        (price, country),
    )
    await message.answer(f"✅ {country} narxi: {money(price)} so'm")


@router.callback_query(F.data.startswith("ad:nctg:"))
async def cb_country_toggle(call: CallbackQuery):
    country = call.data.split(":")[-1]
    await db.execute(
        "UPDATE number_s1_countries SET enabled = 1 - enabled, updated_at=NOW() WHERE country=%s",
        (country,),
    )
    await call.answer("O'zgartirildi")
    await cb_country_list(call)


# ══════════════════════════════════════════════════════════════
#  SERVER 2
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "ad:num:s2")
async def cb_s2_menu(call: CallbackQuery):
    total = int(await db.fetchval("SELECT COUNT(*) FROM number_stock WHERE status='available'", default=0) or 0)
    text, ent = render(
        f"{'{phone}'} Server 2 — zaxira raqamlar\n\n"
        f"{'{info}'} Sotuvda: {total} ta\n\n"
        f"{'{doc}'}' Raqam qo'shish: telefon → parol → narx → davlat."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s2_menu())


@router.callback_query(F.data == "ad:n2add")
async def cb_stock_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.stock_phone)
    text, ent = render(
        f"{'{plus}'} Yangi raqam (Server 2)\n\n"
        f"{'{edit}'} Telefon raqamni yuboring: +998901234567"
    )
    await call.message.answer(text, entities=ent)


@router.message(AdminStates.stock_phone, F.text)
async def msg_stock_phone(message: Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "")
    if len(phone) < 8:
        await message.answer("❗ Telefon noto'g'ri")
        return
    await state.update_data(stock_phone=phone)
    await state.set_state(AdminStates.stock_twofa)
    text, ent = render(
        f"{'{key}'} Hisob paroli (2FA) yoki login kodini kiriting.\n"
        f"{'{info}'}' Yo'q bo'lsa:  /skip  yozing."
    )
    await message.answer(text, entities=ent)


@router.message(AdminStates.stock_twofa, F.text)
async def msg_stock_twofa(message: Message, state: FSMContext):
    val = message.text.strip()
    if val.lower() == "/skip" or val == "-":
        val = ""
    await state.update_data(stock_twofa=val)
    await state.set_state(AdminStates.stock_price)
    await message.answer("💵 Sotish narxini kiriting (so'm):")


@router.message(AdminStates.stock_price, F.text)
async def msg_stock_price(message: Message, state: FSMContext):
    from bot.utils.misc import parse_amount
    price = parse_amount(message.text)
    if price <= 0:
        await message.answer("❗ Noto'g'ri narx")
        return
    await state.update_data(stock_price=price)
    await state.set_state(AdminStates.stock_country)
    await message.answer("🌍 Davlat kodini kiriting (masalan UZ, RU, KZ). /skip — UZ:")


@router.message(AdminStates.stock_country, F.text)
async def msg_stock_country(message: Message, state: FSMContext):
    val = message.text.strip().upper()
    if val.lower() in ("/skip", "-"):
        val = "UZ"
    await state.update_data(stock_country=val)
    await state.set_state(AdminStates.stock_note)
    await message.answer("📝 Izoh (ixtiyoriy). /skip — o'tkazib yuborish:")


@router.message(AdminStates.stock_note, F.text)
async def msg_stock_note(message: Message, state: FSMContext):
    data = await state.get_data()
    note = message.text.strip()
    if note.lower() in ("/skip", "-"):
        note = ""
    await state.clear()
    session_file = tg_client.session_path(data["stock_phone"], subdir="srv2")
    await db.execute(
        "INSERT INTO number_stock (phone, country, price, session_file, twofa, note) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (data["stock_phone"], data.get("stock_country", "UZ"),
         data["stock_price"], session_file, data.get("stock_twofa", ""), note),
    )
    text, ent = render(
        f"{'{check}'} Raqam saqlandi!\n\n"
        f"📱 {data['stock_phone']}\n"
        f"{'{money}'} Narx: {money(data['stock_price'])} so'm\n\n"
        f"{'{info}'} Endi sessiya faylini yuklashingiz mumkin (dokument sifatida)."
    )
    await message.answer(text, entities=ent, reply_markup=kb.s2_menu())


@router.callback_query(F.data.startswith("ad:n2:"))
async def cb_stock_list(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval("SELECT COUNT(*) FROM number_stock", default=0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    rows = await db.fetchall(
        "SELECT * FROM number_stock ORDER BY id DESC LIMIT %s OFFSET %s",
        (PER_PAGE, page * PER_PAGE),
    )
    text, ent = render(
        f"{'{phone}'} Zaxira raqamlar ({total}):\n"
        f"{'{info}'} Sahifa {page + 1}/{total_pages}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s2_kb(rows, page, total_pages))


@router.callback_query(F.data.startswith("ad:n2v:"))
async def cb_stock_view(call: CallbackQuery):
    sid = int(call.data.split(":")[-1])
    item = await db.fetchone("SELECT * FROM number_stock WHERE id=%s", (sid,))
    if not item:
        return
    buyer = await db.fetchone("SELECT id, username, first_name FROM users WHERE id=%s", (item["buyer_id"],)) \
        if item["buyer_id"] else None
    text, ent = render(
        f"{'{phone}'} Raqam #{item['id']}\n\n"
        f"📱 Telefon: {item['phone']}\n"
        f"{'{globe}'} Davlat: {item['country']}\n"
        f"{'{money}'} Narx: {money(item['price'])} so'm\n"
        f"{'{key}'} Parol: {item['twofa'] or '—'}\n"
        f"{'{gear}'} Holat: {item['status']}\n"
        f"{'{user}'} Xaridor: {buyer['first_name'] or buyer['username'] or buyer['id'] if buyer else '—'}\n"
        f"{'{orders}'} Buyurtma: #{item['order_id'] or '—'}\n"
        f"{'{calendar}'} Qo'shilgan: {fmt_dt(item['created_at'])}\n"
        f"{'{clock}'} Sotilgan: {fmt_dt(item['sold_at'])}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.s2_view_kb(item))


@router.callback_query(F.data.startswith("ad:n2sf:"))
async def cb_stock_file_select(call: CallbackQuery, state: FSMContext):
    sid = int(call.data.split(":")[-1])
    item = await db.fetchone("SELECT * FROM number_stock WHERE id=%s", (sid,))
    if not item:
        await call.answer("Topilmadi", show_alert=True)
        return
    await state.update_data(stock_id=sid)
    await state.set_state(AdminStates.stock_file)
    await call.message.answer(
        f"📎 {item['phone']} uchun .session faylini dokument sifatida yuboring:"
    )


@router.message(AdminStates.stock_file, F.document)
async def msg_stock_session(message: Message, state: FSMContext):
    data = await state.get_data()
    sid = int(data.get("stock_id", 0))
    await state.clear()
    item = await db.fetchone("SELECT * FROM number_stock WHERE id=%s", (sid,))
    if not item:
        await message.answer("❗ Raqam topilmadi")
        return
    doc = message.document
    name = doc.file_name or ""
    if not name.endswith(".session"):
        await message.answer("❗ .session fayl yuboring")
        return
    path = item["session_file"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    buf = await message.bot.download(doc)
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    await message.answer(
        f"✅ Sessiya yuklandi: {os.path.basename(path)}",
        reply_markup=kb.back_kb("ad:num:s2"),
    )


@router.callback_query(F.data.startswith("ad:n2on:"))
async def cb_stock_on(call: CallbackQuery):
    sid = int(call.data.split(":")[-1])
    await db.execute(
        "UPDATE number_stock SET status='available', buyer_id=NULL, order_id=NULL, sold_at=NULL WHERE id=%s",
        (sid,),
    )
    await call.answer("Sotuvga chiqarildi")
    await cb_stock_view(call)


@router.callback_query(F.data.startswith("ad:n2back:"))
async def cb_stock_back(call: CallbackQuery):
    sid = int(call.data.split(":")[-1])
    await db.execute(
        "UPDATE number_stock SET status='available', buyer_id=NULL, order_id=NULL, sold_at=NULL WHERE id=%s",
        (sid,),
    )
    await call.answer("Qayta sotuvga qo'yildi")
    await cb_stock_view(call)


@router.callback_query(F.data.startswith("ad:n2del:"))
async def cb_stock_delete(call: CallbackQuery):
    sid = int(call.data.split(":")[-1])
    await db.execute("UPDATE number_stock SET status='removed' WHERE id=%s", (sid,))
    await call.answer("O'chirildi")
    await call.message.edit_text("🗑 Raqam o'chirildi", reply_markup=kb.back_kb("ad:num:s2"))
