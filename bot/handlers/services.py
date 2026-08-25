"""Xizmat handlerlari: Stars, Premium, NFT, Gift, Postga stars."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from bot import keyboards as kb
from bot.keyboards import M_MAIN
from bot.services import orders
from bot.services.orders import OrderError
from bot.states import UserStates
from bot.texts import clean_username, money, render

router = Router(name="user_services")
log = logging.getLogger("svc")


async def balance_of(user_id: int) -> float:
    return float(await db.fetchval("SELECT balance FROM users WHERE id=%s", (user_id,), 0) or 0)


# ══════════════════════════════════════════════════════════════
#  XIZMAT MENYU
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "svc:menu")
async def cb_services_menu(call: CallbackQuery):
    enabled = await db.get_setting_json("services_enabled", {})
    text, ent = render(
        f"{'{rocket}'} Xizmatlar bo'limi\n\n{'{spark}'} Kerakli xizmatni tanlang:"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.services_menu(enabled or {}))


# ══════════════════════════════════════════════════════════════
#  STARS
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "svc:stars")
async def cb_stars(call: CallbackQuery):
    packages = await db.get_setting_json("stars_packages", [])
    bal = await balance_of(call.from_user.id)
    text, ent = render(
        f"{'{star}'} Telegram Stars olish\n\n"
        f"{'{doc}'} Miqdor tanlang va oluvchining username'sini yuborasiz.\n"
        f"{'{star}'} Minimal: {await db.get_setting('stars_min', '50')} ⭐\n\n"
        f"{'{wallet}'} Sizning balansingiz: {money(bal)} so'm"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.stars_menu(packages or []))


@router.callback_query(F.data.startswith("st:pkg:"))
async def cb_stars_pkg(call: CallbackQuery, state: FSMContext):
    amount = int(call.data.split(":")[-1])
    price = await orders.stars_price(amount)
    await state.update_data(stars_amount=amount)
    await state.set_state(UserStates.stars_username)
    text, ent = render(
        f"{'{star}'} {amount} ta star tanlandi\n"
        f"{'{money}'} Narxi: {money(price)} so'm\n\n"
        f"{'{edit}'} Endi oluvchining Telegram username'sini yuboring:\n"
        f"Masalan: @username yoki https://t.me/username"
    )
    await call.message.edit_text(text, entities=ent)


@router.callback_query(F.data == "st:cust")
async def cb_stars_custom(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.stars_custom)
    min_star = int(await db.get_setting("stars_min", "50"))
    text, ent = render(
        f"{'{edit}'} Nechta star kerak?\n"
        f"{'{info}'} Minimal {min_star} ta: {min_star} dan boshlab istalgan miqdor."
    )
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.stars_custom, F.text)
async def msg_stars_custom(message: Message, state: FSMContext):
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer("❗ Iltimos, faqat raqam yuboring. Masalan: 250")
        return
    amount = int(raw)
    min_star = int(await db.get_setting("stars_min", "50"))
    if amount < min_star:
        await message.answer(f"❗ Minimal {min_star} ta star kiritish mumkin")
        return
    await state.update_data(stars_amount=amount)
    await state.set_state(UserStates.stars_username)
    await message.answer("📨 Endi oluvchining username'sini yuboring: @username yoki t.me/username")


@router.message(UserStates.stars_username, F.text)
async def msg_stars_username(message: Message, state: FSMContext):
    username = clean_username(message.text)
    if not username:
        await message.answer("❗ Username formati noto'g'ri. Masalan: @durov yoki https://t.me/durov")
        return
    data = await state.get_data()
    amount = int(data.get("stars_amount", 0))
    await state.update_data(stars_username=username)
    price = await orders.stars_price(amount)
    text, ent = render(
        f"{'{doc}'} Buyurtma tekshiruvi\n\n"
        f"{'{star}'} Stars: {amount} ta\n"
        f"{'{user}'} Oluvchi: @{username}\n"
        f"{'{money}'} Narx: {money(price)} so'm\n\n"
        f"{'{check}'} Tasdiqlaysizmi?"
    )
    await message.answer(text, entities=ent, reply_markup=kb.confirm_kb(f"st:ok:{amount}"))


@router.callback_query(F.data.startswith("st:ok:"))
async def cb_stars_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = int(data.get("stars_amount", 0))
    username = data.get("stars_username")
    await state.clear()
    if not username or not amount:
        await call.answer("Sessiya tugagan, qaytadan boshlang")
        return
    await call.answer("Buyurtma yuborilmoqda...")
    try:
        order = await orders.order_stars(call.from_user.id, username, amount)
        text, ent = render(
            f"{'{check}'} Stars muvaffaqiyatli yuborildi!\n\n"
            f"{'{orders}'} Buyurtma: #{order['id']}\n"
            f"{'{star}'} Miqdor: {amount} ⭐\n"
            f"{'{user}'} Oluvchi: @{username}\n"
            f"{'{money}'} Narx: {money(order['price'])} so'm\n"
            f"{'{spark}'} Xizmat hisobidan qo'shildi!"
        )
        await call.message.edit_text(text, entities=ent)
    except OrderError as e:
        await call.message.edit_text(f"❌ Xatolik: {e.message}", reply_markup=kb.back(M_MAIN))


# ══════════════════════════════════════════════════════════════
#  PREMIUM
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "svc:premium")
async def cb_premium(call: CallbackQuery):
    prices = await db.get_settings(["premium_3", "premium_6", "premium_12"])
    bal = await balance_of(call.from_user.id)
    text, ent = render(
        f"{'{premium}'} Telegram Premium olish\n\n"
        f"{'{doc}'} Muddatni tanlang, so'ng oluvchi username'sini yuborasiz.\n\n"
        f"{'{wallet}'} Balansingiz: {money(bal)} so'm"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.premium_menu(prices))


@router.callback_query(F.data.regexp(r"^pm:(3|6|12)$"))
async def cb_premium_duration(call: CallbackQuery, state: FSMContext):
    duration = int(call.data.split(":")[1])
    if duration not in (3, 6, 12):
        await call.answer("Noto'g'ri muddat")
        return
    await state.update_data(premium_duration=duration)
    await state.set_state(UserStates.premium_username)
    text, ent = render(
        f"{'{edit}'} {duration} oylik Premium tanlandi.\n"
        f"Oluvchining username'sini yuboring: @username yoki t.me/username"
    )
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.premium_username, F.text)
async def msg_premium_username(message: Message, state: FSMContext):
    username = clean_username(message.text)
    if not username:
        await message.answer("❗ Username formati noto'g'ri")
        return
    data = await state.get_data()
    duration = int(data.get("premium_duration", 3))
    await state.update_data(premium_username=username)
    price = float(await db.get_setting(f"premium_{duration}", "0"))
    text, ent = render(
        f"{'{doc}'} Buyurtma tekshiruvi\n\n"
        f"{'{premium}'} Muddat: {duration} oy\n"
        f"{'{user}'} Oluvchi: @{username}\n"
        f"{'{money}'} Narx: {money(price)} so'm\n\n"
        f"{'{check}'} Tasdiqlaysizmi?"
    )
    await message.answer(text, entities=ent, reply_markup=kb.confirm_kb(f"pm:ok:{duration}"))


@router.callback_query(F.data.startswith("pm:ok:"))
async def cb_premium_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    duration = int(data.get("premium_duration", 0))
    username = data.get("premium_username")
    await state.clear()
    if not username or not duration:
        await call.answer("Sessiya tugagan, qaytadan boshlang")
        return
    await call.answer("Buyurtma yuborilmoqda...")
    try:
        order = await orders.order_premium(call.from_user.id, username, duration)
        text, ent = render(
            f"{'{check}'} Premium muvaffaqiyatli yuborildi!\n\n"
            f"{'{orders}'} Buyurtma: #{order['id']}\n"
            f"{'{premium}'} Muddat: {duration} oy\n"
            f"{'{user}'} Oluvchi: @{username}\n"
            f"{'{money}'} Narx: {money(order['price'])} so'm"
        )
        await call.message.edit_text(text, entities=ent)
    except OrderError as e:
        await call.message.edit_text(f"❌ Xatolik: {e.message}", reply_markup=kb.back(M_MAIN))


# ══════════════════════════════════════════════════════════════
#  NFT
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "svc:nft")
async def cb_nft(call: CallbackQuery):
    price = await db.get_setting("nft_price", "0")
    bal = await balance_of(call.from_user.id)
    text, ent = render(
        f"{'{nft}'} NFT olish\n\n"
        f"{'{doc}'} Fragment NFT (username / anonym raqam) sotib olish.\n"
        f"Buyurtma admin tomonidan tekshirilib bajariladi.\n\n"
        f"{'{money}'} Narx: {money(price)} so'm\n"
        f"{'{wallet}'} Balansingiz: {money(bal)} so'm"
    )
    await call.message.edit_text(
        text, entities=ent,
        reply_markup=kb.confirm_kb("nt:start", f"{M_MAIN}"),
    )


@router.callback_query(F.data == "nt:start")
async def cb_nft_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.nft_target)
    text, ent = render(
        f"{'{edit}'} Qaysi NFT kerak?\n"
        f"Havola yoki nomini yuboring:\n"
        f"Masalan: t.me/username, @username yoki raqam: +998901234567"
    )
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.nft_target, F.text)
async def msg_nft_target(message: Message, state: FSMContext):
    target = message.text.strip()
    if len(target) < 4:
        await message.answer("❗ Havola juda qisqa")
        return
    await state.update_data(nft_target=target)
    price = await db.get_setting("nft_price", "0")
    text, ent = render(
        f"{'{doc}'} Buyurtma tekshiruvi\n\n"
        f"{'{nft}'} Ob'ekt: {target}\n"
        f"{'{money}'} Narx: {money(price)} so'm\n\n"
        f"Buyurtma admin tasdig'i bilan bajariladi. Tasdiqlaysizmi?"
    )
    await message.answer(text, entities=ent, reply_markup=kb.confirm_kb("nt:ok"))


@router.callback_query(F.data == "nt:ok")
async def cb_nft_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target = data.get("nft_target")
    await state.clear()
    if not target:
        await call.answer("Sessiya tugagan")
        return
    await call.answer("Buyurtma yaratilmoqda...")
    try:
        order = await orders.order_nft(call.from_user.id, target)
        text, ent = render(
            f"{'{check}'} Buyurtma qabul qilindi!\n\n"
            f"{'{orders}'} Buyurtma: #{order['id']}\n"
            f"{'{nft}'} Ob'ekt: {target}\n"
            f"{'{money}'} Narx: {money(order['price'])} so'm\n\n"
            f"{'{clock}'} Admin tez orada bajaradi. Buyurtmalar bo'limidan kuzating."
        )
        await call.message.edit_text(text, entities=ent)
    except OrderError as e:
        await call.message.edit_text(f"❌ Xatolik: {e.message}", reply_markup=kb.back(M_MAIN))


# ══════════════════════════════════════════════════════════════
#  GIFT
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "svc:gift")
async def cb_gift(call: CallbackQuery):
    price = await db.get_setting("gift_price", "0")
    name = await db.get_setting("gift_name", "Sovg'a")
    bal = await balance_of(call.from_user.id)
    text, ent = render(
        f"{'{gift}'} Gift yuborish\n\n"
        f"{'{doc}'} Tanlangan sovg'a: {name}\n"
        f"Sovg'a Telegram hisobi orqali yuboriladi.\n\n"
        f"{'{money}'} Narx: {money(price)} so'm\n"
        f"{'{wallet}'} Balansingiz: {money(bal)} so'm"
    )
    await call.message.edit_text(
        text, entities=ent, reply_markup=kb.confirm_kb("gf:start", f"{M_MAIN}")
    )


@router.callback_query(F.data == "gf:start")
async def cb_gift_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.gift_username)
    text, ent = render(
        f"{'{edit}'} Sovg'a kimga yuboriladi?\n"
        f"Oluvchining username'sini yuboring: @username yoki t.me/username"
    )
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.gift_username, F.text)
async def msg_gift_username(message: Message, state: FSMContext):
    username = clean_username(message.text)
    if not username:
        await message.answer("❗ Username formati noto'g'ri")
        return
    await state.update_data(gift_username=username)
    price = await db.get_setting("gift_price", "0")
    gift_name = await db.get_setting("gift_name", "Sovg'a")
    text, ent = render(
        f"{'{doc}'} Buyurtma tekshiruvi\n\n"
        f"{'{gift}'} Gift: {gift_name}\n"
        f"{'{user}'} Oluvchi: @{username}\n"
        f"{'{money}'} Narx: {money(price)} so'm\n\n"
        f"{'{check}'} Tasdiqlaysizmi?"
    )
    await message.answer(text, entities=ent, reply_markup=kb.confirm_kb("gf:ok"))


@router.callback_query(F.data == "gf:ok")
async def cb_gift_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = data.get("gift_username")
    await state.clear()
    if not username:
        await call.answer("Sessiya tugagan")
        return
    await call.answer("Gift yuborilmoqda...")
    try:
        order = await orders.order_gift(call.from_user.id, username)
        text, ent = render(
            f"{'{check}'} Gift muvaffaqiyatli yuborildi!\n\n"
            f"{'{orders}'} Buyurtma: #{order['id']}\n"
            f"{'{user}'} Oluvchi: @{username}"
        )
        await call.message.edit_text(text, entities=ent)
    except OrderError as e:
        await call.message.edit_text(f"❌ Xatolik: {e.message}", reply_markup=kb.back(M_MAIN))


# ══════════════════════════════════════════════════════════════
#  POSTGA STARS (paid reaction)
# ══════════════════════════════════════════════════════════════
@router.callback_query(F.data == "svc:reaction")
async def cb_reaction(call: CallbackQuery):
    rate = await db.get_setting("reaction_price_per_star", "300")
    min_s = await db.get_setting("reaction_min_stars", "1")
    max_s = await db.get_setting("reaction_max_stars", "25")
    bal = await balance_of(call.from_user.id)
    text, ent = render(
        f"{'{fire}'} Postga stars bosish\n\n"
        f"{'{doc}'} Kanal postiga hisob orqali paid reaction (star reaction) bosiladi.\n"
        f"Postga {min_s}..{max_s} ta star bosish mumkin.\n"
        f"Har bir star: {money(rate)} so'm\n\n"
        f"{'{wallet}'} Balansingiz: {money(bal)} so'm"
    )
    await call.message.edit_text(
        text, entities=ent, reply_markup=kb.confirm_kb("rc:start", f"{M_MAIN}")
    )


@router.callback_query(F.data == "rc:start")
async def cb_reaction_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.reaction_link)
    text, ent = render(
        f"{'{edit}'} Post havolasini yuboring:\n"
        f"Masalan: https://t.me/kanal_username/123"
    )
    await call.message.edit_text(text, entities=ent)


@router.message(UserStates.reaction_link, F.text)
async def msg_reaction_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if "t.me/" not in link:
        await message.answer("❗ Havola t.me/ ... ko'rinishida bo'lishi kerak")
        return
    await state.update_data(reaction_link=link)
    min_s = int(await db.get_setting("reaction_min_stars", "1"))
    max_s = int(await db.get_setting("reaction_max_stars", "25"))
    text, ent = render(
        f"{'{fire}'} Nechta star bosamiz?\n\n"
        f"{'{link}'} Post: {link}"
    )
    await message.answer(text, entities=ent, reply_markup=kb.reaction_counts(min_s, max_s))


@router.callback_query(F.data.startswith("rc:c:"))
async def cb_reaction_count(call: CallbackQuery, state: FSMContext):
    count = int(call.data.split(":")[-1])
    await state.update_data(reaction_stars=count)
    data = await state.get_data()
    link = data.get("reaction_link", "")
    price = await orders.reaction_price(count)
    text, ent = render(
        f"{'{doc}'} Tekshiruv\n\n"
        f"{'{fire}'} Stars: {count} ta\n"
        f"{'{money}'} Narx: {money(price)} so'm\n\n"
        f"{'{check}'} Tasdiqlaysizmi?"
    )
    await call.message.edit_text(text, entities=ent, reply_markup=kb.reaction_confirm(count, link))


@router.callback_query(F.data.startswith("rc:ok:"))
async def cb_reaction_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    count = int(data.get("reaction_stars", 0))
    link = data.get("reaction_link", "")
    await state.clear()
    if not count or not link:
        await call.answer("Sessiya tugagan")
        return
    await call.answer("Reaksiya yuborilmoqda...")
    try:
        order = await orders.order_reaction(call.from_user.id, link, count)
        text, ent = render(
            f"{'{check}'} Paid reaction muvaffaqiyatli bosildi!\n\n"
            f"{'{orders}'} Buyurtma: #{order['id']}\n"
            f"{'{fire}'} Stars: {count} ta\n"
            f"📎 Post: {link}"
        )
        await call.message.edit_text(text, entities=ent)
    except OrderError as e:
        await call.message.edit_text(f"❌ Xatolik: {e.message}", reply_markup=kb.back(M_MAIN))
