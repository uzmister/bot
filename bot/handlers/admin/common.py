"""Admin — yagona FSM qiymat kiritish (setting_value) handleri."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from bot.handlers.admin import protect
from bot.states import AdminStates

router = Router(name="admin_common")
protect(router)
log = logging.getLogger("admin_common")

NUMERIC_KEYS = {
    "nft_price", "gift_price", "premium_3", "premium_6", "premium_12",
    "min_deposit", "min_withdraw", "reaction_price_per_star", "reaction_min_stars",
    "reaction_max_stars", "stars_rate", "stars_min", "referral_percent",
    "spider_server",
}


@router.message(AdminStates.setting_value, F.text)
async def msg_setting_value(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("skey", "")
    value = message.text.strip()

    # ── Custom emoji ─────────────────────────────────────────
    if key.startswith("_emoji:"):
        emoji_key = key.split(":", 1)[1]
        await state.clear()
        ids = await db.get_setting_json("emoji_ids", {}) or {}
        if value in ("0", "-", "delete"):
            ids.pop(emoji_key, None)
        else:
            digits = "".join(c for c in value if c.isdigit())
            if len(digits) < 5:
                await message.answer("❗ Custom emoji ID raqam bo'lishi kerak (masalan 5368324170671202286)")
                return
            ids[emoji_key] = digits
        await db.set_setting_json("emoji_ids", ids)
        from bot.emoji import reload_emojis
        await reload_emojis()
        await message.answer(f"✅ {emoji_key} emoji saqlandi")
        return

    # ── Stars paket qo'shish ─────────────────────────────────
    if key == "_pkg_amount":
        v = value.replace(" ", "")
        if not v.isdigit():
            await message.answer("❗ Raqam kiriting")
            return
        await state.update_data(pkg_amount=int(v), skey="_pkg_price")
        await message.answer("💵 Paket narxini kiriting (so'm):")
        return

    if key == "_pkg_price":
        from bot.utils.misc import parse_amount
        price = parse_amount(value)
        amount = int(data.get("pkg_amount", 0))
        if price <= 0 or amount <= 0:
            await message.answer("❗ Noto'g'ri qiymat")
            return
        packages = await db.get_setting_json("stars_packages", [])
        packages = [p for p in (packages or []) if int(p.get("amount", 0)) != amount]
        packages.append({"amount": amount, "price": price})
        packages.sort(key=lambda p: int(p["amount"]))
        await db.set_setting_json("stars_packages", packages)
        await state.clear()
        await message.answer(f"✅ Paket saqlandi: {amount} ⭐ = {price} so'm")
        return

    # ── NFT natijasi (admin bajardi) ─────────────────────────
    if key.startswith("_nft_result:"):
        from bot.handlers.admin.orders import finish_nft
        await state.clear()
        await finish_nft(message, int(key.split(":", 1)[1]), value)
        return

    # ── Murojaatga javob ─────────────────────────────────────
    if key.startswith("_ticket_reply:"):
        from bot.handlers.admin.orders import answer_ticket
        await state.clear()
        await answer_ticket(message, int(key.split(":", 1)[1]), value)
        return

    # ── Reklama (broadcast) ─────────────────────────────────
    if key == "_broadcast":
        from bot.handlers.admin.orders import do_broadcast
        await state.clear()
        await do_broadcast(message, value)
        return

    # ── Umumiy sozlama ───────────────────────────────────────
    await state.clear()
    if not key:
        await message.answer("❗ Xatolik, qaytadan boshlang")
        return
    if key in NUMERIC_KEYS:
        try:
            float(value)
        except ValueError:
            await message.answer("❗ Raqam kiritilishi kerak")
            return
    await db.set_setting(key, value)
    await message.answer(f"✅ Saqlandi: {key} = {value[:120]}")
