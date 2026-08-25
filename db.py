"""
MySQL ma'lumotlar bazasi — aiomysql pool + sxema + yordamchi funksiyalar.
Barcha so'rovlar DictCursor bilan dict qaytaradi.
"""
import asyncio
import json
import logging
from typing import Any, Iterable, Optional

import aiomysql

import config

log = logging.getLogger("db")

_pool: Optional[aiomysql.Pool] = None

# ══════════════════════════════════════════════════════════════
#  SXEMA
# ══════════════════════════════════════════════════════════════
SCHEMA: list[str] = [
    """CREATE TABLE IF NOT EXISTS users (
        id            BIGINT PRIMARY KEY,
        username      VARCHAR(64)  DEFAULT NULL,
        first_name    VARCHAR(128) DEFAULT '',
        last_name     VARCHAR(128) DEFAULT '',
        phone         VARCHAR(32)  DEFAULT NULL,
        balance       DECIMAL(14,2) NOT NULL DEFAULT 0,
        ref_by        BIGINT       DEFAULT NULL,
        ref_earned    DECIMAL(14,2) NOT NULL DEFAULT 0,
        order_count   INT          NOT NULL DEFAULT 0,
        is_banned     TINYINT      NOT NULL DEFAULT 0,
        created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen     DATETIME     DEFAULT NULL,
        INDEX idx_users_ref (ref_by),
        INDEX idx_users_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS admins (
        user_id     BIGINT PRIMARY KEY,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS settings (
        skey    VARCHAR(64) PRIMARY KEY,
        svalue  TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS payment_methods (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        method      VARCHAR(10) NOT NULL,
        card_number VARCHAR(32) NOT NULL,
        card_name   VARCHAR(128) DEFAULT '',
        is_active   TINYINT NOT NULL DEFAULT 1,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS deposits (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        user_id       BIGINT NOT NULL,
        amount        DECIMAL(14,2) NOT NULL,
        method        VARCHAR(10) NOT NULL,
        card_digits   VARCHAR(8) DEFAULT NULL,
        status        ENUM('pending','success','cancel') NOT NULL DEFAULT 'pending',
        note          TEXT,
        matched_msg_id BIGINT DEFAULT NULL,
        created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at    DATETIME DEFAULT NULL,
        INDEX idx_dep_status (status),
        INDEX idx_dep_user (user_id),
        INDEX idx_dep_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS transactions (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        user_id       BIGINT NOT NULL,
        type          VARCHAR(32) NOT NULL,
        amount        DECIMAL(14,2) NOT NULL,
        balance_after DECIMAL(14,2) NOT NULL,
        note          TEXT,
        created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_tx_user (user_id),
        INDEX idx_tx_type (type),
        INDEX idx_tx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS orders (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        user_id      BIGINT NOT NULL,
        service      VARCHAR(32) NOT NULL,
        target       VARCHAR(255) DEFAULT NULL,
        qty          INT DEFAULT NULL,
        stars        INT DEFAULT NULL,
        price        DECIMAL(14,2) NOT NULL DEFAULT 0,
        status       ENUM('pending','processing','success','cancel','fail') NOT NULL DEFAULT 'pending',
        external_ref VARCHAR(255) DEFAULT NULL,
        number       VARCHAR(32) DEFAULT NULL,
        hash_code    VARCHAR(255) DEFAULT NULL,
        details      TEXT,
        admin_note   TEXT,
        created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at   DATETIME DEFAULT NULL,
        INDEX idx_ord_user (user_id),
        INDEX idx_ord_status (status),
        INDEX idx_ord_service (service),
        INDEX idx_ord_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS tg_accounts (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        phone         VARCHAR(32) NOT NULL,
        name          VARCHAR(128) DEFAULT '',
        acc_type      VARCHAR(24) NOT NULL,
        session_file  VARCHAR(255) NOT NULL,
        twofa         VARCHAR(255) DEFAULT NULL,
        status        ENUM('active','ban','error','disabled') NOT NULL DEFAULT 'active',
        last_error    TEXT,
        success_count INT NOT NULL DEFAULT 0,
        created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at    DATETIME DEFAULT NULL,
        INDEX idx_acc_type (acc_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS number_stock (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        phone        VARCHAR(32) NOT NULL,
        country      VARCHAR(8)  NOT NULL DEFAULT 'UZ',
        price        DECIMAL(14,2) NOT NULL DEFAULT 0,
        session_file VARCHAR(255) DEFAULT NULL,
        twofa        VARCHAR(255) DEFAULT NULL,
        status       ENUM('available','reserved','sold','removed') NOT NULL DEFAULT 'available',
        buyer_id     BIGINT DEFAULT NULL,
        order_id     INT DEFAULT NULL,
        note         TEXT,
        created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        sold_at      DATETIME DEFAULT NULL,
        INDEX idx_stock_status (status),
        INDEX idx_stock_country (country)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS number_s1_countries (
        country      VARCHAR(8) PRIMARY KEY,
        country_name VARCHAR(128) DEFAULT '',
        price        DECIMAL(12,2) NOT NULL DEFAULT 0,
        enabled      TINYINT NOT NULL DEFAULT 1,
        updated_at   DATETIME DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS tickets (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        user_id      BIGINT NOT NULL,
        subject      VARCHAR(255) DEFAULT '',
        message      TEXT,
        answer       TEXT,
        status       ENUM('open','closed') NOT NULL DEFAULT 'open',
        created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        answered_at  DATETIME DEFAULT NULL,
        INDEX idx_ticket_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
]

# ── Boshlang'ich sozlamalar ──────────────────────────────────
DEFAULT_SETTINGS: dict[str, str] = {
    "welcome_text": "Xush kelibsiz, {name}! 🎉\n\nUshbu bot orqali Telegram Stars, Premium, NFT, Gift olish, postga stars bosish va virtual raqam olish xizmatlaridan foydalanishingiz mumkin.\n\nKerakli bo'limni tanlang 👇",
    "faq_text": "❓ Tez-tez beriladigan savollar\n\n1️⃣ Xizmat narxlari qayerda ko'rsatilgan?\n— Har bir bo'limda narxlar ko'rsatilgan bo'ladi.\n\n2️⃣ To'lov qachon qo'shiladi?\n— To'lov qilingach, avtomatik tekshiriladi va balansga qo'shiladi.\n\n3️⃣ Buyurtma bajarilmasa nima bo'ladi?\n— Pulingiz balansga to'liq qaytariladi.\n\n4️⃣ Yordam kerakmi?\n— Murojaat bo'limi orqali yozing.",
    "support_link": "",
    "channel_link": "",
    "channel_username": "",
    "min_deposit": "10000",
    "min_withdraw": "50000",
    "stars_min": "50",
    "stars_packages": json.dumps([
        {"amount": 50, "price": 18000},
        {"amount": 100, "price": 34000},
        {"amount": 200, "price": 65000},
        {"amount": 500, "price": 155000},
        {"amount": 1000, "price": 300000},
    ]),
    "premium_3": "55000",
    "premium_6": "105000",
    "premium_12": "195000",
    "nft_price": "100000",
    "gift_price": "50000",
    "gift_id": "",
    "gift_name": "Sovg'a",
    "reaction_price_per_star": "300",
    "reaction_min_stars": "1",
    "reaction_max_stars": "25",
    "services_enabled": json.dumps({
        "stars": 1, "premium": 1, "nft": 1, "gift": 1,
        "reaction": 1, "number": 1,
    }),
    "referral_enabled": "1",
    "referral_percent": "5",
    "number_s1_enabled": "1",
    "number_s2_enabled": "1",
    "watcher_enabled": "1",
    "fragment_api_base": config.FRAGMENT_API_BASE,
    "fragment_seed": config.FRAGMENT_SEED,
    "fragment_cookies": config.FRAGMENT_COOKIES,
    "fragment_api_key": config.FRAGMENT_API_KEY,
    "fragment_api_version": "v1",  # v1 | v2
    "spider_api_key": config.SPIDER_API_KEY,
    "spider_api_url": config.SPIDER_API_URL,
    "emoji_ids": "{}",
    "announcement": "",
}


# ══════════════════════════════════════════════════════════════
#  POOL / INIT
# ══════════════════════════════════════════════════════════════
async def init_db() -> None:
    global _pool
    if _pool is not None:
        return
    try:
        _pool = await aiomysql.create_pool(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=config.DB_PASSWORD,
            db=config.DB_NAME, autocommit=True,
            minsize=config.DB_POOL_MIN, maxsize=config.DB_POOL_MAX,
            cursorclass=aiomysql.DictCursor,
        )
    except Exception as e:  # baza hali mavjud emas — yaratamiz
        log.warning("Pool yaratishda xato, bazani yaratishga harakat qilamiz: %s", e)
        conn = await aiomysql.connect(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=config.DB_PASSWORD,
            autocommit=True, cursorclass=aiomysql.DictCursor,
        )
        async with conn.cursor() as cur:
            await cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.close()
        _pool = await aiomysql.create_pool(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=config.DB_PASSWORD,
            db=config.DB_NAME, autocommit=True,
            minsize=config.DB_POOL_MIN, maxsize=config.DB_POOL_MAX,
            cursorclass=aiomysql.DictCursor,
        )

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            for ddl in SCHEMA:
                await cur.execute(ddl)
            for key, value in DEFAULT_SETTINGS.items():
                await cur.execute(
                    "INSERT IGNORE INTO settings (skey, svalue) VALUES (%s, %s)",
                    (key, value),
                )
    log.info("Baza tayyor: %s", config.DB_NAME)


async def close_db() -> None:
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


# ══════════════════════════════════════════════════════════════
#  UMUMIY YORDAMCHILAR
# ══════════════════════════════════════════════════════════════
async def fetchone(sql: str, args: Iterable[Any] = ()) -> Optional[dict]:
    if _pool is None:
        raise RuntimeError("DB pool tayyor emas")
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(args))
            return await cur.fetchone()


async def fetchall(sql: str, args: Iterable[Any] = ()) -> list[dict]:
    if _pool is None:
        raise RuntimeError("DB pool tayyor emas")
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(args))
            return await cur.fetchall()


async def fetchval(sql: str, args: Iterable[Any] = (), default: Any = None) -> Any:
    row = await fetchone(sql, args)
    if not row:
        return default
    return next(iter(row.values()))


async def execute(sql: str, args: Iterable[Any] = ()) -> int:
    """1 ta yozish so'rovi. lastrowid qaytaradi."""
    if _pool is None:
        raise RuntimeError("DB pool tayyor emas")
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(args))
            return cur.lastrowid or 0


async def execute_rowcount(sql: str, args: Iterable[Any] = ()) -> int:
    """Tasirlangan qatorlar sonini qaytaradi (masalan, UPDATE uchun)."""
    if _pool is None:
        raise RuntimeError("DB pool tayyor emas")
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(args))
            return cur.rowcount


async def executemany(sql: str, args: Iterable[Iterable[Any]]) -> None:
    if _pool is None:
        raise RuntimeError("DB pool tayyor emas")
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(sql, [tuple(a) for a in args])


# ══════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════
async def get_setting(key: str, default: str = "") -> str:
    val = await fetchval("SELECT svalue FROM settings WHERE skey=%s", (key,), default)
    return val if val is not None else default


async def set_setting(key: str, value: str) -> None:
    await execute(
        "INSERT INTO settings (skey, svalue) VALUES (%s,%s) "
        "ON DUPLICATE KEY UPDATE svalue=VALUES(svalue)",
        (key, value),
    )


async def get_settings(keys: Iterable[str]) -> dict[str, str]:
    keys = list(keys)
    if not keys:
        return {}
    rows = await fetchall(
        f"SELECT skey, svalue FROM settings WHERE skey IN ({','.join(['%s'] * len(keys))})",
        keys,
    )
    return {r["skey"]: r["svalue"] for r in rows}


async def get_setting_json(key: str, default: Any = None) -> Any:
    raw = await get_setting(key)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


async def set_setting_json(key: str, value: Any) -> None:
    await set_setting(key, json.dumps(value, ensure_ascii=False))
