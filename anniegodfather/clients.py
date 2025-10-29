# -*- coding: utf-8 -*-
from collections import defaultdict
from typing import Any

from grpc import aio
from anniegodfather.proto import (
    anniedad_pb2_grpc as father_grpc,
    anniedad_pb2 as father_pb2,
    auth_pb2_grpc as auth_grpc,
    auth_pb2 as auth_pb2
)


class DadClient:
    def __init__(self, server: str, bot_api_key: str):
        self.bot_api_key = bot_api_key
        self.channel = aio.insecure_channel(server)

        self.auth_stub = auth_grpc.AuthServiceStub(self.channel)
        self.media_stub = father_grpc.MediaStub(self.channel)

        # telegram_id → токены
        self.user_tokens = defaultdict(dict)

    async def ensure_user_token(self, telegram_id: int) -> str:
        """Если нет access токена, логиним пользователя"""
        tokens = self.user_tokens.get(telegram_id)
        if not tokens or not tokens.get("access_token"):
            req = auth_pb2.BotLoginRequest(
                telegram_id=telegram_id,
            )
            resp = await self.auth_stub.LoginBot(req, metadata=[("x-api-key", self.bot_api_key)])
            self.user_tokens[telegram_id] = {
                "access_token": resp.access_token,
                "refresh_token": resp.refresh_token,
            }
        return self.user_tokens[telegram_id]["access_token"]

    async def call_with_auth(self, stub_method, request, telegram_id=None):
        """Универсальный вызов любого RPC"""
        metadata = [("x-api-key", self.bot_api_key)]

        if telegram_id:
            access_token = await self.ensure_user_token(telegram_id)
            metadata.append(("authorization", f"{access_token}"))

        return await stub_method(request, metadata=metadata)

    # ====== Пример методов ======

    async def fetch_post_url(self, filename: str, telegram_id=None):
        request = father_pb2.PostMediaRequest(filename=filename)
        resp = await self.call_with_auth(
            self.media_stub.PostURL,
            request,
            telegram_id=telegram_id,
        )
        return resp.url

    async def fetch_get_url(self, filename: str, telegram_id=None) -> Any:
        """Gets presighned S3 get url from anniedad backend"""

        request = father_pb2.GetMediaRequest(filename=filename)
        resp = await self.call_with_auth(
            self.media_stub.GetURL,
            request,
            telegram_id=telegram_id,
        )

        return resp