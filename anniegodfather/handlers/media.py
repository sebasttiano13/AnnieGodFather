import os

from aiogram import Router, F, types, Bot
from aiogram.client.session import aiohttp
from aiogram.types import Message
from anniegodfather.clients import DadClient
from anniegodfather.logger import logger
from anniegodfather.settings import config
from telethon import TelegramClient
MB = 1 << 20

media_router = Router()

async def download_with_telethon(client, file_id, file_name, chat_id, msg_id):

    # Получаем файл по file_id
    entity = await client.get_entity(chat_id)
    file = await client.get_messages(entity=entity, ids=msg_id)

    if file and file.media:
        # Скачиваем медиа
        await client.download_media(file.media, file=os.path.join(config.SAVE_FOLDER, file_name))


@media_router.message(F.photo | F.video | F.audio | F.document)
async def save_media(message: types.Message, dad: DadClient, telethon: TelegramClient, bot: Bot):
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
            await download_with_telethon(telethon, file_id, file_name, message.chat.id, message.message_id)
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
    url = await dad.fetch_post_url(file_name)
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

@media_router.message(F.text.startswith('show'))
async def test_fetch_get_url(message: Message, dad: DadClient) -> str:
    _, filename = message.text.split(maxsplit=1)
    url = await dad.fetch_get_url(filename=filename)
    await message.answer(url.url)
