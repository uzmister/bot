"""Murojaat (ticket) handlerlari."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import config
import db
from bot import keyboards as kb
from bot.keyboards import M_MAIN
from bot.states import UserStates
from bot.texts import render

router = Router(name="support")
log = logging.getLogger("support")


@router.callback_query(F.data == "sp:new")
async def cb_support_new(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.support_text)
    text, ent = render(
        f"{'{support}'} Murojaat bo'limi\n\n"
        f"{'{edit}'} Muammoingizni yoki taklifingizni yozing.\n"
        f"Admin tez orada javob beradi."
    )
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.support_text, F.text)
async def msg_support(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.clear()
    if len(text) < 5:
        await message.answer("❗ Xabar juda qisqa")
        return
    ticket_id = await db.execute(
        "INSERT INTO tickets (user_id, subject, message) VALUES (%s,%s,%s)",
        (message.from_user.id, text[:100], text),
    )
    ok, ent = render(
        f"{'{check}'} Murojaatingiz qabul qilindi!\n\n"
        f"{'{orders}'} Raqam: #{ticket_id}\n"
        f"{'{clock}'} Tez orada javob olasiz."
    )
    await message.answer(ok, entities=ent, reply_markup=kb.back(M_MAIN))

    # Adminlarga xabar
    for admin_id in config.ADMIN_IDS:
        try:
            alarm, ent2 = render(
                f"{'{bell}'} Yangi murojaat #{ticket_id}\n\n"
                f"👤 Foydalanuvchi: {message.from_user.full_name} (ID: {message.from_user.id})\n"
                f"💬 Xabar: {text[:500]}"
            )
            await message.bot.send_message(admin_id, alarm, entities=ent2)
        except Exception as e:
            log.warning("Admin xabari yuborilmadi %s: %s", admin_id, e)
