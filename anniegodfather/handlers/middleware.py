from collections.abc import Callable
from typing import Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from anniegodfather.clients import DadClient
from anniegodfather.exceptions import DadClientRegistrationAlreadyExistException, AuthLoginUserNotFoundError
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


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except AuthLoginUserNotFoundError:
            if isinstance(event, Update):
                await event.message.answer("Аккаунт не найден. Используйте /register для регистрации")
                return None
        except DadClientRegistrationAlreadyExistException:
            if isinstance(event, Update):
                await event.message.answer("Пользователь с таким именем уже существует. Выберите другое")
                return None
        except Exception:
            raise