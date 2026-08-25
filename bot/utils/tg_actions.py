"""
Telethon orqali Telegram hisob bilan bajariladigan amallar:
- Postga paid (star) reaction bosish  → messages.SendPaidReaction
- Gift (Star Gift) yuborish           → payments.GetPaymentForm + SendStarsForm
"""
from __future__ import annotations

import logging
import random
import re

from telethon import TelegramClient, types
from telethon.tl.functions.messages import SendPaidReactionRequest
from telethon.tl.functions.payments import (
    GetPaymentFormRequest,
    SendStarsFormRequest,
)
from telethon.tl.types import (
    InputInvoiceStarGift,
    PaidReactionPrivacyDefault,
    PeerChannel,
)

log = logging.getLogger("tg_actions")


class TgActionError(Exception):
    pass


def parse_post_link(link: str) -> tuple[str, int]:
    """t.me linkdan (peer, msg_id) ajratadi. Peer — username yoki PeerChannel."""
    if not link:
        raise TgActionError("Post havolasi kiritilmagan")
    m = re.search(r"t\.me/(?:c/)?([^/\s?]+)/(\d+)", link)
    if not m:
        raise TgActionError(
            "Havola formati noto'g'ri. Namuna: https://t.me/kanalusername/123"
        )
    peer_raw, msg_id = m.group(1), int(m.group(2))
    if peer_raw.isdigit():
        # Yopiq kanal: t.me/c/1234567890/123
        peer: object = PeerChannel(channel_id=int(peer_raw))
    else:
        peer = peer_raw
    return peer, msg_id  # type: ignore[return-value]


async def resolve_post(client: TelegramClient, link: str):
    """(input_peer, msg_id) — get_input_entity orqali hal qiladi."""
    peer_raw, msg_id = parse_post_link(link)
    try:
        peer = await client.get_input_entity(peer_raw)  # type: ignore[arg-type]
    except Exception as e:
        raise TgActionError(
            "Post topilmadi. Hisob kanal a'zosi ekanini tekshiring "
            "(yopiq kanal bo'lsa, hisob kanalga qo'shilgan bo'lishi kerak)."
        ) from e
    return peer, msg_id


async def send_paid_reaction(
    client: TelegramClient,
    peer,
    msg_id: int,
    count: int,
    anonymous: bool = True,
) -> dict:
    """count dona star bilan paid reaction yuboradi."""
    count = max(1, int(count))
    try:
        await client(
            SendPaidReactionRequest(
                peer=peer,
                msg_id=msg_id,
                count=count,
                random_id=random.getrandbits(63),
                private=PaidReactionPrivacyDefault()
                if not anonymous
                else types.PaidReactionPrivacyAnonymous(),
            )
        )
        return {"ok": True, "count": count}
    except Exception as e:
        raise TgActionError(f"Paid reaction yuborilmadi: {e}") from e


async def send_star_gift(
    client: TelegramClient,
    user_peer,
    gift_id: int,
    hide_name: bool = True,
    message: str | None = None,
) -> dict:
    """
    Star Gift yuborish: GetPaymentForm -> SendStarsForm (hisobning
    o'z stars balansidan to'lanadi).
    """
    try:
        kwargs = {"peer": user_peer, "gift_id": int(gift_id), "hide_name": hide_name}
        if message:
            kwargs["message"] = message
        invoice = InputInvoiceStarGift(**kwargs)
        form = await client(GetPaymentFormRequest(invoice=invoice))
        result = await client(
            SendStarsFormRequest(form_id=form.form_id, invoice=invoice)
        )
        return {"ok": True, "result": result}
    except Exception as e:
        raise TgActionError(f"Gift yuborilmadi: {e}") from e
