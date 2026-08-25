"""Admin klaviaturalar."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton as B
from aiogram.types import InlineKeyboardMarkup as K

from bot.emoji import FALLBACK as EMO

AD = "ad"


def nav_2(texts: list[tuple[str, str, str]]) -> K:
    """(chap, callback, o'ng) juftlar ro'yxati → 2 ustunli klaviatura."""
    rows = []
    for left_text, left_cb, right_text, right_cb in texts:
        rows.append([B(left_text, callback_data=left_cb), B(right_text, callback_data=right_cb)])
    return K(inline_keyboard=rows)


def one(text: str, cb: str) -> K:
    return K(inline_keyboard=[[B(text, callback_data=cb)]])


def main() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['chart']} Statistika", callback_data=f"{AD}:stats"),
         B(f"{EMO['user']} Foydalanuvchilar", callback_data=f"{AD}:us:0")],
        [B(f"{EMO['bank']} Moliya", callback_data=f"{AD}:fin"),
         B(f"{EMO['gear']} Xizmatlar", callback_data=f"{AD}:svc")],
        [B(f"{EMO['server']} Raqamlar", callback_data=f"{AD}:num"),
         B(f"{EMO['key']} Hisoblar", callback_data=f"{AD}:acc")],
        [B(f"{EMO['orders']} Buyurtmalar", callback_data=f"{AD}:ol:all:0"),
         B(f"{EMO['trophy']} Hisobot", callback_data=f"{AD}:rep:today")],
        [B(f"{EMO['megaphone']} Reklama", callback_data=f"{AD}:bcast"),
         B(f"{EMO['support']} Murojaatlar", callback_data=f"{AD}:tk:0")],
        [B(f"{EMO['settings']} Sozlamalar", callback_data=f"{AD}:cfg"),
         B(f"{EMO['history']} Depozitlar", callback_data=f"{AD}:dep:0")],
        [B(f"{EMO['back']} Chiqish", callback_data="m:main")],
    ])


def stats_kb() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")],
    ])


def back_kb(label: str = f"{EMO['back']} Orqaga") -> K:
    return K(inline_keyboard=[[B(label, callback_data=f"{AD}:main")]])


def users_list_kb(rows: list[dict], page: int, total_pages: int) -> K:
    kb_rows = []
    for u in rows:
        text = f"{EMO['user']} {u['first_name'] or u['username'] or u['id']} ({u['id']})"
        kb_rows.append([B(text, callback_data=f"{AD}:uv:{u['id']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:us:{page - 1}"))
    nav.append(B(f"{EMO['search']} Qidirish", callback_data=f"{AD}:usearch"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:us:{page + 1}"))
    kb_rows.append(nav)
    kb_rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")])
    return K(inline_keyboard=kb_rows)


def user_view_kb(uid: int, banned: bool) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['plus']} Balans qo'shish", callback_data=f"{AD}:uadd:{uid}"),
         B(f"{EMO['minus']} Balans yechish", callback_data=f"{AD}:usub:{uid}")],
        [B(f"{EMO['history']} Tranzaksiyalar", callback_data=f"{AD}:utx:{uid}:0"),
         B(f"{EMO['ref']} Referallar", callback_data=f"{AD}:uref:{uid}")],
        [B(f"{EMO['warn']} Bloklash" if not banned else f"{EMO['check']} Blokdan chiqarish",
           callback_data=f"{AD}:uban:{uid}")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:us:0")],
    ])


def finance_menu() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['card']} Kartalar", callback_data=f"{AD}:cards:0"),
         B(f"{EMO['history']} Depozitlar", callback_data=f"{AD}:dep:0")],
        [B(f"{EMO['doc']} Tranzaksiyalar", callback_data=f"{AD}:tx:0")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")],
    ])


def cards_kb(cards: list[dict], page: int, total_pages: int) -> K:
    rows = []
    for c in cards:
        status = "🟢" if c["is_active"] else "🔴"
        rows.append([B(f"{status} {c['method']} · {c['card_number']}",
                       callback_data=f"{AD}:cardv:{c['id']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:cards:{page - 1}"))
    nav.append(B(f"{EMO['plus']} Karta qo'shish", callback_data=f"{AD}:cadd"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:cards:{page + 1}"))
    rows.append(nav)
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:fin")])
    return K(inline_keyboard=rows)


def card_view_kb(card: dict) -> K:
    label = "O'chirish" if card["is_active"] else "Yoqish"
    return K(inline_keyboard=[
        [B(f"{EMO['off'] if card['is_active'] else EMO['on']} {label}",
           callback_data=f"{AD}:ctg:{card['id']}")],
        [B(f"{EMO['delete']} O'chirish", callback_data=f"{AD}:cdel:{card['id']}")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:cards:0")],
    ])


def deposits_kb(deps: list[dict], page: int, total_pages: int) -> K:
    rows = []
    for d in deps:
        st = {"pending": "⏳", "success": "✅", "cancel": "🚫"}.get(d["status"], "❔")
        rows.append([B(f"{st} #{d['id']} · {d['user_id']} · {d['amount']} so'm · {d['method']}",
                       callback_data=f"{AD}:depv:{d['id']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:dep:{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:dep:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:fin")])
    return K(inline_keyboard=rows)


def deposit_view_kb(dep: dict) -> K:
    rows = []
    if dep["status"] == "pending":
        rows.append([B(f"{EMO['check']} Tasdiqlash", callback_data=f"{AD}:depok:{dep['id']}"),
                     B(f"{EMO['cross']} Bekor qilish", callback_data=f"{AD}:depno:{dep['id']}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:dep:0")])
    return K(inline_keyboard=rows)


def tx_kb(rows: list[dict], page: int, total_pages: int) -> K:
    kb_rows = []
    for t in rows:
        kb_rows.append([B(f"#{t['id']} · {t['user_id']} · {t['amount']} so'm · {t['type']}",
                          callback_data=f"{AD}:txv:{t['id']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:tx:{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:tx:{page + 1}"))
    if nav:
        kb_rows.append(nav)
    kb_rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:fin")])
    return K(inline_keyboard=kb_rows)


def services_menu(enabled: dict) -> K:
    rows = []
    star = "🟢" if enabled.get("stars", 1) else "🔴"
    prem = "🟢" if enabled.get("premium", 1) else "🔴"
    nft = "🟢" if enabled.get("nft", 1) else "🔴"
    gift = "🟢" if enabled.get("gift", 1) else "🔴"
    reac = "🟢" if enabled.get("reaction", 1) else "🔴"
    num = "🟢" if enabled.get("number", 1) else "🔴"
    rows.append([B(f"{star} {EMO['star']} Stars", callback_data=f"{AD}:svc:stars"),
                 B(f"{prem} {EMO['premium']} Premium", callback_data=f"{AD}:svc:premium")])
    rows.append([B(f"{nft} {EMO['nft']} NFT", callback_data=f"{AD}:svc:nft"),
                 B(f"{gift} {EMO['gift']} Gift", callback_data=f"{AD}:svc:gift")])
    rows.append([B(f"{reac} {EMO['fire']} Reaksiya", callback_data=f"{AD}:svc:reaction"),
                 B(f"{num} {EMO['phone']} Raqam", callback_data=f"{AD}:num")])
    rows.append([B(f"{EMO['ref']} Referal", callback_data=f"{AD}:svc:referral"),
                 B(f"{EMO['bolt']} Watcher", callback_data=f"{AD}:svc:watcher")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")])
    return K(inline_keyboard=rows)


def setting_value_kb(back_cb: str) -> K:
    return K(inline_keyboard=[[B(f"{EMO['back']} Orqaga", callback_data=back_cb)]])


def numbers_menu() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['globe']} Server 1 (Spider)", callback_data=f"{AD}:num:s1"),
         B(f"{EMO['phone']} Server 2 (Hisob)", callback_data=f"{AD}:num:s2")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")],
    ])


def s1_menu() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['refresh']} Davlatlarni yangilash", callback_data=f"{AD}:nsync")],
        [B(f"{EMO['list']} Davlatlar narxi", callback_data=f"{AD}:ncl:0")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:num")],
    ])


def s1_countries_kb(countries: list[dict], page: int, total_pages: int) -> K:
    rows = []
    for c in countries:
        st = "🟢" if c["enabled"] else "🔴"
        rows.append([B(f"{st} {c['country']} · {c['country_name']} · {c['price']} so'm",
                       callback_data=f"{AD}:ncp:{c['country']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:ncl:{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:ncl:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:num")])
    return K(inline_keyboard=rows)


def s1_country_kb(country: str, enabled: bool) -> K:
    label = "O'chirish" if enabled else "Yoqish"
    return K(inline_keyboard=[
        [B(f"{EMO['edit']} Narx o'zgartirish", callback_data=f"{AD}:ncp:{country}")],
        [B(f"{EMO['off'] if enabled else EMO['on']} {label}",
           callback_data=f"{AD}:nctg:{country}")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:num")],
    ])

def s2_menu() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['plus']} Raqam qo'shish", callback_data=f"{AD}:n2add")],
        [B(f"{EMO['list']} Zaxira raqamlar", callback_data=f"{AD}:n2:0")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:num")],
    ])


def s2_kb(items: list[dict], page: int, total_pages: int) -> K:
    rows = []
    for it in items:
        st = {"available": "🟢", "reserved": "🟡", "sold": "🔴", "removed": "⚫"}.get(it["status"], "❔")
        rows.append([B(f"{st} {it['phone']} · {it['country']} · {it['price']} so'm",
                       callback_data=f"{AD}:n2v:{it['id']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:n2:{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:n2:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(f"{EMO['plus']} Raqam qo'shish", callback_data=f"{AD}:n2add")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:num")])
    return K(inline_keyboard=rows)


def s2_view_kb(item: dict) -> K:
    rows = []
    if item["status"] in ("available", "removed"):
        rows.append([B(f"{EMO['on']} Sotuvga chiqarish", callback_data=f"{AD}:n2on:{item['id']}")])
    if item["status"] == "sold":
        rows.append([B(f"{EMO['edit']} Qayta sotuvga qo'yish", callback_data=f"{AD}:n2back:{item['id']}")])
    rows.append([B(f"{EMO['import']} Sessiya fayli yuklash", callback_data=f"{AD}:n2sf:{item['id']}")])
    rows.append([B(f"{EMO['delete']} O'chirish", callback_data=f"{AD}:n2del:{item['id']}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:n2:0")])
    return K(inline_keyboard=rows)


def accounts_menu() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['card']} UZCARD to'lov", callback_data=f"{AD}:acc:payment_uzcard"),
         B(f"{EMO['card']} HUMO to'lov", callback_data=f"{AD}:acc:payment_humo")],
        [B(f"{EMO['fire']} Reaksiya", callback_data=f"{AD}:acc:reaction"),
         B(f"{EMO['gift']} Gift", callback_data=f"{AD}:acc:gift")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")],
    ])


def acc_type_kb(acc_type: str, accounts: list[dict]) -> K:
    rows = []
    for a in accounts:
        st = {"active": "🟢", "ban": "🔴", "error": "🟠", "disabled": "⚫"}.get(a["status"], "❔")
        rows.append([B(f"{st} {a['phone']} · {a['name'] or '—'}",
                       callback_data=f"{AD}:accv:{a['id']}")])
    rows.append([B(f"{EMO['plus']} Hisob qo'shish", callback_data=f"{AD}:accadd:{acc_type}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:acc")])
    return K(inline_keyboard=rows)


def acc_view_kb(acc: dict) -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['off'] if acc['status'] == 'active' else EMO['on']} "
           f"{'Bloklash' if acc['status'] == 'active' else 'Faollashtirish'}",
           callback_data=f"{AD}:actg:{acc['id']}")],
        [B(f"{EMO['delete']} O'chirish", callback_data=f"{AD}:acdel:{acc['id']}")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:acc:{acc['acc_type']}")],
    ])


def orders_filter_kb(current: str) -> K:
    statuses = [("all", "Barchasi"), ("pending", "⏳ Kutilmoqda"), ("processing", "🔄 Jarayonda"),
                ("success", "✅ Bajarildi"), ("cancel", "🚫 Bekor"), ("fail", "❌ Xato")]
    rows = []
    for key, label in statuses:
        mark = "• " if key == current else ""
        rows.append([B(f"{mark}{label}", callback_data=f"{AD}:ol:{key}:0")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")])
    return K(inline_keyboard=rows)


def orders_kb(orders: list[dict], status: str, page: int, total_pages: int) -> K:
    rows = []
    for o in orders:
        rows.append([B(f"#{o['id']} · {o['user_id']} · {o['service']} · {o['price']} so'm",
                       callback_data=f"{AD}:ov:{o['id']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:ol:{status}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:ol:{status}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(f"{EMO['search']} Filtr", callback_data=f"{AD}:olf:{status}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")])
    return K(inline_keyboard=rows)


def order_view_kb(o: dict) -> K:
    rows = []
    if o["service"] == "nft" and o["status"] == "processing":
        rows.append([B(f"{EMO['check']} Bajarildi (natija yozish)", callback_data=f"{AD}:onft:{o['id']}")])
    if o["status"] in ("processing", "pending"):
        rows.append([B(f"{EMO['cross']} Bekor + qaytarish", callback_data=f"{AD}:ocancel:{o['id']}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:ol:all:0")])
    return K(inline_keyboard=rows)


def tickets_kb(tickets: list[dict], page: int, total_pages: int) -> K:
    rows = []
    for t in tickets:
        st = "🟡" if t["status"] == "open" else "🟢"
        rows.append([B(f"{st} #{t['id']} · {t['user_id']} · {(t['subject'] or '')[:40]}",
                       callback_data=f"{AD}:tkv:{t['id']}")])
    nav = []
    if page > 0:
        nav.append(B(f"{EMO['back']} Oldingi", callback_data=f"{AD}:tk:{page - 1}"))
    if page < total_pages - 1:
        nav.append(B("➡️ Keyingi", callback_data=f"{AD}:tk:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")])
    return K(inline_keyboard=rows)


def ticket_view_kb(t: dict) -> K:
    rows = []
    if t["status"] == "open":
        rows.append([B(f"{EMO['mail']} Javob berish", callback_data=f"{AD}:tkr:{t['id']}")])
    rows.append([B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:tk:0")])
    return K(inline_keyboard=rows)


def reports_kb(current: str) -> K:
    return K(inline_keyboard=[
        [B(f"{'• ' if current == 'today' else ''}Bugun", callback_data=f"{AD}:rep:today"),
         B(f"{'• ' if current == 'week' else ''}7 kun", callback_data=f"{AD}:rep:week")],
        [B(f"{'• ' if current == 'month' else ''}Oy", callback_data=f"{AD}:rep:month"),
         B(f"{'• ' if current == 'all' else ''}Hammasi", callback_data=f"{AD}:rep:all")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")],
    ])


def broadcast_kb() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['check']} Yuborishni boshlash", callback_data=f"{AD}:bcastgo")],
        [B(f"{EMO['cross']} Bekor", callback_data=f"{AD}:main")],
    ])


def services_settings_kb() -> K:
    return K(inline_keyboard=[
        [B(f"{EMO['star']} Stars narxlar", callback_data=f"{AD}:sv:stars")],
        [B(f"{EMO['premium']} Premium narxlar", callback_data=f"{AD}:sv:premium")],
        [B(f"{EMO['nft']} NFT narx", callback_data=f"{AD}:v:nft_price")],
        [B(f"{EMO['gift']} Gift sozlamalari", callback_data=f"{AD}:sv:gift")],
        [B(f"{EMO['fire']} Reaksiya narxi", callback_data=f"{AD}:sv:reaction")],
        [B(f"{EMO['wallet']} Minimal to'lov", callback_data=f"{AD}:v:min_deposit")],
        [B(f"{EMO['ref']} Referal", callback_data=f"{AD}:sv:referral")],
        [B(f"{EMO['bolt']} Payment watcher", callback_data=f"{AD}:svc:watcher")],
        [B(f"{EMO['back']} Orqaga", callback_data=f"{AD}:main")],
    ])
