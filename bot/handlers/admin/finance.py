"""Admin — moliya: kartalar, depozitlar, tranzaksiyalar."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from bot.handlers.admin import kb, protect
from bot.services import wallet
from bot.states import AdminStates
from bot.texts import fmt_dt, money, render

router = Router(name="admin_finance")
protect(router)
PER_PAGE = 10


@router.callback_query(F.data == "ad:fin")
async def cb_finance(call: CallbackQuery):
    text, ent = render("{'bank'} Moliya bo'limi\n\n{'spark'} Kerakli bo'limni tanlang.")
    await call.message.edit_text(text, entities=ent, reply_markup=kb.finance_menu())


# ══════════════════════════════════════════════════════════════
#  KARTALAR
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("ad:cards:"))
async def cb_cards(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval("SELECT COUNT(*) FROM payment_methods", default=0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    cards = await db.fetchall(
        "SELECT * FROM payment_methods ORDER BY id DESC LIMIT %s OFFSET %s",
        (PER_PAGE, page * PER_PAGE),
    )
    text, ent = render(
        f"{'{card}'} To'lov kartalari ({total}):\n\n"
        f"{'{info}'} Faol kartalar to'lov sahifasida ko'rinadi."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.cards_kb(cards, page, total_pages))


@router.callback_query(F.data == "ad:cadd")
async def cb_card_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.card_number)
    text, ent = render(
        "{'plus'} Yangi karta qo'shish\n\n"
        "{'edit'} Karta raqamini yuboring, masalan: 8600 1234 5678 9012"
    )
    await call.message.answer(text, entities=ent)


@router.message(AdminStates.card_number, F.text)
async def msg_card_number(message: Message, state: FSMContext):
    digits = "".join(c for c in message.text if c.isdigit())
    if len(digits) < 12:
        await message.answer("❗ Karta raqami noto'g'ri")
        return
    await state.update_data(card_number=digits)
    await state.set_state(AdminStates.card_name)
    await message.answer("👤 Karta egasining ismini yuboring (masalan: ALIYEV ALI):")


@router.message(AdminStates.card_name, F.text)
async def msg_card_name(message: Message, state: FSMContext):
    data = await state.get_data()
    number = data.get("card_number", "")
    name = message.text.strip()[:128]
    await state.clear()
    await db.execute(
        "INSERT INTO payment_methods (method, card_number, card_name) VALUES (%s,%s,%s)",
        ("UZCARD", number, name),
    )
    await message.answer("✅ Karta qo'shildi", reply_markup=kb.back_kb())


@router.callback_query(F.data.startswith("ad:cardv:"))
async def cb_card_view(call: CallbackQuery):
    cid = int(call.data.split(":")[-1])
    card = await db.fetchone("SELECT * FROM payment_methods WHERE id=%s", (cid,))
    if not card:
        return
    status_txt = "Faol" if card["is_active"] else "O'chirilgan"
    text, ent = render(
        "{'card'} Karta\n\n"
        f"Raqam: {card['card_number']}\n"
        f"👤 Egasi: {card['card_name'] or '—'}\n"
        f"{'{gear}'} Holat: {status_txt}\n"
        f"{'{calendar}'} Qo'shilgan: {fmt_dt(card['created_at'])}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.card_view_kb(card))


@router.callback_query(F.data.startswith("ad:ctg:"))
async def cb_card_toggle(call: CallbackQuery):
    cid = int(call.data.split(":")[-1])
    await db.execute("UPDATE payment_methods SET is_active = 1 - is_active WHERE id=%s", (cid,))
    await call.answer("O'zgartirildi")
    await cb_card_view(call)


@router.callback_query(F.data.startswith("ad:cdel:"))
async def cb_card_delete(call: CallbackQuery):
    cid = int(call.data.split(":")[-1])
    await db.execute("DELETE FROM payment_methods WHERE id=%s", (cid,))
    await call.answer("O'chirildi")
    await call.message.edit_text("🗑 Karta o'chirildi", reply_markup=kb.back_kb())


# ══════════════════════════════════════════════════════════════
#  DEPOZITLAR
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("ad:dep:"))
async def cb_deposits(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval("SELECT COUNT(*) FROM deposits", default=0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    deps = await db.fetchall(
        "SELECT * FROM deposits ORDER BY status='pending' DESC, id DESC LIMIT %s OFFSET %s",
        (PER_PAGE, page * PER_PAGE),
    )
    text, ent = render(
        f"{'{history}'} Depozitlar ({total}):\n"
        f"{'{info}'} Avval kutilayotganlar ko'rinadi. Sahifa {page + 1}/{total_pages}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.deposits_kb(deps, page, total_pages))


@router.callback_query(F.data.startswith("ad:depv:"))
async def cb_deposit_view(call: CallbackQuery):
    did = int(call.data.split(":")[-1])
    dep = await db.fetchone("SELECT * FROM deposits WHERE id=%s", (did,))
    if not dep:
        return
    text, ent = render(
        f"{'{doc}'} Depozit #{dep['id']}\n\n"
        f"👤 Foydalanuvchi: {dep['user_id']}\n"
        f"{'{money}'} Summa: {money(dep['amount'])} so'm\n"
        f"{'{card}'} Usul: {dep['method']}\n"
        f"{'{key}'} Oxirgi 4: {dep['card_digits'] or '—'}\n"
        f"{'{gear}'} Holat: {dep['status']}\n"
        f"{'{calendar}'} Yaratilgan: {fmt_dt(dep['created_at'])}\n"
        f"Xabar ID: {dep['matched_msg_id'] or '—'}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.deposit_view_kb(dep))


@router.callback_query(F.data.startswith("ad:depok:"))
async def cb_deposit_approve(call: CallbackQuery):
    did = int(call.data.split(":")[-1])
    updated = await db.execute_rowcount(
        "UPDATE deposits SET status='success', updated_at=NOW() WHERE id=%s AND status='pending'",
        (did,),
    )
    if not updated:
        await call.answer("Depozit allaqachon boshqa holatda", show_alert=True)
        return
    dep = await db.fetchone("SELECT * FROM deposits WHERE id=%s", (did,))
    new_bal = await wallet.credit(
        dep["user_id"], float(dep["amount"]), "deposit",
        f"To'lov tasdiqlandi (admin) #{did} {dep['method']}",
    )
    try:
        ok, ent = render(
            f"{'{check}'} To'lovingiz tasdiqlandi!\n"
            f"{'{money}'} Summa: {money(dep['amount'])} so'm\n"
            f"{'{wallet}'} Balans: {money(new_bal)} so'm"
        )
        await call.bot.send_message(dep["user_id"], ok, entities=ent)
    except Exception:
        pass
    await call.answer("Tasdiqlandi")
    await cb_deposit_view(call)


@router.callback_query(F.data.startswith("ad:depno:"))
async def cb_deposit_cancel(call: CallbackQuery):
    did = int(call.data.split(":")[-1])
    await db.execute(
        "UPDATE deposits SET status='cancel', updated_at=NOW() WHERE id=%s AND status='pending'",
        (did,),
    )
    await call.answer("Bekor qilindi")
    await cb_deposit_view(call)


# ══════════════════════════════════════════════════════════════
#  TRANZAKSIYALAR
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("ad:tx:"))
async def cb_tx(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval("SELECT COUNT(*) FROM transactions", default=0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    rows = await db.fetchall(
        "SELECT * FROM transactions ORDER BY id DESC LIMIT %s OFFSET %s",
        (PER_PAGE, page * PER_PAGE),
    )
    lines = [f"{'{doc}'} Tranzaksiyalar ({total}), sahifa {page + 1}/{total_pages}:"]
    if not rows:
        lines.append("{info} Bo'sh")
    for r in rows:
        lines.append(
            f"#{r['id']} · {r['user_id']} · {r['type']} · {r['amount']} so'm · "
            f"balans {r['balance_after']} · {fmt_dt(r['created_at'])}"
        )
    text, ent = render("\n".join(lines))
    await call.message.edit_text(text, entities=ent, reply_markup=kb.tx_kb(rows, page, total_pages))


@router.callback_query(F.data.startswith("ad:txv:"))
async def cb_tx_view(call: CallbackQuery):
    tid = int(call.data.split(":")[-1])
    t = await db.fetchone("SELECT * FROM transactions WHERE id=%s", (tid,))
    if not t:
        return
    text, ent = render(
        f"{'{doc}'} Tranzaksiya #{t['id']}\n\n"
        f"👤 Foydalanuvchi: {t['user_id']}\n"
        f"{'{box}'} Turi: {t['type']}\n"
        f"{'{money}'} Summa: {t['amount']} so'm\n"
        f"{'{wallet}'} Balans: {t['balance_after']} so'm\n"
        f"Izoh: {t['note'] or '—'}\n"
        f"{'{calendar}'} Vaqt: {fmt_dt(t['created_at'])}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.back_kb())
