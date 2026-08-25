"""
Spider Service (https://api.spider-service.com) — Server 1 raqam xizmati.

GET ?apiKay=KEY&action=...
  getBalance | getCountrys | getInfo | getNumber&country=PS[&server=1] | getCode&hash_code=...
"""
from __future__ import annotations

import logging

import aiohttp

import db

log = logging.getLogger("spider")


class SpiderError(Exception):
    pass


async def _cfg() -> tuple[str, str]:
    key = await db.get_setting("spider_api_key", "")
    url = (await db.get_setting("spider_api_url", "https://api.spider-service.com")).rstrip("/")
    return url, key


def _pick(obj: dict, keys: list[str], default=None):
    for k in keys:
        if isinstance(obj, dict) and obj.get(k) not in (None, ""):
            return obj[k]
    return default


async def _call(action: str, **params) -> dict:
    url, key = await _cfg()
    if not key:
        raise SpiderError("Spider API kaliti kiritilmagan (Admin → Raqam → Server 1)")
    qs = {"apiKay": key, "action": action, **params}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=qs, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                data = await resp.json(content_type=None)
                if not isinstance(data, dict):
                    raise SpiderError(f"Noto'g'ri javob: HTTP {resp.status}")
                return data
    except aiohttp.ClientError as e:
        raise SpiderError(f"Spider xizmatiga ulanishda xato: {e}") from e
    except ValueError:
        raise SpiderError("Spider xizmatidan noto'g'ri javob keldi") from None


def _ok(data: dict) -> bool:
    status = str(_pick(data, ["status", "success", "ok"], "")).lower()
    return status in ("success", "ok", "true", "1", "active", "") or bool(data.get("code") or data.get("number"))


def _msg(data: dict) -> str:
    return str(_pick(data, ["message", "error", "msg", "details"], "Noma'lum xatolik"))


async def get_balance() -> float:
    data = await _call("getBalance")
    if not _ok(data):
        raise SpiderError(_msg(data))
    raw = _pick(data, ["balance", "wallet", "amount", "data"], 0)
    if isinstance(raw, dict):
        raw = _pick(raw, ["balance", "amount", "total"], 0)
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


async def get_info() -> dict:
    return await _call("getInfo")


async def get_countries() -> list[dict]:
    """[{'country': 'PS', 'name': 'Falastin', ...}, ...] — turli formatlarni o'qiydi."""
    data = await _call("getCountrys")
    raw = _pick(data, ["countries", "data", "list", "result"], [])
    if isinstance(raw, dict):
        raw = _pick(raw, ["countries", "list", "data"], [])
    out: list[dict] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.append({"country": item.upper(), "name": item})
            elif isinstance(item, dict):
                code = _pick(item, ["country", "code", "iso", "id"], "")
                name = _pick(item, ["name", "country_name", "title", "label"], code)
                if code:
                    out.append({"country": str(code).upper(), "name": str(name)})
    return out


async def get_number(country: str, server: int = 1) -> dict:
    """{'number': '+970...', 'hash_code': '...'} qaytaradi."""
    data = await _call("getNumber", country=country.upper(), server=server)
    if not _ok(data):
        raise SpiderError(_msg(data))
    number = _pick(data, ["number", "phone", "phonenumber", "value"], "")
    hash_code = _pick(data, ["hash_code", "hash", "id", "order_id"], "")
    if not number:
        # nested data
        nested = _pick(data, ["data", "result"], {})
        if isinstance(nested, dict):
            number = _pick(nested, ["number", "phone", "phonenumber"], "")
            hash_code = _pick(nested, ["hash_code", "hash", "id"], hash_code)
    if not number:
        raise SpiderError(f"Raqam topilmadi: {_msg(data)}")
    return {"number": str(number), "hash_code": str(hash_code or "")}


async def get_code(hash_code: str) -> str:
    data = await _call("getCode", hash_code=hash_code)
    if not _ok(data):
        raise SpiderError(_msg(data))
    code = _pick(data, ["code", "sms", "message", "value"], "")
    nested = _pick(data, ["data", "result"], {})
    if not code and isinstance(nested, dict):
        code = _pick(nested, ["code", "sms", "value"], "")
    if not code:
        raise SpiderError(f"Kod hali kelmagan: {_msg(data)}")
    return str(code)
