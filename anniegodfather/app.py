# -*- coding: utf-8 -*-

import asyncio
import os

from aiogram import Bot, Dispatcher, html, types, F
from aiogram.client.session import aiohttp
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from anniegodfather.handlers.middleware import ClientMiddleware, ErrorMiddleware
from pydantic.v1.validators import anystr_strip_whitespace
from telethon import TelegramClient

from logger import logger
from settings import config
from clients import DadClient
from anniegodfather.handlers import default_router, cmd_router, media_router

MB = 1 << 20

async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    # And the run events dispatching
    dp = Dispatcher()
    bot = Bot(token=config.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


    client = TelegramClient(f"sessions/media_session", config.API_ID, config.API_HASH)
    telethon_client = await client.start(bot_token=config.TELEGRAM_TOKEN)

    dad = DadClient("127.0.0.1:8081", config.DAD_API_KEY)

    dp.update.outer_middleware(ClientMiddleware(dad, telethon_client))
    dp.update.outer_middleware(ErrorMiddleware())

    dp.include_routers(cmd_router, media_router)
    dp.include_router(default_router)



    await dp.start_polling(bot, )
    await telethon_client.disconnect()

if __name__ == "__main__":
    logger.info("Starting Annie bot")
    asyncio.run(main())
