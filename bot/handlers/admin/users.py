"""Admin — foydalanuvchilar boshqaruvi."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from bot.handlers.admin import kb, protect
from bot.services import wallet
from bot.services.users import count_referrals, referral_list, set_banned
from bot.states import AdminStates
from bot.texts import fmt_dt, money, render

router = Router(name="admin_users")
protect(router)
PER_PAGE = 10


async def render_user(u: dict) -> tuple[str, list]:
    refs = await count_referrals(u["id"])
    return render(
        f"{'{user}'} Foydalanuvchi\n\n"
        f"ID: {u['id']}\n"
        f"👤 Ism: {u['first_name'] or '—'} {u['last_name'] or ''}\n"
        f"@ Username: @{u['username'] or '—'}\n"
        f"{'{wallet}'} Balans: {money(u['balance'])} so'm\n"
        f"{'{ref}'} Referallar: {refs} ta\n"
        f"{'{orders}'} Buyurtmalar: {u['order_count']} ta\n"
        f"{'{calendar}'} Ro'yxatdan o'tgan: {fmt_dt(u['created_at'])}\n"
        f"{'{clock}'} Oxirgi faollik: {fmt_dt(u['last_seen'])}\n"
        f"{'{warn}'} Holat: {'Bloklangan' if u['is_banned'] else 'Faol'}"
    )


@router.callback_query(F.data.startswith("ad:us:"))
async def cb_users_list(call: CallbackQuery):
    page = int(call.data.split(":")[-1] or 0)
    total = int(await db.fetchval("SELECT COUNT(*) FROM users", default=0) or 0)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages - 1)
    rows = await db.fetchall(
        "SELECT id, first_name, username, balance, is_banned, created_at FROM users "
        "ORDER BY id DESC LIMIT %s OFFSET %s",
        (PER_PAGE, page * PER_PAGE),
    )
    text, ent = render(
        f"{'{user}'} Foydalanuvchilar ({total}):\n"
        f"{'{info}'} Sahifa {page + 1}/{total_pages}"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.users_list_kb(rows, page, total_pages))


@router.callback_query(F.data == "ad:usearch")
async def cb_user_search(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.user_search)
    await call.message.answer("🔍 ID yoki username kiriting:")


@router.message(AdminStates.user_search, F.text)
async def msg_user_search(message: Message, state: FSMContext):
    q = message.text.strip()
    await state.clear()
    q = q.lstrip("@").lower()
    row = None
    if q.isdigit():
        row = await db.fetchone("SELECT * FROM users WHERE id=%s", (int(q),))
    if not row:
        row = await db.fetchone("SELECT * FROM users WHERE LOWER(username)=%s", (q,))
    if not row:
        await message.answer("⚪ Foydalanuvchi topilmadi")
        return
    text, ent = await render_user(row)
    await message.answer(text, entities=ent, reply_markup=kb.user_view_kb(row["id"], bool(row["is_banned"])))


@router.callback_query(F.data.startswith("ad:uv:"))
async def cb_user_view(call: CallbackQuery):
    uid = int(call.data.split(":")[-1])
    u = await db.fetchone("SELECT * FROM users WHERE id=%s", (uid,))
    if not u:
        await call.answer("Topilmadi", show_alert=True)
        return
    text, ent = await render_user(u)
    await call.message.edit_text(text, entities=ent, reply_markup=kb.user_view_kb(uid, bool(u["is_banned"])))


@router.callback_query(F.data.startswith("ad:uban:"))
async def cb_user_ban(call: CallbackQuery):
    uid = int(call.data.split(":")[-1])
    u = await db.fetchone("SELECT is_banned FROM users WHERE id=%s", (uid,))
    if not u:
        return
    new = not bool(u["is_banned"])
    await set_banned(uid, new)
    await call.answer("Bloklandi" if new else "Blokdan chiqarildi")
    await cb_user_view(call)


@router.callback_query(F.data.startswith("ad:uadd:"))
async def cb_user_add_balance(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split(":")[-1])
    await state.update_data(balance_target=uid)
    await state.set_state(AdminStates.balance_add)
    await call.message.answer("💰 Qo'shiladigan summani kiriting (so'm):")


@router.message(AdminStates.balance_add, F.text)
async def msg_balance_add(message: Message, state: FSMContext):
    from bot.utils.misc import parse_amount
    data = await state.get_data()
    uid = int(data.get("balance_target", 0))
    await state.clear()
    amount = parse_amount(message.text)
    if amount <= 0:
        await message.answer("❗ Noto'g'ri summa")
        return
    new_bal = await wallet.add_balance(uid, amount, f"Admin qo'shdi ({message.from_user.id})")
    await message.answer(f"✅ Qo'shildi. Yangi balans: {money(new_bal)} so'm")
    u = await db.fetchone("SELECT * FROM users WHERE id=%s", (uid,))
    if u:
        text, ent = await render_user(u)
        await message.answer(text, entities=ent, reply_markup=kb.user_view_kb(uid, bool(u["is_banned"])))


@router.callback_query(F.data.startswith("ad:usub:"))
async def cb_user_sub_balance(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split(":")[-1])
    await state.update_data(balance_target=uid)
    await state.set_state(AdminStates.balance_sub)
    await call.message.answer("➖ Yechiladigan summani kiriting (so'm):")


@router.message(AdminStates.balance_sub, F.text)
async def msg_balance_sub(message: Message, state: FSMContext):
    from bot.utils.misc import parse_amount
    data = await state.get_data()
    uid = int(data.get("balance_target", 0))
    await state.clear()
    amount = parse_amount(message.text)
    if amount <= 0:
        await message.answer("❗ Noto'g'ri summa")
        return
    new_bal = await wallet.sub_balance(uid, amount, f"Admin yechdi ({message.from_user.id})")
    await message.answer(f"✅ Yechildi. Yangi balans: {money(new_bal)} so'm")
    u = await db.fetchone("SELECT * FROM users WHERE id=%s", (uid,))
    if u:
        text, ent = await render_user(u)
        await message.answer(text, entities=ent, reply_markup=kb.user_view_kb(uid, bool(u["is_banned"])))


@router.callback_query(F.data.startswith("ad:utx:"))
async def cb_user_tx(call: CallbackQuery):
    _, _, uid, page = call.data.split(":")
    page = int(page or 0)
    rows = await db.fetchall(
        "SELECT * FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT 10 OFFSET %s",
        (int(uid), page * 10),
    )
    lines = [f"{'{history}'} Tranzaksiyalar — {uid} (sahifa {page + 1}):"]
    if not rows:
        lines.append("{info} Bo'sh")
    for r in rows:
        lines.append(
            f"#{r['id']} {r['type']} · {r['amount']} so'm · balans {r['balance_after']} · "
            f"{fmt_dt(r['created_at'])}"
        )
    text, ent = render("\n".join(lines))
    await call.message.edit_text(text, entities=ent, reply_markup=kb.back_kb())


@router.callback_query(F.data.startswith("ad:uref:"))
async def cb_user_refs(call: CallbackQuery):
    uid = int(call.data.split(":")[-1])
    refs = await referral_list(uid, 20)
    lines = [f"{'{ref}'} Referallar — {uid}:"]
    if not refs:
        lines.append("{info} Yo'q")
    for r in refs:
        lines.append(f"👤 {r['first_name'] or r['username']} ({r['id']}) · {fmt_dt(r['created_at'])}")
    text, ent = render("\n".join(lines))
    await call.message.edit_text(text, entities=ent, reply_markup=kb.back_kb())
