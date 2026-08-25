"""
Buyurtmalar biznes-logikasi: yaratish, muvaffaqiyat/bekor qilish,
referal bonus, tashqi xizmat chaqiruvlari.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import db
from bot.services import wallet
from bot.utils import fragment, spider, tg_actions, tg_client
from bot.utils.tg_client import AccountError

log = logging.getLogger("orders")


class OrderError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xatolik."""

    def __init__(self, message: str, refunded: bool = False):
        super().__init__(message)
        self.message = message
        self.refunded = refunded


# ══════════════════════════════════════════════════════════════
#  ASOSIY ORDER OPERATSIYALARI
# ══════════════════════════════════════════════════════════════
async def create_order(
    user_id: int,
    service: str,
    target: str | None = None,
    qty: int | None = None,
    stars: int | None = None,
    price: float = 0.0,
    details: dict | None = None,
) -> dict:
    order_id = await db.execute(
        "INSERT INTO orders (user_id, service, target, qty, stars, price, details, status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,'processing')",
        (user_id, service, target, qty, stars, price,
         json.dumps(details or {}, ensure_ascii=False)),
    )
    order = await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))
    return order


async def set_order_fields(order_id: int, **fields: Any) -> None:
    sets = ", ".join(f"{k}=%s" for k in fields)
    await db.execute(
        f"UPDATE orders SET {sets}, updated_at=NOW() WHERE id=%s",
        (*fields.values(), order_id),
    )


async def success_order(order_id: int, external_ref: str | None = None, details: dict | None = None) -> tuple[dict, float]:
    """Order'ni 'success' qiladi, foydalanuvchi statistikasini va referal bonusni beradi."""
    order = await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))
    if not order:
        raise OrderError("Buyurtma topilmadi")
    if order["status"] == "success":
        return order, 0.0

    await db.execute(
        "UPDATE orders SET status='success', external_ref=%s, details=COALESCE(%s, details), "
        "updated_at=NOW() WHERE id=%s",
        (external_ref, json.dumps(details, ensure_ascii=False) if details else None, order_id),
    )
    await db.execute(
        "UPDATE users SET order_count=order_count+1 WHERE id=%s", (order["user_id"],)
    )

    # Referal bonus
    bonus = 0.0
    user = await db.fetchone("SELECT ref_by FROM users WHERE id=%s", (order["user_id"],))
    referrer_id = user.get("ref_by") if user else None
    if referrer_id:
        try:
            bonus = await wallet.grant_referral_bonus(referrer_id, order["user_id"], float(order["price"]))
        except Exception as e:
            log.warning("Referal bonus xatosi o#%s: %s", order_id, e)

    return await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,)), bonus or 0.0


async def fail_order(order_id: int, reason: str, refund: bool = True) -> dict:
    order = await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))
    if not order:
        raise OrderError("Buyurtma topilmadi")
    if order["status"] in ("success", "cancel"):
        return order
    if refund and float(order["price"]) > 0 and order["status"] != "fail":
        try:
            await wallet.credit(
                order["user_id"], float(order["price"]), "refund",
                f"Buyurtma #{order_id} qaytarildi ({reason})",
            )
        except Exception as e:
            log.error("Qaytarish xatosi o#%s: %s", order_id, e)
    await db.execute(
        "UPDATE orders SET status='fail', admin_note=%s, updated_at=NOW() WHERE id=%s",
        (reason[:1000], order_id),
    )
    return await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))


async def cancel_order(order_id: int, reason: str = "") -> dict:
    order = await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))
    if not order:
        raise OrderError("Buyurtma topilmadi")
    if order["status"] in ("success", "cancel"):
        return order
    if float(order["price"]) > 0:
        try:
            await wallet.credit(
                order["user_id"], float(order["price"]), "refund",
                f"Buyurtma #{order_id} bekor qilindi",
            )
        except Exception as e:
            log.error("Bekor qilishda qaytarish xatosi o#%s: %s", order_id, e)
    await db.execute(
        "UPDATE orders SET status='cancel', admin_note=%s, updated_at=NOW() WHERE id=%s",
        (reason[:1000], order_id),
    )
    return await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))


# ══════════════════════════════════════════════════════════════
#  NARXLAR
# ══════════════════════════════════════════════════════════════
async def _cancel_new(order_id: int) -> None:
    try:
        await db.execute("UPDATE orders SET status='cancel' WHERE id=%s", (order_id,))
    except Exception:
        pass


async def stars_price(amount: int) -> float | None:
    """Paket yoki kustom (rate) narx. Topilmasa None."""
    packages = await db.get_setting_json("stars_packages", [])
    for p in packages or []:
        if int(p.get("amount", 0)) == int(amount):
            return float(p.get("price", 0))
    try:
        rate = float(await db.get_setting("stars_rate", "340"))
    except ValueError:
        rate = 340.0
    return round(amount * rate, 2)


async def reaction_price(stars: int) -> float:
    try:
        rate = float(await db.get_setting("reaction_price_per_star", "300"))
    except ValueError:
        rate = 300.0
    return round(int(stars) * rate, 2)


# ══════════════════════════════════════════════════════════════
#  XIZMATLAR
# ══════════════════════════════════════════════════════════════
async def order_stars(user_id: int, username: str, amount: int) -> dict:
    """Stars xarid — Fragment API orqali."""
    price = await stars_price(amount)
    if price is None or price <= 0:
        raise OrderError("Narx aniqlanmadi")
    order = await create_order(
        user_id, "stars", target=username, stars=amount, price=price,
        details={"username": username, "amount": amount},
    )
    try:
        await wallet.debit(user_id, price, "order", f"Stars #{order['id']}")
    except wallet.NoMoney:
        await db.execute("UPDATE orders SET status='cancel' WHERE id=%s", (order["id"],))
        raise OrderError("Balansda mablag' yetarli emas. Avval balansni to'ldiring.") from None
    try:
        result = await fragment.buy_stars(username, amount)
        order, bonus = await success_order(
            order["id"],
            external_ref=str(result.get("ref_id") or result.get("transaction_hash") or ""),
            details={"username": username, "amount": amount, "api": result},
        )
        return order
    except fragment.FragmentError as e:
        await fail_order(order["id"], str(e))
        raise OrderError(f"Stars xaridi bajarilmadi: {e}. Pul balansga qaytarildi.", refunded=True) from None


async def order_premium(user_id: int, username: str, duration: int) -> dict:
    key = f"premium_{duration}"
    price = float(await db.get_setting(key, "0"))
    if price <= 0:
        raise OrderError("Bu muddat uchun narx sozlanmagan")
    order = await create_order(
        user_id, "premium", target=username, qty=duration, price=price,
        details={"username": username, "duration": duration},
    )
    try:
        await wallet.debit(user_id, price, "order", f"Premium #{order['id']}")
    except wallet.NoMoney:
        await _cancel_new(order["id"])
        raise OrderError("Balansda mablag' yetarli emas. Avval balansni to'ldiring.") from None
    try:
        result = await fragment.buy_premium(username, duration)
        order, _ = await success_order(
            order["id"],
            external_ref=str(result.get("ref_id") or result.get("transaction_hash") or ""),
            details={"username": username, "duration": duration, "api": result},
        )
        return order
    except fragment.FragmentError as e:
        await fail_order(order["id"], str(e))
        raise OrderError(f"Premium xaridi bajarilmadi: {e}. Pul balansga qaytarildi.", refunded=True) from None


async def order_gift(user_id: int, username: str) -> dict:
    gift_id = await db.get_setting("gift_id", "")
    price = float(await db.get_setting("gift_price", "0"))
    if not gift_id:
        raise OrderError("Gift sozlanmagan (Admin: xizmat → Gift)")
    if price <= 0:
        raise OrderError("Gift narxi sozlanmagan")
    order = await create_order(
        user_id, "gift", target=username, qty=1, price=price,
        details={"username": username, "gift_id": gift_id},
    )
    try:
        await wallet.debit(user_id, price, "order", f"Gift #{order['id']}")
    except wallet.NoMoney:
        await _cancel_new(order["id"])
        raise OrderError("Balansda mablag' yetarli emas.") from None

    account = await _get_account("gift")
    try:
        client = await tg_client.get_client(account["phone"], account["session_file"])
        if not await tg_client.is_authorized(client):
            raise AccountError("Gift hisobi avtorizatsiyadan o'tmagan")
        peer = await client.get_input_entity(username)
        await tg_actions.send_star_gift(client, peer, int(gift_id))
        order, _ = await success_order(order["id"], details={"username": username, "gift_id": gift_id})
        await tg_client.drop_client(account["phone"])
        return order
    except Exception as e:
        await fail_order(order["id"], str(e))
        raise OrderError(f"Gift yuborilmadi: {e}. Pul balansga qaytarildi.", refunded=True) from None


async def order_reaction(user_id: int, link: str, stars: int) -> dict:
    min_s = int(await db.get_setting("reaction_min_stars", "1"))
    max_s = int(await db.get_setting("reaction_max_stars", "25"))
    if not (min_s <= stars <= max_s):
        raise OrderError(f"Stars soni {min_s}..{max_s} oralig'ida bo'lishi kerak")
    price = await reaction_price(stars)
    order = await create_order(
        user_id, "reaction", target=link, stars=stars, price=price,
        details={"link": link, "stars": stars},
    )
    try:
        await wallet.debit(user_id, price, "order", f"Postga stars #{order['id']}")
    except wallet.NoMoney:
        await _cancel_new(order["id"])
        raise OrderError("Balansda mablag' yetarli emas.") from None

    account = await _get_account("reaction")
    try:
        client = await tg_client.get_client(account["phone"], account["session_file"])
        if not await tg_client.is_authorized(client):
            raise AccountError("Reaksiya hisobi avtorizatsiyadan o'tmagan")
        peer, msg_id = await tg_actions.resolve_post(client, link)
        await tg_actions.send_paid_reaction(client, peer, msg_id, stars)
        order, _ = await success_order(
            order["id"], details={"link": link, "stars": stars, "account": account["phone"]}
        )
        await tg_client.drop_client(account["phone"])
        return order
    except tg_actions.TgActionError as e:
        await fail_order(order["id"], str(e))
        raise OrderError(f"Reaksiya yuborilmadi: {e}. Pul balansga qaytarildi.", refunded=True) from None
    except Exception as e:
        await fail_order(order["id"], str(e))
        raise OrderError(f"Reaksiya yuborilmadi: {e}", refunded=True) from None


async def order_nft(user_id: int, target: str) -> dict:
    """NFT buyurtma — admin qo'lda bajaradi (Fragment'da NFT alohida jarayon)."""
    price = float(await db.get_setting("nft_price", "0"))
    if price <= 0:
        raise OrderError("NFT narxi sozlanmagan")
    order = await create_order(
        user_id, "nft", target=target, qty=1, price=price,
        details={"target": target},
    )
    try:
        await wallet.debit(user_id, price, "order", f"NFT #{order['id']}")
    except wallet.NoMoney:
        await _cancel_new(order["id"])
        raise OrderError("Balansda mablag' yetarli emas.") from None
    return order


async def _get_account(acc_type: str) -> dict:
    acc = await db.fetchone(
        "SELECT * FROM tg_accounts WHERE acc_type=%s AND status='active' "
        "ORDER BY success_count ASC LIMIT 1",
        (acc_type,),
    )
    if not acc:
        raise AccountError(f"{acc_type} uchun faol hisob topilmadi")
    return acc


# ══════════════════════════════════════════════════════════════
#  RAQAMLAR
# ══════════════════════════════════════════════════════════════
async def order_number_s1(user_id: int, country: str) -> dict:
    row = await db.fetchone(
        "SELECT * FROM number_s1_countries WHERE country=%s AND enabled=1", (country.upper(),)
    )
    if not row:
        raise OrderError("Bu davlat uchun xizmat o'chirilgan")
    price = float(row["price"])
    server = int(await db.get_setting("spider_server", "1"))

    order = await create_order(
        user_id, "number_s1", target=country, qty=1, price=price,
        details={"country": country.upper()},
    )
    try:
        await wallet.debit(user_id, price, "order", f"Raqam (S1) #{order['id']}")
    except wallet.NoMoney:
        await _cancel_new(order["id"])
        raise OrderError("Balansda mablag' yetarli emas.") from None

    try:
        data = await spider.get_number(country, server=server)
        await set_order_fields(
            order["id"], number=data["number"], hash_code=data["hash_code"],
        )
        order, _ = await success_order(
            order["id"],
            details={"country": country.upper(), "number": data["number"], "hash": data["hash_code"]},
        )
        return order
    except spider.SpiderError as e:
        await fail_order(order["id"], str(e))
        raise OrderError(f"Raqam olinmadi: {e}. Pul balansga qaytarildi.", refunded=True) from None


async def number_s1_code(order_id: int) -> str:
    order = await db.fetchone("SELECT * FROM orders WHERE id=%s", (order_id,))
    if not order or order["service"] != "number_s1":
        raise OrderError("Buyurtma topilmadi")
    if order["status"] != "success":
        raise OrderError("Raqam hali olinmagan")
    if not order.get("hash_code"):
        raise OrderError("Hash_code yo'q")
    code = await spider.get_code(order["hash_code"])
    return str(code)


async def order_number_s2(user_id: int, stock_id: int) -> dict:
    stock = await db.fetchone("SELECT * FROM number_stock WHERE id=%s", (stock_id,))
    if not stock or stock["status"] != "available":
        raise OrderError("Bu raqam allaqachon sotilgan yoki mavjud emas")

    order = await create_order(
        user_id, "number_s2", target=stock["phone"], qty=1, price=float(stock["price"]),
        details={"phone": stock["phone"], "country": stock["country"]},
    )
    # Raqamni band qilish (faqat bitta xaridor uchun)
    locked = await db.execute_rowcount(
        "UPDATE number_stock SET status='reserved', order_id=%s WHERE id=%s AND status='available'",
        (order["id"], stock_id),
    )
    if not locked:
        await db.execute("UPDATE orders SET status='cancel' WHERE id=%s", (order["id"],))
        raise OrderError("Raqam birov olib ulgurdi")

    try:
        await wallet.debit(user_id, float(stock["price"]), "order", f"Raqam (S2) #{order['id']}")
    except wallet.NoMoney:
        await db.execute("UPDATE number_stock SET status='available', order_id=NULL WHERE id=%s", (stock_id,))
        raise OrderError("Balansda mablag' yetarli emas.") from None

    await db.execute(
        "UPDATE number_stock SET status='sold', buyer_id=%s, sold_at=NOW() WHERE id=%s",
        (user_id, stock_id),
    )
    await success_order(order["id"], details={"phone": stock["phone"], "country": stock["country"]})
    return await db.fetchone("SELECT * FROM orders WHERE id=%s", (order["id"],))
