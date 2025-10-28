from collections.abc import Callable
from typing import Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from anniegodfather.clients import DadClient
from telethon.client import TelegramClient

class ClientMiddleware(BaseMiddleware):
    def __init__(self, dad: DadClient, telethon: TelegramClient):
        self.dad = dad
        self.telethon = telethon

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Добавляем клиент в data
        data['dad'] = self.dad
        data['telethon'] = self.telethon
        return await handler(event, data)