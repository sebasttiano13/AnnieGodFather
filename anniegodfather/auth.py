
import asyncio
from typing import Optional

import grpc
from anniegodfather.proto import auth_pb2_grpc, auth_pb2
from grpc import aio


class AuthManager:
    def __init__(self, auth_stub: auth_pb2_grpc.AuthServiceStub, bot_token: str):
        self.auth_stub = auth_stub
        self.bot_token = bot_token
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_mode = False   # False = бот, True = пользователь
        self.lock = asyncio.Lock()

    async def ensure_token(self):
        """Гарантирует наличие действующего access токена"""
        async with self.lock:
            if not self.access_token:
                if self.user_mode:
                    raise RuntimeError("User mode active, but no user login")
                await self.login_bot()
            return self.access_token

    async def login_bot(self):
        """Первичный вход для бота"""
        req = auth_pb2.BotLoginRequest(api_token=self.bot_token)
        resp = await self.auth_stub.LoginBot(req)
        self.access_token = resp.access_token
        self.refresh_token = resp.refresh_token
        self.user_mode = False

    async def login_telegram_user(self, telegram_id: int, username: str):
        """Вход по Telegram ID и username"""
        req = auth_pb2.LoginTelegramRequest(
            telegram_id=str(telegram_id),
            username=username
        )
        resp = await self.auth_stub.LoginTelegram(req)
        self.access_token = resp.access_token
        self.refresh_token = resp.refresh_token
        self.user_mode = True

    async def refresh(self):
        """Обновление access токена"""
        if not self.refresh_token:
            # нет refresh — пробуем логиниться заново
            if self.user_mode:
                raise RuntimeError("Cannot refresh user token without refresh_token")
            await self.login_bot()
            return

        req = auth_pb2.RefreshRequest(refresh_token=self.refresh_token)
        resp = await self.auth_stub.Refresh(req)
        self.access_token = resp.access_token
        self.refresh_token = resp.refresh_token

class AuthInterceptor(aio.ClientInterceptor):
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        access_token = await self.auth_manager.ensure_token()
        metadata = list(client_call_details.metadata or [])
        metadata.append(("authorization", access_token))

        new_details = aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
            compression=client_call_details.compression,
        )

        try:
            return await continuation(new_details, request)
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                await self.auth_manager.refresh()
                new_token = await self.auth_manager.ensure_token()
                metadata[-1] = ("authorization", new_token)
                new_details = new_details._replace(metadata=metadata)
                return await continuation(new_details, request)
            raise