"""Kichik yordamchi funksiyalar: base64, summa, log."""
from __future__ import annotations

import base64
import binascii
import logging
import re

BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def b64_encode_auto(value: str) -> str:
    """
    Seed/cookies uchun: agar qiymat allaqachon base64 bo'lsa — o'zgarishsiz,
    aks holda base64 kodlaydi (fragment API base64 kutiladi).
    """
    if not value:
        return ""
    s = value.strip()
    if BASE64_RE.fullmatch(s) and len(s) % 4 == 0:
        try:
            decoded = base64.b64decode(s, validate=True)
            # dekodlangan narsa oddiy matnga o'xshasa, u allaqachon base64
            if b"%" not in decoded:
                return s
        except (binascii.Error, ValueError):
            pass
    return base64.b64encode(s.encode("utf-8")).decode("utf-8")


def parse_amount(s: str | int | float | None) -> float:
    """'14 000' | '14,000' | '14000' -> 14000.0"""
    if isinstance(s, (int, float)):
        return float(s)
    s = re.sub(r"\s+", "", str(s or ""))
    if not s:
        return 0.0
    if s.count(",") > 0 and s.count(".") > 0:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(",") > 0:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def sanitize_text(text: str, limit: int = 4000) -> str:
    return (text or "")[:limit]
