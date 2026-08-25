"""Admin — tizim sozlamalari, matnlar, emojilar, fragment/spider API."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton as B
from aiogram.types import InlineKeyboardMarkup as K
from aiogram.types import Message

import db
from bot.emoji import FALLBACK, reload_emojis
from bot.handlers.admin import kb, protect
from bot.states import AdminStates
from bot.texts import render

router = Router(name="admin_settings")
protect(router)

EMOJI_KEYS = [
    "star", "premium", "nft", "gift", "fire", "phone", "money", "wallet",
    "ref", "support", "admin", "orders", "back", "check", "cross", "warn",
    "info", "card", "bank", "server", "code", "gear", "history", "bolt",
]


@router.callback_query(F.data == "ad:cfg")
async def cb_cfg(call: CallbackQuery):
    ann = await db.get_setting("announcement", "")
    ann_show = ann[:80] if ann else "Yo'q"
    text, ent = render(
        "{'gear'} Tizim sozlamalari\n\n"
        f"{'{megaphone}'} E'lon: {ann_show}\n\n"
        "{'spark'} Bo'limni tanlang:"
    )
    rows = [
        [B(f"{'{edit}'} Salomlashuv matni", callback_data="ad:v:welcome_text"),
         B(f"{'{info}'} FAQ", callback_data="ad:v:faq_text")],
        [B(f"{'{link}'} Kanal havolasi", callback_data="ad:v:channel_link"),
         B(f"{'{link}'} Kanal username", callback_data="ad:v:channel_username")],
        [B(f"{'{support}'} Yordam havolasi", callback_data="ad:v:support_link"),
         B(f"{'{megaphone}'} E'lon", callback_data="ad:ann")],
        [B(f"{'{spark}'} Emojilar", callback_data="ad:emj"),
         B(f"{'{rocket}'} Fragment API", callback_data="ad:frag")],
        [B(f"{'{server}'} Spider API", callback_data="ad:spr")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:main")],
    ]
    await call.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))


@router.callback_query(F.data == "ad:ann")
async def cb_announcement(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.setting_value)
    await state.update_data(skey="announcement")
    await call.message.answer("📣 Yangi e'lon matnini yuboring (bo'sh qoldirsangiz o'chiriladi):")


# ── Emojilar ─────────────────────────────────────────────────
@router.callback_query(F.data == "ad:emj")
async def cb_emojis(call: CallbackQuery):
    ids = await db.get_setting_json("emoji_ids", {})
    ids = ids or {}
    rows = []
    for key in EMOJI_KEYS:
        mark = "✅" if ids.get(key) else "❌"
        rows.append([B(f"{mark} {FALLBACK.get(key, '')} {key}", callback_data=f"ad:emj:{key}")])
    rows.append([B(f"{'{back}'} Orqaga", callback_data="ad:cfg")])
    text, ent = render(
        "{'spark'} Custom emoji sozlamalari\n\n"
        "{'info'} Haqiqiy custom emoji ID (raqam) kiriting — matnlarda chiroyli "
        "custom emoji ko'rinadi. Bo'sh bo'lsa oddiy emoji ishlatiladi.\n\n"
        "{'warn'} ID olish: premium akkauntdan emojini xabar sifatida yuboring, "
        "yoki @CustomEmojiBot dan foydalaning. ID = document_id."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))


@router.callback_query(F.data.startswith("ad:emj:"))
async def cb_emoji_set(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[-1]
    if key not in FALLBACK:
        return
    await state.set_state(AdminStates.setting_value)
    await state.update_data(skey=f"_emoji:{key}")
    text, ent = render(
        f"{'{edit}'} {key} uchun custom emoji ID kiriting.\n"
        f"O'chirish uchun — yuboring: 0"
    )
    await call.message.answer(text, entities=ent)
    await call.answer()


# Emoji qiymatini kiritish — bot.handlers.admin.services.msg_set_value da
# birlashtirilgan (skey="_emoji:{key}").


# ── Fragment API ─────────────────────────────────────────────
@router.callback_query(F.data == "ad:frag")
async def cb_fragment(call: CallbackQuery):
    base = await db.get_setting("fragment_api_base", "https://fragment-api.net")
    ver = await db.get_setting("fragment_api_version", "v1")
    seed = await db.get_setting("fragment_seed", "")
    cookies = await db.get_setting("fragment_cookies", "")
    api_key = await db.get_setting("fragment_api_key", "")
    seed_ok = "✔ kiritilgan" if seed else "✖ yo'q"
    cookies_ok = "✔ kiritilgan" if cookies else "✖ yo'q"
    key_ok = "✔ kiritilgan" if api_key else "✖ yo'q"
    text, ent = render(
        f"{'{rocket}'} Fragment API\n\n"
        f"{'{server}'} Server: {base}\n"
        f"{'{gear}'} Rejim: {ver.upper()}\n"
        f"{'{key}'} seed: {seed_ok}\n"
        f"🍪 cookies: {cookies_ok}\n"
        f"{'{lock}'} auth_key: {key_ok}\n\n"
        f"{'{info}'} v1 — buyStarsWithoutKYC/buyPremiumWithoutKYC; v2 — create+pay oqimi."
    )
    rows = [
        [B(f"Rejim: {ver.upper()}", callback_data="ad:fragver")],
        [B("✏️ seed", callback_data="ad:v:fragment_seed"),
         B("🍪 cookies", callback_data="ad:v:fragment_cookies")],
        [B("✏️ base", callback_data="ad:v:fragment_api_base"),
         B("✏️ auth_key", callback_data="ad:v:fragment_api_key")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:cfg")],
    ]
    await call.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))


@router.callback_query(F.data == "ad:fragver")
async def cb_fragment_version(call: CallbackQuery):
    cur = await db.get_setting("fragment_api_version", "v1")
    await db.set_setting("fragment_api_version", "v2" if cur == "v1" else "v1")
    await call.answer("Rejim almashtirildi")
    await cb_fragment(call)


# ── Spider API ───────────────────────────────────────────────
@router.callback_query(F.data == "ad:spr")
async def cb_spider(call: CallbackQuery):
    key = await db.get_setting("spider_api_key", "")
    url = await db.get_setting("spider_api_url", "https://api.spider-service.com")
    server = await db.get_setting("spider_server", "1")
    key_ok = "✔ kiritilgan" if key else "✖ yo'q"
    text, ent = render(
        f"{'{server}'} Spider API (Server 1)\n\n"
        f"{'{lock}'} API key: {key_ok}\n"
        f"URL: {url}\n"
        f"{'{gear}'} server raqami: {server}\n\n"
        f"{'{info}'} Kalit olish: @S_PIDERRBot → API Key → Show Key"
    )
    rows = [
        [B("✏️ API key", callback_data="ad:v:spider_api_key"),
         B("✏️ server raqami", callback_data="ad:v:spider_server")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:cfg")],
    ]
    await call.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))
