"""
Loyiha sozlamalari — .env faylidan o'qiladi.
Barcha dinamik sozlamalar (narxlar, seed, kartalar, emojilar...)
MySQL dagi `settings` jadvalida saqlanadi va Admin paneldan o'zgartiriladi.
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float = 0.0) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# ── Telegram bot ─────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "6155982488").replace(" ", "").split(",") if x.strip().isdigit()]

# ── Telegram API (Telethon hisoblar uchun) ───────────────────
TG_API_ID = _int("TG_API_ID", 23031437)
TG_API_HASH = os.getenv("TG_API_HASH", "5e9d1608783f1cb697d0405431d45e2b")

# ── MySQL ─────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = _int("DB_PORT", 3306)
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "uzvendor_bot")
DB_POOL_MIN = _int("DB_POOL_MIN", 2)
DB_POOL_MAX = _int("DB_POOL_MAX", 10)

# ── Sessiyalar papkasi ────────────────────────────────────────
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# ── Fragment API (boshlang'ich, panelda o'zgartiriladi) ──────
FRAGMENT_API_BASE = os.getenv("FRAGMENT_API_BASE", "https://fragment-api.net")
FRAGMENT_SEED = os.getenv("FRAGMENT_SEED", "")          # base64 yoki oddiy seed
FRAGMENT_COOKIES = os.getenv("FRAGMENT_COOKIES", "")    # ixtiyoriy (KYC)
FRAGMENT_API_KEY = os.getenv("FRAGMENT_API_KEY", "")    # v2 rejim uchun auth_key

# ── Spider Service (Server 1) ────────────────────────────────
SPIDER_API_KEY = os.getenv("SPIDER_API_KEY", "")
SPIDER_API_URL = os.getenv("SPIDER_API_URL", "https://api.spider-service.com")

# ── To'lov aniqlash ──────────────────────────────────────────
PAYMENT_BOTS = {"UZCARD": "CardXabarBot", "HUMO": "HumocardBot"}
SCAN_WINDOW_SEC = 900          # shu vaqtdagi depositlar tekshiriladi (15 daq)
MATCH_WINDOW_SEC = 300         # xabar necha sekund ichida bo'lishi kerak
AMOUNT_EPSILON = 0.01          # summa xatolik chegarasi
WATCHER_SLEEP = 3             # watcher sikli orasidagi pauza (sek)

# ── Umumiy ───────────────────────────────────────────────────
ENABLE_PAYMENT_WATCHER = os.getenv("ENABLE_PAYMENT_WATCHER", "1") == "1"
ENABLE_NUMBER_S1 = os.getenv("ENABLE_NUMBER_S1", "1") == "1"
ENABLE_NUMBER_S2 = os.getenv("ENABLE_NUMBER_S2", "1") == "1"
TIMEZONE = os.getenv("TZ", "Asia/Tashkent")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
