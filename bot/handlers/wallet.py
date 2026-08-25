"""Balans handlerlari: to'ldirish (avtomatik aniqlash), tarix."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from bot import keyboards as kb
from bot.keyboards import M_MAIN
from bot.states import UserStates
from bot.texts import fmt_dt, money, render

router = Router(name="wallet")
log = logging.getLogger("wallet")

SERVICE_TX = {
    "deposit": "To'lov",
    "order": "Buyurtma",
    "refund": "Qaytarish",
    "ref_bonus": "Referal bonus",
    "admin_add": "Admin qo'shdi",
    "admin_sub": "Admin yechdi",
    "ref_signup": "Yangi referal",
    "admin_fix": "Admin tuzatish",
}


@router.callback_query(F.data == "w:main")
async def cb_wallet(call: CallbackQuery):
    bal = await db.fetchval("SELECT balance FROM users WHERE id=%s", (call.from_user.id,), 0)
    text, ent = render(
        f"{'{wallet}'} Sizning balansingiz\n\n"
        f"{'{money}'} Balans: {money(bal)} so'm\n\n"
        f"{'{card}'} To'ldirish uchun karta quyidagi bo'limda."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.wallet_menu())


@router.callback_query(F.data == "w:topup")
async def cb_topup(call: CallbackQuery):
    methods = await db.fetchall(
        "SELECT * FROM payment_methods WHERE is_active=1 ORDER BY id"
    )
    if not methods:
        text, ent = render("{warn} Hozircha to'lov kartalari qo'shilmagan")
        await call.message.edit_text(text, entities=ent, reply_markup=kb.back("w:main"))
        return
    text, ent = render(
        f"{'{card}'} To'lov usulini tanlang:\n\n"
        f"{'{info}'} Karta raqamiga aynan belgilangan summani o'tkazing."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.topup_methods(methods))


@router.callback_query(F.data.startswith("w:m:"))
async def cb_topup_method(call: CallbackQuery, state: FSMContext):
    _, _, method, card_id = call.data.split(":")
    await state.update_data(topup_method=method, topup_card_id=int(card_id))
    await state.set_state(UserStates.topup_amount)
    min_dep = await db.get_setting("min_deposit", "10000")
    text, ent = render(
        f"{'{edit}'} To'lov summasini kiriting (so'm):\n\n"
        f"{'{info}'} Minimal summa: {money(min_dep)} so'm"
    )
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.topup_amount, F.text)
async def msg_topup_amount(message: Message, state: FSMContext):
    from bot.utils.misc import parse_amount
    amount = parse_amount(message.text)
    min_dep = float(await db.get_setting("min_deposit", "10000"))
    if amount < min_dep:
        await message.answer(f"❗ Minimal summa {money(min_dep)} so'm")
        return
    if amount > 100_000_000:
        await message.answer("❗ Bir martada 100 000 000 so'mdan ko'p kiritib bo'lmaydi")
        return
    data = await state.get_data()
    method = data.get("topup_method")
    card_id = int(data.get("topup_card_id", 0))
    card = await db.fetchone("SELECT * FROM payment_methods WHERE id=%s", (card_id,))
    if not card:
        await message.answer("❗ Karta topilmadi")
        return
    await state.update_data(topup_amount=amount)
    text, ent = render(
        f"{'{card}'} To'lov ma'lumotlari\n\n"
        f"{'{bank}'} Karta: <b>{card['card_number']}</b>\n"
        f"{'{user}'} Ism: {card['card_name'] or '—'}\n"
        f"{'{money}'} Summa: <b>{money(amount)} so'm</b>\n\n"
        f"{'{warn}'} Aynan shu summani o'tkazing. Xabarnoma xatosini oldini olish "
        f"uchun karta raqamining oxirgi 4 raqamini kiriting (aniqroq moslik)."
    )
    text = text.replace("<b>", "").replace("</b>", "")
    await message.answer(text, entities=ent, reply_markup=kb.last4_kb(method, card_id))


@router.callback_query(F.data.startswith("w:4:"))
async def cb_last4_ask(call: CallbackQuery, state: FSMContext):
    _, _, method, card_id = call.data.split(":")
    await state.set_state(UserStates.topup_last4)
    text, ent = render("{edit} Karta raqamining oxirgi 4 raqamini kiriting:")
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.topup_last4, F.text)
async def msg_last4(message: Message, state: FSMContext):
    digits = "".join(ch for ch in message.text if ch.isdigit())[-4:]
    if len(digits) != 4:
        await message.answer("❗ Oxirgi 4 raqamni kiritishingiz kerak.")
        return
    await state.update_data(topup_last4=digits)
    data = await state.get_data()
    method = data.get("topup_method")
    card_id = data.get("topup_card_id")
    amount = float(data.get("topup_amount", 0))
    card = await db.fetchone("SELECT * FROM payment_methods WHERE id=%s", (card_id,))
    text, ent = render(
        f"{'{card}'} Tekshirish\n\n"
        f"{'{bank}'} Karta: {card['card_number']}\n"
        f"{'{money}'} Summa: {money(amount)} so'm\n"
        f"{'{key}'} Oxirgi 4: {digits}\n\n"
        f"{'{check}'} To'lovni amalga oshirgach, \"To'lov qildim\" tugmasini bosing."
    )
    await message.answer(text, entities=ent, reply_markup=kb.deposit_paid_kb(method, card_id))


@router.callback_query(F.data.startswith("w:n4:"))
async def cb_no_last4(call: CallbackQuery, state: FSMContext):
    _, _, method, card_id = call.data.split(":")
    data = await state.get_data()
    amount = float(data.get("topup_amount", 0) or 0)
    await state.update_data(topup_last4="")
    card = await db.fetchone("SELECT * FROM payment_methods WHERE id=%s", (int(card_id),))
    text, ent = render(
        f"{'{card}'} To'lov ma'lumotlari\n\n"
        f"{'{bank}'} Karta: {card['card_number'] if card else '—'}\n"
        f"{'{money}'} Summa: {money(amount)} so'm\n\n"
        f"{'{check}'} To'lovni amalga oshirgach, \"To'lov qildim\" tugmasini bosing."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.deposit_paid_kb(method, card_id))


@router.callback_query(F.data.startswith("w:pay:"))
async def cb_paid(call: CallbackQuery, state: FSMContext):
    _, _, method, card_id = call.data.split(":")
    data = await state.get_data()
    amount = float(data.get("topup_amount", 0) or 0)
    last4 = str(data.get("topup_last4", "") or "")
    await state.clear()

    if amount <= 0:
        await call.answer("Summa yo'q, qaytadan boshlang", show_alert=True)
        return

    # Faqat bitta pending depozit bo'lsin
    existing = await db.fetchone(
        "SELECT * FROM deposits WHERE user_id=%s AND status='pending' "
        "AND created_at > NOW() - INTERVAL 15 MINUTE ORDER BY id DESC LIMIT 1",
        (call.from_user.id,),
    )
    if existing:
        dep = existing
    else:
        dep_id = await db.execute(
            "INSERT INTO deposits (user_id, amount, method, card_digits) VALUES (%s,%s,%s,%s)",
            (call.from_user.id, amount, method.upper(), last4 or None),
        )
        dep = await db.fetchone("SELECT * FROM deposits WHERE id=%s", (dep_id,))

    enabled = (await db.get_setting("watcher_enabled", "1")) == "1"
    text, ent = render(
        f"{'{clock}'} To'lov kutilmoqda...\n\n"
        f"{'{orders}'} Depozit: #{dep['id']}\n"
        f"{'{card}'} Karta: {method}\n"
        f"{'{money}'} Summa: {money(amount)} so'm\n\n"
        + (f"{'{spark}'} To'lov avtomatik tekshirilmoqda. Bir necha daqiqada balansga qo'shiladi."
           if enabled else
           f"{'{warn}'} Avtomatik tekshirish o'chirilgan. Admin bilan bog'laning.")
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.back("w:main"))


@router.callback_query(F.data.startswith("w:hist:"))
async def cb_history(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    per = 10
    rows = await db.fetchall(
        "SELECT * FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT %s OFFSET %s",
        (call.from_user.id, per + 1, page * per),
    )
    total = int(await db.fetchval("SELECT COUNT(*) FROM transactions WHERE user_id=%s", (call.from_user.id,), 0) or 0)
    lines = [f"{'{history}'} To'lovlar tarixi (sahifa {page + 1}):\n"]
    if not rows:
        lines.append("{info} Hozircha yozuvlar yo'q")
    for r in rows[:per]:
        sign = "+" if float(r["amount"]) >= 0 else "−"
        lines.append(
            f"{'{doc}'} #{r['id']} {SERVICE_TX.get(r['type'], r['type'])} — "
            f"{sign}{money(abs(float(r['amount'])))} so'm\n"
            f"   🕘 {fmt_dt(r['created_at'])} | balans: {money(r['balance_after'])}"
        )
    text, ent = render("\n".join(lines))
    total_pages = max(1, (total + per - 1) // per)
    await call.message.edit_text(text, entities=ent, reply_markup=kb.orders_kb_nav(page, total_pages, "w:hist:"))



