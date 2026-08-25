"""Asosiy handlerlar: /start, asosiy menyu, referal, FAQ, kanal."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

import db
from bot import keyboards as kb
from bot.keyboards import M_MAIN
from bot.services.users import count_referrals, is_admin
from bot.texts import money, render

router = Router(name="base")
log = logging.getLogger("base")


async def show_menu(obj, admin_flag: bool = False, edit: bool = False) -> None:
    chat_id = obj.message.chat.id if isinstance(obj, CallbackQuery) else obj.chat.id
    balance = await db.fetchval("SELECT balance FROM users WHERE id=%s", (obj.from_user.id,), 0)
    text, entities = render(
        f"{'{home}'} Asosiy menyu\n\n"
        f"{'{wallet}'} Balansingiz: {money(balance)} so'm\n\n"
        f"{'{spark}'} Quyidagi bo'limlardan birini tanlang:"
    )
    markup = kb.main_menu(admin_flag)
    if isinstance(obj, CallbackQuery):
        try:
            await obj.message.edit_text(text, entities=entities, reply_markup=markup)
            return
        except Exception:
            pass
        await obj.message.answer(text, entities=entities, reply_markup=markup)
    else:
        await obj.answer(text, entities=entities, reply_markup=markup)


@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome = await db.get_setting("welcome_text")
    name = message.from_user.first_name or "dost"
    welcome = welcome.replace("{name}", name).replace("{username}", f"@{message.from_user.username or name}")
    text, entities = render(welcome + "\n\n" + "{spark}")
    admin_flag = await is_admin(message.from_user.id)
    await message.answer(text, entities=entities, reply_markup=kb.main_menu(admin_flag))


@router.callback_query(F.data == M_MAIN)
async def cb_main(call: CallbackQuery):
    admin_flag = await is_admin(call.from_user.id)
    await show_menu(call, admin_flag, edit=True)


@router.callback_query(F.data == "m:ref")
async def cb_ref(call: CallbackQuery):
    bot_me = await call.bot.get_me()
    link = f"https://t.me/{bot_me.username}?start={call.from_user.id}"
    cnt = await count_referrals(call.from_user.id)
    percent = await db.get_setting("referral_percent", "5")
    enabled = await db.get_setting("referral_enabled", "1")
    state = "Faol" if enabled == "1" else "O'chirilgan"
    text, entities = render(
        f"{'{ref}'} Referal dastur\n\n"
        f"{'{user}'} Taklif qilganlar: {cnt} ta\n"
        f"{'{coin}'} Bonus: xaridning {percent}% i\n"
        f"{'{gear}'} Holat: {state}\n\n"
        f"{'{link}'} Sizning havolangiz:\n{link}\n\n"
        f"{'{spark}'} Do'stlaringizga yuboring va daromad oling!"
    )
    await call.message.edit_text(text, entities=entities, reply_markup=kb.referal_kb())


@router.callback_query(F.data == "m:faq")
async def cb_faq(call: CallbackQuery):
    faq = await db.get_setting("faq_text")
    text, entities = render(faq)
    await call.message.edit_text(text, entities=entities, reply_markup=kb.support_kb())


@router.callback_query(F.data == "m:channel")
async def cb_channel(call: CallbackQuery):
    link = await db.get_setting("channel_link", "")
    if link:
        text, entities = render(f"{'{chat}'} Rasmiy kanalimiz:\n{link}")
        await call.message.edit_text(text, entities=entities, reply_markup=kb.back(M_MAIN))
    else:
        text, entities = render("{warn} Kanal hali qo'shilmagan")
        await call.message.edit_text(text, entities=entities, reply_markup=kb.back(M_MAIN))
