"""
Smoke test — DB'siz biznes-logika va moslik mantiqini tekshiradi.

Ishga tushirish:
    .venv/bin/python tests/smoke_test.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db

# ──────────────────────────────────────────────────────────────
#  IN-MEMORY DB
# ──────────────────────────────────────────────────────────────
class FakeDB:
    def __init__(self):
        self.users = {}
        self.settings = dict(db.DEFAULT_SETTINGS)
        self.orders = {}
        self.tx = []
        self.deposits = {}
        self.stock = {}
        self.countries = {}
        self._ids = {"order": 0, "dep": 0, "tx": 0, "stock": 0}

    def users_row(self, uid, balance=100000.0):
        self.users[uid] = {
            "id": uid, "username": "tester", "first_name": "T",
            "last_name": "", "balance": balance, "ref_by": None,
            "order_count": 0, "is_banned": 0,
        }
        return self.users[uid]

    def new_order(self, **kw):
        self._ids["order"] += 1
        row = {"id": self._ids["order"], "user_id": 0, "service": "x", "target": None,
               "qty": None, "stars": None, "price": 0, "status": "processing",
               "external_ref": None, "number": None, "hash_code": None,
               "details": None, "admin_note": None, "created_at": None}
        row.update(kw)
        self.orders[row["id"]] = row
        return dict(row)


F = FakeDB()


async def fake_fetchone(sql, args=()):
    args = tuple(args)
    if "FROM users" in sql:
        if "WHERE id=%s" in sql and args:
            return dict(F.users.get(args[0], {})) or None
        return None
    if "FROM settings" in sql:
        key = args[0] if args else None
        return {"skey": key, "svalue": F.settings.get(key, "")} if key in F.settings else None
    if "FROM orders" in sql and "WHERE id" in sql:
        return dict(F.orders.get(args[0], {})) or None
    if "FROM deposits" in sql and "WHERE id" in sql:
        return dict(F.deposits.get(args[0], {})) or None
    if "FROM number_s1_countries" in sql:
        c = args[0].upper() if args else ""
        row = F.countries.get(c)
        return dict(row) if row else None
    if "FROM number_stock" in sql and "WHERE id" in sql:
        return dict(F.stock.get(args[0], {})) or None
    if "SELECT ref_by" in sql:
        u = F.users.get(args[0])
        return {"ref_by": u["ref_by"] if u else None}
    if "SELECT is_banned" in sql:
        u = F.users.get(args[0])
        return {"is_banned": u["is_banned"] if u else 0}
    return None


async def fake_fetchall(sql, args=()):
    if "FROM orders" in sql:
        out = [dict(o) for o in F.orders.values()]
        if "status=%s" in sql:
            out = [o for o in out if o["status"] == args[0]]
        return sorted(out, key=lambda o: -o["id"])
    if "FROM deposits" in sql:
        return [dict(d) for d in F.deposits.values()]
    if "FROM number_stock" in sql:
        return [dict(s) for s in F.stock.values()]
    if "FROM number_s1_countries" in sql:
        return [dict(c) for c in F.countries.values()]
    if "FROM users" in sql:
        return [dict(u) for u in F.users.values()]
    return []


async def fake_fetchval(sql, args=(), default=None):
    if "FROM settings" in sql:
        key = args[0] if args else None
        return F.settings.get(key, default) if key else default
    if "COUNT(*)" in sql:
        if "deposits" in sql:
            return len(F.deposits)
        if "users" in sql:
            return len(F.users)
    if "balance" in sql and "FROM users" in sql:
        u = F.users.get(args[0])
        return u["balance"] if u else 0
    if "COUNT(*) FROM orders" in sql:
        return len(F.orders)
    return default


async def fake_execute(sql, args=()):
    args = tuple(args)
    if sql.startswith("INSERT INTO orders"):
        oid = F._ids["order"] + 1
        F._ids["order"] = oid
        F.orders[oid] = {"id": oid, "user_id": args[0], "service": args[1],
                         "target": args[2], "qty": args[3], "stars": args[4],
                         "price": args[5], "status": "processing", "external_ref": None,
                         "number": None, "hash_code": None, "details": args[6],
                         "admin_note": None, "created_at": None}
        return oid
    if sql.startswith("INSERT INTO deposits"):
        did = F._ids["dep"] + 1
        F._ids["dep"] = did
        F.deposits[did] = {"id": did, "user_id": args[0], "amount": float(args[1]),
                           "method": args[2], "card_digits": args[3], "status": "pending",
                           "matched_msg_id": None}
        return did
    if sql.startswith("INSERT INTO number_stock"):
        sid = F._ids["stock"] + 1
        F._ids["stock"] = sid
        F.stock[sid] = {"id": sid, "phone": args[0], "country": args[1],
                        "price": float(args[2]), "session_file": args[3],
                        "twofa": args[4], "note": args[5], "status": "available",
                        "buyer_id": None, "order_id": None}
        return sid
    if sql.startswith("INSERT INTO settings") or sql.startswith("INSERT IGNORE INTO settings"):
        key, val = args[0], args[1]
        F.settings[key] = val
        return 1
    if sql.startswith("INSERT INTO transactions"):
        F._ids["tx"] += 1
        F.tx.append({"id": F._ids["tx"], "user_id": args[0], "type": args[1],
                     "amount": args[2], "balance_after": args[3]})
        return F._ids["tx"]
    if sql.startswith("UPDATE users"):
        uid = args[-1]
        if "balance = balance -" in sql:
            amount = float(args[0])
            u = F.users[uid]
            if u["balance"] >= amount:
                u["balance"] -= amount
                return 1
            return 0
        if "balance = balance +" in sql:
            F.users[uid]["balance"] += float(args[0])
            return 1
        if "SET balance =" in sql:
            F.users[uid]["balance"] = float(args[0])
            return 1
        if "order_count" in sql:
            F.users[uid]["order_count"] += 1
            return 1
        if "ref_earned" in sql:
            F.users[uid]["ref_earned"] += float(args[0])
            F.users[uid]["balance"] += float(args[0])
            return 1
        return 1
    if sql.startswith("UPDATE orders"):
        oid = args[-1]
        o = F.orders.get(oid)
        if not o:
            return 0
        if "status='success'" in sql:
            o["status"] = "success"
        elif "status='cancel'" in sql:
            o["status"] = "cancel"
        elif "status='fail'" in sql:
            o["status"] = "fail"
        if "number=%s" in sql:
            o["number"] = args[0]
        if "hash_code=%s" in sql:
            o["hash_code"] = args[0]
        if "external_ref" in sql:
            o["external_ref"] = args[0]
        return 1
    if sql.startswith("UPDATE deposits"):
        did = args[-1]
        d = F.deposits.get(did)
        if not d or d["status"] != "pending":
            return 0
        d["status"] = "success"
        d["matched_msg_id"] = args[0]
        return 1
    if sql.startswith("UPDATE number_stock"):
        sid = args[-1]
        s = F.stock.get(sid)
        if not s:
            return 0
        if "status='reserved'" in sql:
            if s["status"] != "available":
                return 0
            s["status"] = "reserved"
            s["order_id"] = args[0]
            return 1
        if "status='sold'" in sql:
            s["status"] = "sold"
            s["buyer_id"] = args[0]
            return 1
        if "status='available'" in sql:
            s["status"] = "available"
            s["buyer_id"] = None
            s["order_id"] = None
            return 1
        return 1
    return 1


async def fake_execute_rowcount(sql, args=()):
    if "UPDATE number_stock" in sql or "UPDATE orders" in sql or "UPDATE deposits" in sql:
        return await fake_execute(sql, args)
    return 1


# Patch db module
db.fetchone = fake_fetchone
db.fetchall = fake_fetchall
db.fetchval = fake_fetchval
db.execute = fake_execute
db.execute_rowcount = fake_execute_rowcount


# ──────────────────────────────────────────────────────────────
#  Fake tashqi xizmatlar
# ──────────────────────────────────────────────────────────────
from bot.services import orders as order_svc
from bot.services import wallet
from bot.utils import fragment, spider, tg_actions, tg_client

real_wallet = {k: getattr(wallet, k) for k in ("debit", "credit", "change_balance", "grant_referral_bonus")}


async def fake_debit(user_id, amount, tx_type, note=""):
    u = F.users[user_id]
    if u["balance"] < amount:
        raise wallet.NoMoney("yoq")
    u["balance"] -= amount
    F.tx.append({"id": len(F.tx) + 1, "user_id": user_id, "type": tx_type,
                 "amount": -amount, "balance_after": u["balance"]})
    return u["balance"]


async def fake_credit(user_id, amount, tx_type, note=""):
    F.users[user_id]["balance"] += amount
    return F.users[user_id]["balance"]


async def fake_grant(ref, buyer, amount):
    return None


wallet.debit = fake_debit
wallet.credit = fake_credit
wallet.grant_referral_bonus = fake_grant
wallet.change_balance = fake_credit


class FakeFragment:
    async def buy_stars(self, u, a):
        return {"success": True, "ref_id": "Ref#TEST", "transaction_hash": "hash1"}

    async def buy_premium(self, u, d):
        return {"success": True, "ref_id": "Ref#PM", "transaction_hash": "hash2"}


fragment.buy_stars = FakeFragment().buy_stars
fragment.buy_premium = FakeFragment().buy_premium


async def fake_get_number(country, server=1):
    return {"number": "+9701234567", "hash_code": "HASH-1"}


async def fake_get_code(hash_code):
    return "12345"


spider.get_number = fake_get_number
spider.get_code = fake_get_code


class FakeClient:
    def __init__(self):
        self.phone = "998001234567"

    async def get_input_entity(self, x):
        return x

    async def is_authorized(self):
        return True

    async def get_me(self):
        return type("Me", (), {"id": 1, "username": "x", "first_name": "X" })()


fake_acc = {"id": 1, "phone": "998001234567", "session_file": "x.session", "status": "active"}


async def fake_get_account(t):
    return fake_acc


async def fake_tg_client(phone, sf=None):
    return FakeClient()


async def fake_drop(phone, **kw):
    return None


async def fake_auth(client):
    return True


async def fake_reaction(client, peer, msg_id, count):
    return {"ok": True, "count": count}


async def fake_resolve(client, link):
    return "peer", 123


async def fake_gift(client, peer, gift_id, **kw):
    return {"ok": True}


order_svc._get_account = fake_get_account
tg_client.get_client = fake_tg_client
tg_client.is_authorized = fake_auth
tg_client.drop_client = fake_drop
tg_actions.send_paid_reaction = fake_reaction
tg_actions.resolve_post = fake_resolve
tg_actions.send_star_gift = fake_gift


# ──────────────────────────────────────────────────────────────
#  Testlar
# ──────────────────────────────────────────────────────────────
async def main():
    passed = 0

    def check(name, cond):
        nonlocal passed
        assert cond, name
        passed += 1
        print(f"  ✔ {name}")

    print("1) Emoji render")
    from bot.emoji import E, FALLBACK
    await db.set_setting_json("emoji_ids", {"star": "1234567890123456789"})
    await E.reload()
    text, ents = E.render("Salom {star} va {premium}")
    check("fallback va custom entity", "⭐" in text and ents and ents[0].type == "custom_emoji")

    print("2) Stars buyurtma")
    F.users_row(100, balance=500000)
    o = await order_svc.order_stars(100, "durov", 50)
    check("status success", o["status"] == "success")
    check("balance ayirildi", F.users[100]["balance"] == 500000 - 18000)

    print("3) Premium buyurtma")
    o = await order_svc.order_premium(100, "durov", 3)
    check("premium success", o["status"] == "success")

    print("4) Gift buyurtma")
    await db.set_setting("gift_id", "1234")
    o = await order_svc.order_gift(100, "durov")
    check("gift success", o["status"] == "success")

    print("5) Reaksiya")
    o = await order_svc.order_reaction(100, "https://t.me/channel/123", 3)
    check("reaction success", o["status"] == "success")

    print("6) NFT (admin bajaradi)")
    o = await order_svc.order_nft(100, "username")
    check("nft processing", o["status"] == "processing")

    print("7) Raqam S1")
    F.countries["PS"] = {"country": "PS", "country_name": "Falastin", "price": 10000, "enabled": 1}
    o = await order_svc.order_number_s1(100, "ps")
    check("s1 success", o["status"] == "success" and o["number"] == "+9701234567")
    code = await order_svc.number_s1_code(o["id"])
    check("kod olindi", code == "12345")

    print("8) Raqam S2")
    await fake_execute("INSERT INTO number_stock (phone, country, price, session_file, twofa, note) "
                       "VALUES (%s,%s,%s,%s,%s,%s)",
                       ("998701234567", "UZ", 25000, "/tmp/x.session", "pass", ""))
    sid = 1
    o = await order_svc.order_number_s2(100, sid)
    check("s2 success", o["status"] == "success" and F.stock[sid]["status"] == "sold")
    check("s2 xaridor", F.stock[sid]["buyer_id"] == 100)

    print("9) Yetarli balans yo'q")
    try:
        await order_svc.order_stars(100, "durov", 1000)
        check("NoMoney chiqishi", False)
    except order_svc.OrderError as e:
        check("NoMoney chiqishi", "mablag'" in e.message)

    print("10) To'lov mosligi (watcher)")
    from bot.utils.watcher import PaymentWatcher
    watcher = PaymentWatcher(None)
    await fake_execute(
        "INSERT INTO deposits (user_id, amount, method, card_digits) VALUES (%s,%s,%s,%s)",
        (100, 50000, "UZCARD", "1234"),
    )
    dep_id = F._ids["dep"]
    await watcher._try_match("UZCARD", 50000.0, ["1234"], 777, "+ 50 000 UZS")
    check("depozit tasdiqlandi", F.deposits[dep_id]["status"] == "success")
    check("balans qo'shildi", F.users[100]["balance"] > 100000)

    print(f"\n✅ {passed} ta test muvaffaqiyatli o'tdi")


if __name__ == "__main__":
    asyncio.run(main())
