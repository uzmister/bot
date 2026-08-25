"""
Telethon hisob menejeri.

- Har bir telefon raqam uchun bitta TelegramClient (fayl sessiyasi)
- Buzilgan sessiyani xavfsiz qayta yaratish (namunadagi kabi)
- Admin paneldan hisob qo'shish: kod + 2FA oqimi
"""
from __future__ import annotations

import asyncio
import logging
import os
import re

from telethon import TelegramClient, errors
from telethon.sessions import SQLiteSession

import config
from bot.texts import normalize_phone

log = logging.getLogger("tg_client")

_clients: dict[str, TelegramClient] = {}
_locks: dict[str, asyncio.Lock] = {}


class AccountError(Exception):
    pass


def _lock_for(phone: str) -> asyncio.Lock:
    if phone not in _locks:
        _locks[phone] = asyncio.Lock()
    return _locks[phone]


def session_path(phone: str, subdir: str = "") -> str:
    clean = normalize_phone(phone) or "no_phone"
    folder = os.path.join(config.SESSIONS_DIR, subdir) if subdir else config.SESSIONS_DIR
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{clean}.session")


def _remove_broken(session_file: str) -> None:
    for suffix in ["", "-journal", "-shm", "-wal"]:
        p = session_file + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError as e:
                log.warning("Sessiya fayli o'chirilmadi %s: %s", p, e)


def make_client(phone: str, session_file: str | None = None) -> TelegramClient:
    sf = session_file or session_path(phone)
    try:
        return TelegramClient(sf, config.TG_API_ID, config.TG_API_HASH)
    except (ValueError, Exception) as e:
        log.warning("Sessiya buzilgan (%s), qayta yaratilmoqda: %s", sf, e)
        _remove_broken(sf)
        return TelegramClient(sf, config.TG_API_ID, config.TG_API_HASH)


async def get_client(phone: str, session_file: str | None = None) -> TelegramClient:
    """Ulangan (majburiy emas) klientni qaytaradi."""
    phone = normalize_phone(phone)
    async with _lock_for(phone):
        client = _clients.get(phone)
        if client is None or client.is_closed():
            client = make_client(phone, session_file)
            _clients[phone] = client
        if not client.is_connected():
            try:
                await client.connect()
            except Exception as e:
                raise AccountError(f"Ulanish xatosi: {e}") from e
        return client


async def is_authorized(client: TelegramClient) -> bool:
    try:
        return await client.is_user_authorized()
    except Exception:
        return False


async def drop_client(phone: str, delete_session: bool = False, session_file: str | None = None) -> None:
    phone = normalize_phone(phone)
    client = _clients.pop(phone, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass
    if delete_session:
        _remove_broken(session_file or session_path(phone))


async def close_all() -> None:
    for client in list(_clients.values()):
        try:
            await client.disconnect()
        except Exception:
            pass
    _clients.clear()


# ══════════════════════════════════════════════════════════════
#  LOGIN (admin paneldan hisob qo'shish)
# ══════════════════════════════════════════════════════════════
async def start_login(phone: str) -> dict:
    """Kod yuboradi. {'status': 'code_sent' | 'already'} qaytaradi."""
    client = await get_client(phone)
    if await is_authorized(client):
        me = await client.get_me()
        return {"status": "already", "user": _user_dict(me)}
    res = await client.send_code_request(phone)
    return {"status": "code_sent", "phone_code_hash": res.phone_code_hash}


async def submit_code(phone: str, code: str, phone_code_hash: str) -> dict:
    client = await get_client(phone)
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        me = await client.get_me()
        return {"status": "success", "user": _user_dict(me)}
    except errors.SessionPasswordNeededError:
        return {"status": "need_password"}
    except errors.FloodWaitError as e:
        raise AccountError(f"Juda ko'p urinish, {e.seconds} soniya kutin") from e
    except Exception as e:
        raise AccountError(f"Kod noto'g'ri yoki sessiya muammosi: {e}") from e


async def submit_2fa(phone: str, password: str) -> dict:
    client = await get_client(phone)
    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        return {"status": "success", "user": _user_dict(me)}
    except Exception as e:
        raise AccountError(f"2FA parol noto'g'ri: {e}") from e


def _user_dict(user) -> dict:
    return {
        "id": getattr(user, "id", None),
        "first_name": getattr(user, "first_name", ""),
        "last_name": getattr(user, "last_name", ""),
        "username": getattr(user, "username", ""),
        "phone": getattr(user, "phone", ""),
    }
