"""Admin — Telegram hisoblar (Telethon sessiyalar) boshqaruvi."""
from __future__ import annotations

import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from bot.handlers.admin import kb, protect
from bot.states import AdminStates
from bot.texts import fmt_dt, normalize_phone, render
from bot.utils import tg_client
from bot.utils.tg_client import AccountError

router = Router(name="admin_accounts")
protect(router)

TYPE_LABEL = {
    "payment_uzcard": "UZCARD to'lov",
    "payment_humo": "HUMO to'lov",
    "reaction": "Reaksiya",
    "gift": "Gift",
}


@router.callback_query(F.data == "ad:acc")
async def cb_accounts_menu(call: CallbackQuery):
    text, ent = render(
        "{'key'} Telegram hisoblar (Telethon sessiyalar)\n\n"
        "{'info'} To'lov aniqlash, postga star bosish va gift yuborish uchun "
        "hisoblar kerak. Qo'shish: telefon raqam → login kod → (2FA)."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.accounts_menu())


@router.callback_query(F.data.startswith("ad:acc:"))
async def cb_acc_list(call: CallbackQuery):
    acc_type = call.data.split(":")[-1]
    if acc_type not in TYPE_LABEL:
        return
    accounts = await db.fetchall(
        "SELECT * FROM tg_accounts WHERE acc_type=%s ORDER BY id DESC", (acc_type,)
    )
    text, ent = render(
        f"{'{key}'} {TYPE_LABEL[acc_type]} hisoblar ({len(accounts)}):"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.acc_type_kb(acc_type, accounts))


@router.callback_query(F.data.startswith("ad:accadd:"))
async def cb_acc_add(call: CallbackQuery, state: FSMContext):
    acc_type = call.data.split(":")[-1]
    if acc_type not in TYPE_LABEL:
        return
    await state.update_data(acc_type=acc_type)
    await state.set_state(AdminStates.acc_phone)
    text, ent = render(
        f"{'{plus}'} Yangi hisob ({TYPE_LABEL[acc_type]})\n\n"
        f"{'{edit}'} Telefon raqamini yuboring:\nMasalan: +998901234567"
    )
    await call.message.answer(text, entities=ent)


@router.message(AdminStates.acc_phone, F.text)
async def msg_acc_phone(message: Message, state: FSMContext):
    phone = normalize_phone(message.text)
    if len(phone) < 10:
        await message.answer("❗ Telefon raqami noto'g'ri")
        return
    phone = "+" + phone
    await state.update_data(acc_phone=phone)
    try:
        result = await tg_client.start_login(phone)
    except AccountError as e:
        await message.answer(f"❌ {e}")
        return
    except Exception as e:
        await message.answer(f"❌ Ulanish xatosi: {e}")
        return
    if result["status"] == "already":
        await state.set_state(AdminStates.acc_name)
        await message.answer("✅ Hisob allaqachon avtorizatsiyalangan. Nomini kiriting:")
        return
    await state.update_data(phone_code_hash=result["phone_code_hash"])
    await state.set_state(AdminStates.acc_code)
    await message.answer("🔐 Telegramdan kelgan login kodni kiriting (faqat raqam):")


@router.message(AdminStates.acc_code, F.text)
async def msg_acc_code(message: Message, state: FSMContext):
    code = "".join(c for c in message.text if c.isdigit())
    if len(code) < 3:
        await message.answer("❗ Kod raqam bo'lishi kerak")
        return
    data = await state.get_data()
    phone = data.get("acc_phone", "")
    phash = data.get("phone_code_hash", "")
    try:
        result = await tg_client.submit_code(phone, code, phash)
    except AccountError as e:
        await message.answer(f"❌ {e}")
        return
    if result["status"] == "need_password":
        await state.set_state(AdminStates.acc_2fa)
        await message.answer("🔐 Hisobda 2FA parol yoqilgan. Parolni kiriting:")
        return
    await state.set_state(AdminStates.acc_name)
    await message.answer("✅ Kirildi! Hisobga nom bering (masalan: UZ-01):")


@router.message(AdminStates.acc_2fa, F.text)
async def msg_acc_2fa(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("acc_phone", "")
    try:
        await tg_client.submit_2fa(phone, message.text.strip())
    except AccountError as e:
        await message.answer(f"❌ {e}")
        return
    await state.update_data(acc_twofa=message.text.strip())
    await state.set_state(AdminStates.acc_name)
    await message.answer("✅ Kirildi! Hisobga nom bering:")


@router.message(AdminStates.acc_name, F.text)
async def msg_acc_name(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("acc_phone", "")
    acc_type = data.get("acc_type", "")
    name = message.text.strip()[:128]
    twofa = data.get("acc_twofa")
    await state.clear()

    # Mavjud bo'lsa yangilash
    existing = await db.fetchone(
        "SELECT id FROM tg_accounts WHERE phone=%s AND acc_type=%s", (phone, acc_type)
    )
    if existing:
        await db.execute(
            "UPDATE tg_accounts SET name=%s, twofa=%s, status='active', updated_at=NOW() "
            "WHERE id=%s",
            (name, twofa, existing["id"]),
        )
    else:
        session_file = tg_client.session_path(phone)
        await db.execute(
            "INSERT INTO tg_accounts (phone, name, acc_type, session_file, twofa) "
            "VALUES (%s,%s,%s,%s,%s)",
            (phone, name, acc_type, session_file, twofa),
        )
    await message.answer(
        f"✅ Hisob saqlandi: {phone}\n"
        f"Turi: {TYPE_LABEL.get(acc_type, acc_type)}\n"
        f"Sessiya fayli: {os.path.basename(tg_client.session_path(phone))}",
        reply_markup=kb.back_kb(),
    )


@router.callback_query(F.data.startswith("ad:accv:"))
async def cb_acc_view(call: CallbackQuery):
    aid = int(call.data.split(":")[-1])
    acc = await db.fetchone("SELECT * FROM tg_accounts WHERE id=%s", (aid,))
    if not acc:
        return
    text, ent = render(
        f"{'{key}'} Hisob #{acc['id']}\n\n"
        f"📱 Telefon: {acc['phone']}\n"
        f"👤 Nomi: {acc['name'] or '—'}\n"
        f"{'{box}'} Turi: {TYPE_LABEL.get(acc['acc_type'], acc['acc_type'])}\n"
        f"{'{gear}'} Holat: {acc['status']}\n"
        f"{'{check}'} Muvaffaqiyat: {acc['success_count']} ta\n"
        f"{'{calendar}'} Qo'shilgan: {fmt_dt(acc['created_at'])}\n"
        + (f"\n⚠️ Xato: {acc['last_error']}" if acc.get("last_error") else "")
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.acc_view_kb(acc))


@router.callback_query(F.data.startswith("ad:actg:"))
async def cb_acc_toggle(call: CallbackQuery):
    aid = int(call.data.split(":")[-1])
    acc = await db.fetchone("SELECT * FROM tg_accounts WHERE id=%s", (aid,))
    if not acc:
        return
    new_status = "disabled" if acc["status"] == "active" else "active"
    await db.execute(
        "UPDATE tg_accounts SET status=%s, updated_at=NOW() WHERE id=%s", (new_status, aid)
    )
    await call.answer("O'zgartirildi")
    await cb_acc_view(call)


@router.callback_query(F.data.startswith("ad:acdel:"))
async def cb_acc_delete(call: CallbackQuery):
    aid = int(call.data.split(":")[-1])
    acc = await db.fetchone("SELECT * FROM tg_accounts WHERE id=%s", (aid,))
    if acc:
        await tg_client.drop_client(acc["phone"], delete_session=True, session_file=acc["session_file"])
        await db.execute("DELETE FROM tg_accounts WHERE id=%s", (aid,))
    await call.answer("O'chirildi")
    await call.message.edit_text("🗑 Hisob o'chirildi", reply_markup=kb.back_kb())
