"""
@VinexUzBot — Stars/Premium/NFT/Gift/Reaksiya/Raqam xizmat boti.

Ishga tushirish:
    python3 main.py

Ish jarayoni:
  1. MySQL bazasini yaratadi (db.py)
  2. Botni yuradi (aiogram 3)
  3. To'lov aniqlash watcher'ini yuradi (Telethon)
"""
from __future__ import annotations

import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import config
import db
from bot.emoji import reload_emojis
from bot.handlers import base, numbers, orders, services, support, wallet
from bot.handlers.admin import (
    accounts,
    common,
    finance,
    numbers as adm_numbers,
    orders as adm_orders,
    panel,
    services as adm_services,
    settings,
    users,
)
from bot.middlewares import UserMiddleware
from bot.utils.misc import setup_logging
from bot.utils.tg_client import close_all
from bot.utils.watcher import PaymentWatcher

log = logging.getLogger("main")

stop_event = asyncio.Event()


def _install_signal_handlers() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass


async def shutdown(bot: Bot, watcher: PaymentWatcher | None, task: asyncio.Task | None) -> None:
    log.info("Yopilyapti...")
    if watcher:
        watcher.stop()
    if task:
        try:
            await asyncio.wait_for(task, timeout=10)
        except (asyncio.TimeoutError, Exception):
            pass
    try:
        await close_all()
    except Exception:
        pass
    try:
        await bot.session.close()
    except Exception:
        pass
    if db._pool:
        await db.close_db()


async def main() -> None:
    setup_logging()
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    try:
        await db.init_db()
        await reload_emojis()
    except Exception as e:
        log.error("Bazaga ulanishda xato: %s", e)
        log.info("MySQL ma'lumotlarini .env faylida tekshiring (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)")
        return

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    for r in (
        base.router,
        services.router,
        numbers.router,
        wallet.router,
        orders.router,
        support.router,
        panel.router,
        users.router,
        finance.router,
        adm_services.router,
        settings.router,
        accounts.router,
        adm_numbers.router,
        adm_orders.router,
        common.router,
    ):
        dp.include_router(r)

    watcher = PaymentWatcher(bot)
    task = asyncio.create_task(watcher.run()) if config.ENABLE_PAYMENT_WATCHER else None

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Bot ishga tushdi: @%s", (await bot.get_me()).username)
        await dp.start_polling(bot)
    finally:
        await shutdown(bot, watcher, task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
