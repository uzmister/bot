"""
To'lov aniqlash xizmati (Quart versiyasidagi namunaning botga moslashgani).

CardXabarBot (UZCARD) va HumocardBot (HUMO) — sessiyali Telegram hisob orqali
o'qiladi, yangi "➕ N UZS" xabarlari kutilayotgan (pending) depozitlar bilan
solishtiriladi va mos kelsa balans avtomatik to'ldiriladi.

Xususiyatlari:
- Bir xil xabar ikki marta hisoblanmaydi (msg_id dedupe)
- Summa + oxirgi 4 raqam mosligi (ixtiyoriy, aniqroq)
- 5 daqiqalik yangilik oynasi, sessiya buzilganini xavfsiz tiklash
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

import db
import config
from bot.services.wallet import credit
from bot.utils.misc import parse_amount
from bot.utils import tg_client

log = logging.getLogger("watcher")

AMOUNT_RE = re.compile(r"\+?\s*([\d\s.,]+)\s*UZS", re.I)
DIGITS_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")


class PaymentWatcher:
    def __init__(self, bot):
        self.bot = bot
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        log.info("To'lov watcher ishga tushdi")
        while not self._stop.is_set():
            try:
                enabled = (await db.get_setting("watcher_enabled", "1")) == "1"
                if enabled:
                    await self._scan_all()
            except Exception as e:
                log.error("Watcher sikl xatosi: %s", e)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=config.WATCHER_SLEEP)
            except asyncio.TimeoutError:
                pass
        log.info("To'lov watcher to'xtadi")

    # ── skan ────────────────────────────────────────────────
    async def _scan_all(self) -> None:
        accounts = await db.fetchall(
            "SELECT * FROM tg_accounts WHERE acc_type IN ('payment_uzcard','payment_humo') "
            "AND status='active'"
        )
        for acc in accounts:
            try:
                await self._scan_account(acc)
            except Exception as e:
                log.warning("Hisob skani xatosi (%s): %s", acc["phone"], e)
                if "flood" in str(e).lower() or "auth" in str(e).lower():
                    await db.execute(
                        "UPDATE tg_accounts SET status='error', last_error=%s, updated_at=NOW() WHERE id=%s",
                        (str(e)[:500], acc["id"]),
                    )

    async def _scan_account(self, acc: dict) -> None:
        method = "UZCARD" if acc["acc_type"] == "payment_uzcard" else "HUMO"
        peer = config.PAYMENT_BOTS.get(method)
        if not peer:
            return
        client = await tg_client.get_client(acc["phone"], acc["session_file"])
        if not await tg_client.is_authorized(client):
            await db.execute(
                "UPDATE tg_accounts SET status='error', last_error='Avtorizatsiya yoq', "
                "updated_at=NOW() WHERE id=%s",
                (acc["id"],),
            )
            raise tg_client.AccountError("Hisob avtorizatsiyadan o'tmagan")

        messages = await client.get_messages(peer, limit=30)
        now_ts = time.time()
        scanned = 0
        for msg in messages:
            text = getattr(msg, "message", None)
            date = getattr(msg, "date", None)
            ts = date.timestamp() if date else 0
            if not text or (now_ts - ts) > config.MATCH_WINDOW_SEC or ts > now_ts + 60:
                continue
            m = AMOUNT_RE.search(text)
            if not m:
                continue
            amount = parse_amount(m.group(1))
            if amount <= 0:
                continue
            digits = DIGITS_RE.findall(text)
            await self._try_match(method, amount, digits, int(getattr(msg, "id", 0)), text)
            scanned += 1
        if scanned:
            log.info("%s (%s): %d ta moslik tekshirildi", peer, acc["phone"], scanned)

    # ── moslik ──────────────────────────────────────────────
    async def _try_match(self, method: str, amount: float, digits: list[str], msg_id: int, msg_text: str) -> None:
        # Shu xabar allaqachon boshqa depozitga ulanganmi?
        dup = await db.fetchone(
            "SELECT id FROM deposits WHERE matched_msg_id=%s AND status='success'", (msg_id,)
        )
        if dup:
            return

        deposits = await db.fetchall(
            "SELECT * FROM deposits WHERE status='pending' AND method=%s "
            "AND created_at > NOW() - INTERVAL %s MINUTE",
            (method, max(5, config.SCAN_WINDOW_SEC // 60)),
        )
        for dep in deposits:
            if abs(float(dep["amount"]) - amount) > config.AMOUNT_EPSILON:
                continue
            if dep.get("card_digits") and str(dep["card_digits"]) not in digits:
                continue

            # Faqat bitta watcher ustidan o'tishi uchun atomik update
            updated = await db.execute_rowcount(
                "UPDATE deposits SET status='success', matched_msg_id=%s, updated_at=NOW() "
                "WHERE id=%s AND status='pending'",
                (msg_id, dep["id"]),
            )
            if not updated:
                continue

            try:
                new_balance = await credit(
                    dep["user_id"], float(dep["amount"]), "deposit",
                    f"To'lov keldi #{dep['id']} ({method})",
                )
                log.info("Depozit #%s tasdiqlandi, user %s, %s so'm", dep["id"], dep["user_id"], dep["amount"])
                await self._notify(dep, method, new_balance, msg_text)
            except Exception as e:
                log.error("Depozit #%s kreditlash xatosi: %s", dep["id"], e)
            return

    async def _notify(self, dep: dict, method: str, new_balance: float, msg_text: str) -> None:
        try:
            from bot.texts import money, render
            msg, ent = render(
                f"{'{check}'} To'lov qabul qilindi!\n\n"
                f"{'{card}'} Karta: {method}\n"
                f"{'{money}'} Summa: {money(dep['amount'])} so'm\n"
                f"{'{wallet}'} Yangi balans: {money(new_balance)} so'm\n\n"
                f"{'{spark}'} Rahmat!"
            )
            await self.bot.send_message(dep["user_id"], msg, entities=ent)
        except Exception as e:
            log.warning("Depozit bildirishnomasi yuborilmadi: %s", e)
