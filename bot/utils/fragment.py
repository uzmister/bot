"""
Fragment API (https://fragment-api.net) — Stars va Premium xarid.

V1 (asosiy): POST /buyStarsWithoutKYC, /buyPremiumWithoutKYC
V2 (ixtiyoriy): POST /v2/... /create + /pay + /check

Seed va cookies base64 formatda kutiladi — bot o'zi kodlaydi.
Sozlamalar DB `settings` jadvalidan o'qiladi (admin panel).
"""
from __future__ import annotations

import logging

import aiohttp

import db
from bot.utils.misc import b64_encode_auto

log = logging.getLogger("fragment")


class FragmentError(Exception):
    pass


async def _get_cfg() -> dict:
    base = await db.get_setting("fragment_api_base", "https://fragment-api.net")
    seed = await db.get_setting("fragment_seed", "")
    cookies = await db.get_setting("fragment_cookies", "")
    api_key = await db.get_setting("fragment_api_key", "")
    version = (await db.get_setting("fragment_api_version", "v1")).strip().lower()
    return {
        "base": base.rstrip("/"),
        "seed": seed,
        "cookies": cookies,
        "api_key": api_key,
        "version": version if version in ("v1", "v2") else "v1",
    }


async def _post(path: str, payload: dict, timeout: int = 120) -> dict:
    cfg = await _get_cfg()
    url = cfg["base"] + path
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 200:
                    return body
                raise FragmentError(body.get("message") or f"HTTP {resp.status}")
    except aiohttp.ClientError as e:
        raise FragmentError(f"Fragment API'ga ulanishda xato: {e}") from e
    except ValueError:
        raise FragmentError("Fragment API noto'g'ri javob qaytardi") from None


async def _get(path: str, params: dict, timeout: int = 60) -> dict:
    cfg = await _get_cfg()
    url = cfg["base"] + path
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 200:
                    return body
                raise FragmentError(body.get("message") or f"HTTP {resp.status}")
    except aiohttp.ClientError as e:
        raise FragmentError(f"Fragment API'ga ulanishda xato: {e}") from e
    except ValueError:
        raise FragmentError("Fragment API noto'g'ri javob qaytardi") from None


def _check(result: dict) -> dict:
    if not isinstance(result, dict):
        raise FragmentError("Fragment API noto'g'ri javob")
    if not result.get("success", False):
        raise FragmentError(str(result.get("message", "Noma'lum xatolik")))
    return result


# ══════════════════════════════════════════════════════════════
#  STAR
# ══════════════════════════════════════════════════════════════
async def buy_stars_v1(username: str, amount: int) -> dict:
    cfg = await _get_cfg()
    payload = {
        "username": username,
        "amount": int(amount),
        "seed": b64_encode_auto(cfg["seed"]),
    }
    if cfg["cookies"]:
        payload["fragment_cookies"] = b64_encode_auto(cfg["cookies"])
    result = await _post("/buyStarsWithoutKYC", payload)
    return _check(result)


async def buy_stars_v2(username: str, amount: int) -> dict:
    cfg = await _get_cfg()
    if not cfg["api_key"]:
        raise FragmentError("V2 rejim uchun auth_key kiritilmagan")
    created = await _post("/v2/buyStarsWithoutKYC/create", {
        "username": username,
        "amount": int(amount),
        "auth_key": cfg["api_key"],
        "custom_order_info": f"uzvendor-{username}",
    })
    created = _check(created)
    order_uuid = created.get("order_id") or created.get("order_uuid")
    cost = created.get("cost")
    if not order_uuid or cost is None:
        raise FragmentError("Order yaratilmadi (order_id/cost topilmadi)")
    paid = await _post("/v2/buyStarsWithoutKYC/pay", {
        "order_uuid": order_uuid,
        "auth_key": cfg["api_key"],
        "cost": cost,
    })
    return _check(paid)


async def buy_stars(username: str, amount: int) -> dict:
    cfg = await _get_cfg()
    if cfg["version"] == "v2":
        return await buy_stars_v2(username, amount)
    return await buy_stars_v1(username, amount)


# ══════════════════════════════════════════════════════════════
#  PREMIUM
# ══════════════════════════════════════════════════════════════
async def buy_premium_v1(username: str, duration: int) -> dict:
    cfg = await _get_cfg()
    payload = {
        "username": username,
        "duration": int(duration),
        "seed": b64_encode_auto(cfg["seed"]),
    }
    if cfg["cookies"]:
        payload["fragment_cookies"] = b64_encode_auto(cfg["cookies"])
    result = await _post("/buyPremiumWithoutKYC", payload)
    return _check(result)


async def buy_premium_v2(username: str, duration: int) -> dict:
    cfg = await _get_cfg()
    if not cfg["api_key"]:
        raise FragmentError("V2 rejim uchun auth_key kiritilmagan")
    created = await _post("/v2/buyPremiumWithoutKYC/create", {
        "username": username,
        "duration": int(duration),
        "auth_key": cfg["api_key"],
        "custom_order_info": f"uzvendor-{username}",
    })
    created = _check(created)
    order_uuid = created.get("order_id") or created.get("order_uuid")
    cost = created.get("cost")
    if not order_uuid or cost is None:
        raise FragmentError("Order yaratilmadi (order_id/cost topilmadi)")
    paid = await _post("/v2/buyPremiumWithoutKYC/pay", {
        "order_uuid": order_uuid,
        "auth_key": cfg["api_key"],
        "cost": cost,
    })
    return _check(paid)


async def buy_premium(username: str, duration: int) -> dict:
    cfg = await _get_cfg()
    if cfg["version"] == "v2":
        return await buy_premium_v2(username, duration)
    return await buy_premium_v1(username, duration)


# ══════════════════════════════════════════════════════════════
#  BOSHQA
# ══════════════════════════════════════════════════════════════
async def get_balance() -> float:
    cfg = await _get_cfg()
    if cfg["version"] == "v2" and cfg["api_key"]:
        try:
            result = await _get("/v2/getBalance", {"auth_key": cfg["api_key"]})
            return float(_check(result).get("balance", 0.0))
        except FragmentError:
            pass
    try:
        result = await _post("/getBalance", {"seed": b64_encode_auto(cfg["seed"])})
        return float(_check(result).get("balance", 0.0))
    except FragmentError:
        return 0.0


async def get_user_info(username: str) -> dict:
    cfg = await _get_cfg()
    payload = {"username": username}
    if cfg["cookies"]:
        payload["fragment_cookies"] = b64_encode_auto(cfg["cookies"])
    if cfg["version"] == "v2" and cfg["api_key"]:
        try:
            result = await _get("/v2/getUserInfo", {"username": username, "auth_key": cfg["api_key"]})
            return _check(result)
        except FragmentError:
            pass
    result = await _post("/getUserInfo", payload)
    return _check(result)
