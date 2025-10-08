# -*- coding: utf-8 -*-

import asyncio
import os

from aiogram import Bot, Dispatcher, html, types, F
from aiogram.client.session import aiohttp
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from pydantic.v1.validators import anystr_strip_whitespace
from telethon import TelegramClient

from logger import logger
from settings import config
from clients import DadClient

dp = Dispatcher()
bot = Bot(token=config.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

client = TelegramClient(f"sessions/media_session", config.API_ID, config.API_HASH)

MB = 1 << 20


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


async def download_with_telethon(file_id, file_name, chat_id, msg_id):

    # Получаем файл по file_id
    entity = await client.get_entity(chat_id)
    file = await client.get_messages(entity=entity, ids=msg_id)

    if file and file.media:
        # Скачиваем медиа
        await client.download_media(file.media, file=os.path.join(config.SAVE_FOLDER, file_name))


@dp.message(F.photo | F.video | F.audio | F.document)
async def save_media(message: types.Message):

    if message.photo:
        # Если это фото, берем последний элемент (самое высокое качество)
        file_id = message.photo[-1].file_id
        file_name = f"photo_{file_id}.jpg"
        logger.info("Catch photo %s" % file_name)
    elif message.document:
        file_size = message.document.file_size
        file_id = message.document.file_id
        file_name = message.document.file_name
        logger.info("Catch document %s" % file_name)

        # If file more than 20 Mb
        if file_size > 20 * MB:
        # Если это документ, берем file_id и оригинальное имя файла
            await download_with_telethon(file_id, file_name, message.chat.id, message.message_id)
            return

    elif message.video:
        file_id = message.video.file_id
        file_name = f"video_{file_id}.mp4"
        logger.info("Catch video %s" % file_name)
    elif message.audio:
        file_id = message.audio.file_id
        file_name = f"audio_{file_id}.mp3"
        logger.info("Catch audio %s" % file_name)
    else:
        await message.reply("Этот тип медиа не поддерживается.")
        return

    # Получаем информацию о файле
    file = await bot.get_file(file_id)
    file_path = file.file_path


    # Скачиваем файл
    file_location = os.path.join(config.SAVE_FOLDER, file_name)
    await bot.download_file(file_path, file_location)

    # Получаем подписанную ссылку
    dad_client = DadClient("127.0.0.1:8081")
    url = await dad_client.fetch_post_url()
    logger.info("GET URL: %s", url)
    # --- загружаем на S3 через presigned URL ---
    async with aiohttp.ClientSession() as session:
        with open(file_location, "rb") as f:
            async with session.put(url.url, data=f) as resp:
                if resp.status == 200:
                    logger.info("File saved to S3 %s" % file_name)
                    await message.reply(f"✅ Файл загружен в S3: {file_name}")
                else:
                    text = await resp.text()
                    await message.reply(f"⚠️ Ошибка при загрузке ({resp.status}): {text}")

    os.remove(file_location)

@dp.message(F.text.startswith('show'))
async def test_fetch_get_url(message: Message) -> str:
    _, filename = message.text.split(maxsplit=1)
    dad_client = DadClient("127.0.0.1:8081")
    url = await dad_client.fetch_get_url(filename=filename)
    await message.answer(url.url)

@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")

async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    # And the run events dispatching

    await client.start(bot_token=config.TELEGRAM_TOKEN)

    await dp.start_polling(bot, )

    await client.disconnect()

if __name__ == "__main__":
    logger.info("Starting Annie bot")
    asyncio.run(main())
