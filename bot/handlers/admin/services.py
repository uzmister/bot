"""Admin — xizmat narxlari va sozlamalari (qiymat kiritish: admin/common.py)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton as B
from aiogram.types import InlineKeyboardMarkup as K

import db
from bot.handlers.admin import kb, protect
from bot.states import AdminStates
from bot.texts import money, render

router = Router(name="admin_services")
protect(router)


@router.callback_query(F.data == "ad:svc")
async def cb_services(call: CallbackQuery):
    enabled = await db.get_setting_json("services_enabled", {})
    text, ent = render(
        "{'gear'} Xizmatlar: narxlar va holatlar.\n\n"
        "{'info'} Yashil — yoqilgan, qizil — o'chirilgan."
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.services_menu(enabled or {}))


@router.callback_query(F.data.startswith("ad:togsvc:"))
async def cb_toggle_service(call: CallbackQuery):
    key = call.data.split(":")[-1]
    enabled = await db.get_setting_json("services_enabled", {})
    enabled[key] = 0 if enabled.get(key, 1) else 1
    await db.set_setting_json("services_enabled", enabled)
    await call.answer("O'zgartirildi")
    await cb_services(call)


@router.callback_query(F.data.startswith("ad:tog:"))
async def cb_toggle_setting(call: CallbackQuery):
    key = call.data.split(":")[-1]
    cur = await db.get_setting(key, "1")
    await db.set_setting(key, "0" if cur == "1" else "1")
    await call.answer("O'zgartirildi")
    new_val = await db.get_setting(key, "1")
    if key == "watcher_enabled":
        status_txt = "Yoniq" if new_val == "1" else "O'chiq"
        text, ent = render(f"⚡️ Payment watcher: {status_txt}")
    else:
        text, ent = render(f"{'{check}'} O'zgartirildi ({key})")
    await call.message.edit_text(text, entities=ent, reply_markup=kb.back_kb())


@router.callback_query(F.data.startswith("ad:v:"))
async def cb_set_value(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[-1]
    current = await db.get_setting(key, "")
    await state.update_data(skey=key)
    await state.set_state(AdminStates.setting_value)
    text, ent = render(
        f"{'{edit}'} Yangi qiymatni kiriting.\n\n"
        f"{'{doc}'} Kalit: {key}\n"
        f"{'{info}'} Joriy: {current or '—'}"
    )
    await call.message.answer(text, entities=ent)
    await call.answer()


# ══════════════════════════════════════════════════════════════
#  STARS PAKETLAR
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "ad:svc:stars")
async def cb_stars_settings(call: CallbackQuery):
    packages = await db.get_setting_json("stars_packages", [])
    rate = await db.get_setting("stars_rate", "340")
    min_s = await db.get_setting("stars_min", "50")
    lines = [f"{'{star}'} Stars sozlamalari\n\n{'{doc}'} Paketlar:"]
    if not packages:
        lines.append("{warn} Paketlar yo'q")
    rows = []
    for p in packages or []:
        lines.append(f"• {p['amount']} ⭐ — {money(p['price'])} so'm")
        rows.append([B(f"🗑 {p['amount']} ⭐", callback_data=f"ad:pkgdel:{p['amount']}")])
    lines.append(f"\n{'{edit}'} Kustom narx: {rate} so'm/⭐ (min {min_s})")
    text, ent = render("\n".join(lines))
    rows.append([B("➕ Paket qo'shish", callback_data="ad:pkgadd")])
    rows.append([B("✏️ Kustom narx (stars_rate)", callback_data="ad:v:stars_rate")])
    rows.append([B("✏️ Minimal (stars_min)", callback_data="ad:v:stars_min")])
    rows.append([B(f"{'{back}'} Orqaga", callback_data="ad:svc")])
    await call.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))


@router.callback_query(F.data == "ad:pkgadd")
async def cb_pkg_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.setting_value)
    await state.update_data(skey="_pkg_amount")
    text, ent = render("{'edit'} Paket miqdorini kiriting (⭐):")
    await call.message.answer(text, entities=ent)


@router.callback_query(F.data.startswith("ad:pkgdel:"))
async def cb_pkg_delete(call: CallbackQuery):
    amount = int(call.data.split(":")[-1])
    packages = await db.get_setting_json("stars_packages", [])
    packages = [p for p in (packages or []) if int(p.get("amount", 0)) != amount]
    await db.set_setting_json("stars_packages", packages)
    await call.answer("O'chirildi")
    await cb_stars_settings(call)


# ══════════════════════════════════════════════════════════════
#  PREMIUM / GIFT / REACTION / REFERAL / WATCHER
# ══════════════════════════════════════════════════════════════
async def _edit(target: CallbackQuery, text: str, ent: list, rows: list[list[B]]) -> None:
    await target.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))


async def show_premium(target: CallbackQuery) -> None:
    p3 = await db.get_setting("premium_3", "0")
    p6 = await db.get_setting("premium_6", "0")
    p12 = await db.get_setting("premium_12", "0")
    text, ent = render(
        f"{'{premium}'} Premium narxlar\n\n"
        f"3 oy: {money(p3)} so'm\n"
        f"6 oy: {money(p6)} so'm\n"
        f"12 oy: {money(p12)} so'm"
    )
    rows = [
        [B("✏️ 3 oy", callback_data="ad:v:premium_3"),
         B("✏️ 6 oy", callback_data="ad:v:premium_6")],
        [B("✏️ 12 oy", callback_data="ad:v:premium_12")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:svc")],
    ]
    await _edit(target, text, ent, rows)


async def show_gift(target: CallbackQuery) -> None:
    price = await db.get_setting("gift_price", "0")
    gid = await db.get_setting("gift_id", "")
    name = await db.get_setting("gift_name", "Sovg'a")
    text, ent = render(
        f"{'{gift}'} Gift sozlamalari\n\n"
        f"{'{money}'} Narx: {money(price)} so'm\n"
        f"{'{key}'} Gift ID: {gid or '—'}\n"
        f"👤 Nomi: {name}"
    )
    rows = [
        [B("✏️ Gift ID", callback_data="ad:v:gift_id"),
         B("✏️ Nomi", callback_data="ad:v:gift_name")],
        [B("✏️ Narx", callback_data="ad:v:gift_price")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:svc")],
    ]
    await _edit(target, text, ent, rows)


async def show_reaction(target: CallbackQuery) -> None:
    rate = await db.get_setting("reaction_price_per_star", "300")
    mn = await db.get_setting("reaction_min_stars", "1")
    mx = await db.get_setting("reaction_max_stars", "25")
    text, ent = render(
        f"{'{fire}'} Reaksiya sozlamalari\n\n"
        f"{'{money}'} Narx: {money(rate)} so'm/⭐\n"
        f"{'{info}'} Chegara: {mn}..{mx} ⭐"
    )
    rows = [
        [B("✏️ Narx", callback_data="ad:v:reaction_price_per_star")],
        [B("✏️ Min", callback_data="ad:v:reaction_min_stars"),
         B("✏️ Max", callback_data="ad:v:reaction_max_stars")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:svc")],
    ]
    await _edit(target, text, ent, rows)


@router.callback_query(F.data == "ad:svc:premium")
async def cb_premium_settings(call: CallbackQuery):
    await show_premium(call)


@router.callback_query(F.data == "ad:svc:gift")
async def cb_gift_settings(call: CallbackQuery):
    await show_gift(call)


@router.callback_query(F.data == "ad:svc:reaction")
async def cb_reaction_settings(call: CallbackQuery):
    await show_reaction(call)


@router.callback_query(F.data == "ad:svc:referral")
async def cb_referral_settings(call: CallbackQuery):
    enabled = (await db.get_setting("referral_enabled", "1")) == "1"
    percent = await db.get_setting("referral_percent", "5")
    status_txt = "Yoniq" if enabled else "O'chiq"
    action_txt = "O'chirish" if enabled else "Yoqish"
    text, ent = render(
        f"{'{ref}'} Referal sozlamalari\n\n"
        f"{'{gear}'} Holat: {status_txt}\n"
        f"{'{coin}'} Bonus: xaridning {percent}% i"
    )
    rows = [
        [B(f"{'{off}' if enabled else '{on}'} {action_txt}",
           callback_data="ad:tog:referral_enabled")],
        [B("✏️ Foiz", callback_data="ad:v:referral_percent")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:svc")],
    ]
    await call.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))


@router.callback_query(F.data == "ad:svc:watcher")
async def cb_watcher_settings(call: CallbackQuery):
    enabled = (await db.get_setting("watcher_enabled", "1")) == "1"
    status_txt = "Yoniq" if enabled else "O'chiq"
    action_txt = "O'chirish" if enabled else "Yoqish"
    text, ent = render(
        f"{'{bolt}'} Payment watcher\n\n"
        f"{'{gear}'} Holat: {status_txt}\n\n"
        f"{'{info}'} Faol bo'lsa, CardXabarBot/HumocardBot xabarlari orqali to'lovlar "
        f"avtomatik tasdiqlanadi."
    )
    rows = [
        [B(f"{'{off}' if enabled else '{on}'} {action_txt}",
           callback_data="ad:tog:watcher_enabled")],
        [B(f"{'{back}'} Orqaga", callback_data="ad:svc")],
    ]
    await call.message.edit_text(text, entities=ent, reply_markup=K(inline_keyboard=rows))
