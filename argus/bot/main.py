import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.handlers import start, investigate, results

logger = logging.getLogger(__name__)


async def start_bot(token: str):
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(investigate.router)
    dp.include_router(results.router)

    logger.info("Starting Argus Telegram bot (polling mode)")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
