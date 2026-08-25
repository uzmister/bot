"""
Barcha inline klaviaturalar (callback_data prefikslari xuddi shu yerdagi
konstantalarga mos keladi — handlerlar shu prefikslarni o'qiydi).
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton as B
from aiogram.types import InlineKeyboardMarkup as K

from bot.emoji import FALLBACK as EMO

# ── Umumiy prefikslar ────────────────────────────────────────
M_MAIN = "m:main"
SVC = "svc"          # svc:stars | svc:premium | svc:nft | svc:gift | svc:reaction | svc:number
ST = "st"            # st:pkg:50 | st:cust
PM = "pm"            # pm:3 | pm:6 | pm:12
NT = "nt"            # nt:ok
GF = "gf"            # gf:ok
RC = "rc"            # rc:c:5 (count) | rc:ok:5
W = "w"              # w:topup | w:m:UZCARD | w:pay:UZCARD | w:4:UZCARD | w:n4:UZCARD | w:hist:0
N = "n"              # n:s1 | n:s2 | n:s1c:PS | n:s1b:PS | n:s1code:ID | n:s2b:ID
O = "o"              # o:list:0 | o:v:ID
SP = "sp"            # sp:new
AD = "ad"            # admin


def main_menu(is_admin: bool = False) -> K:
    rows = [
        [B(f"{EMO['star']} Stars olish", callback_data=f"{SVC}:stars"),
         B(f"{EMO['premium']} Premium", callback_data=f"{SVC}:premium")],
        [B(f"{EMO['nft']} NFT olish", callback_data=f"{SVC}:nft"),
         B(f"{EMO['gift']} Gift olish", callback_data=f"{SVC}:gift")],
        [B(f"{EMO['fire']} Postga stars", callback_data=f"{SVC}:reaction"),
         B(f"{EMO['phone']} Raqam olish", callback_data=f"{SVC}:number")],
        [B(f"{EMO['wallet']} Balans", callback_data=f"{W}:main"),
         B(f"{EMO['orders']} Buyurtmalar", callback_data=f"{O}:list:0")],
        [B(f"{EMO['ref']} Referal", callback_data="m:ref"),
         B(f"{EMO['support']} Murojaat", callback_data=f"{SP}:new")],
        [B(f"{EMO['info']} FAQ", callback_data="m:faq"),
         B(f"{EMO['chat']} Kanal", callback_data="m:channel")],
    ]
    if is_admin:
        rows.append([B(f"{EMO['admin']} Admin Panel", callback_data=f"{AD}:main")])
    return K(inline_keyboard=rows)


def back(cb: str, label: str = f"{EMO['back']} Orqaga") -> K:
    return K(inline_keyboard=[[B(label, callback_data=cb)]])


def back_close(cb: str) -> K:
    return K(inline_keyboard=[[B(f"{EMO['back']} Orqaga", callback_data=cb)]])


# ── Xizmat menu ──────────────────────────────────────────────
def services_menu(enabled: dict) -> K:
    rows = []
    if enabled.get("stars", 1):
        rows.append([B(f"{EMO['star']} Stars olish", callback_data=f"{SVC}:stars")])
    if enabled.get("premium", 1):
        rows.append([B(f"{EMO['premium']} Premium olish", callback_data=f"{SVC}:premium")])
    if enabled.get("nft", 1):
        rows.append([B(f"{EMO['nft']} NFT olish", callback_data=f"{SVC}:nft")])
    if enabled.get("gift", 1):
        rows.append([B(f"{EMO['gift']} Gift olish", callback_data=f"{SVC}:gift")])
    if enabled.get("reaction", 1):
        rows.append([B(f"{EMO['fire']} Postga stars bosish", callback_data=f"{SVC}:reaction")])
    if enabled.get("number", 1):
        rows.append([B(f"{EMO['phone']} Raqam olish", callback_data=f"{SVC}:number")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)])
    return K(inline_keyboard=rows)


# ── Stars ────────────────────────────────────────────────────
def stars_menu(packages: list[dict], min_star: int = 50) -> K:
    rows = []
    for p in packages:
        rows.append([B(f"{EMO['star']} {p['amount']} ⭐ — {p['price']:,} so'm".replace(",", " "),
                       callback_data=f"{ST}:pkg:{p['amount']}")])
    rows.append([B(f"{EMO['edit']} Boshqa miqdor", callback_data=f"{ST}:cust")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{M_MAIN}")])
    return K(inline_keyboard=rows)


def confirm_kb(cb_yes: str, cb_no: str = f"{M_MAIN}") -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['check']} Tasdiqlash", callback_data=cb_yes)],
        [B(f"{EMO['cross']} Bekor qilish", callback_data=cb_no)],
    ])


# ── Premium ──────────────────────────────────────────────────
def premium_menu(prices: dict) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['premium']} 3 oy — {prices.get('premium_3','—')} so'm", callback_data=f"{PM}:3")],
        [B(f"{EMO['premium']} 6 oy — {prices.get('premium_6','—')} so'm", callback_data=f"{PM}:6")],
        [B(f"{EMO['premium']} 12 oy — {prices.get('premium_12','—')} so'm", callback_data=f"{PM}:12")],
        [B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)],
    ])


# ── Reaction ─────────────────────────────────────────────────
def reaction_counts(min_c: int, max_c: int) -> K:
    counts = list(range(max(min_c, 1), max_c + 1))
    rows = []
    for i in range(0, len(counts), 4):
        row = []
        for c in counts[i:i + 4]:
            row.append(B(str(c), callback_data=f"{RC}:c:{c}"))
        rows.append(row)
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)])
    return K(inline_keyboard=rows)


def reaction_confirm(stars: int, link: str) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['check']} Tasdiqlash ({stars} ⭐)", callback_data=f"{RC}:ok:{stars}")],
        [B(f"{EMO['cross']} Bekor qilish", callback_data=M_MAIN)],
    ])


# ── Wallet ───────────────────────────────────────────────────
def wallet_menu() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['plus']} Balans to'ldirish", callback_data=f"{W}:topup")],
        [B(f"{EMO['history']} To'lovlar tarixi", callback_data=f"{W}:hist:0")],
        [B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)],
    ])


def topup_methods(methods: list[dict]) -> K:
    rows = []
    for m in methods:
        rows.append([B(f"{EMO['card']} {m['method']} — {m['card_number']}",
                       callback_data=f"{W}:m:{m['method']}:{m['id']}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{W}:main")])
    return K(inline_keyboard=rows)


def last4_kb(method: str, card_id: int) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['edit']} Oxirgi 4 raqamni kiritaman", callback_data=f"{W}:4:{method}:{card_id}")],
        [B(f"{EMO['ok']} Kiritmayman", callback_data=f"{W}:n4:{method}:{card_id}")],
        [B(f"{EMO['cross']} Bekor qilish", callback_data=f"{W}:main")],
    ])


def deposit_paid_kb(method: str, card_id: int) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['check']} To'lov qildim", callback_data=f"{W}:pay:{method}:{card_id}")],
        [B(f"{EMO['cross']} Bekor qilish", callback_data=f"{W}:main")],
    ])


# ── Numbers ──────────────────────────────────────────────────
def number_menu(s1: bool, s2: bool) -> K:
    rows = []
    if s1:
        rows.append([B(f"{EMO['server']} Server 1 (API)", callback_data=f"{N}:s1")])
    if s2:
        rows.append([B(f"{EMO['server']} Server 2 (Hisob)" , callback_data=f"{N}:s2")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)])
    return K(inline_keyboard=rows)


def s1_countries(countries: list[dict]) -> K:
    rows = []
    for c in countries:
        rows.append([B(f"{EMO['globe']} {c['country_name'] or c['country']} — {c['price']:,} so'm".replace(",", " "),
                       callback_data=f"{N}:s1c:{c['country']}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{SVC}:number")])
    return K(inline_keyboard=rows)


def s1_buy_kb(country: str) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['check']} Sotib olish", callback_data=f"{N}:s1b:{country}")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{N}:s1")],
    ])


def s1_code_kb(order_id: int) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['code']} Kodni olish", callback_data=f"{N}:s1code:{order_id}")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{O}:list:0")],
    ])


def s2_stock(numbers: list[dict]) -> K:
    rows = []
    for n in numbers:
        rows.append([B(f"{EMO['phone']} +{n['phone']} — {n['price']:,} so'm".replace(",", " "),
                       callback_data=f"{N}:s2b:{n['id']}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{SVC}:number")])
    return K(inline_keyboard=rows)


# ── Orders ───────────────────────────────────────────────────
def orders_kb(page: int, total_pages: int, ids: list[int]) -> K:
    rows = []
    for oid in ids:
        rows.append([B(f"{EMO['doc']} #{oid}", callback_data=f"{O}:v:{oid}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{O}:list:{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{O}:list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)])
    return K(inline_keyboard=rows)


def order_view_kb(order_id: int, number: str | None = None, can_code: bool = False) -> K:
    rows = []
    if can_code and number:
        rows.append([B(f"{EMO['code']} Kodni olish", callback_data=f"{N}:s1code:{order_id}")])
    if can_code and number:
        rows.append([B(f"{EMO['ok']} Mana, xatolik yo'q", callback_data=f"{O}:ok:{order_id}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{O}:list:0")])
    return K(inline_keyboard=rows)


def orders_kb_nav(page: int, total_pages: int, prefix: str) -> K:
    rows = []
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{prefix}{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{prefix}{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{W}:main")])
    return K(inline_keyboard=rows)


def support_kb() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['mail']} Xabar yozish", callback_data=f"{SP}:new")],
        [B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)],
    ])


def referal_kb() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['back']} Orqaga", callback_data=M_MAIN)],
    ])
