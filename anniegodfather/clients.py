# -*- coding: utf-8 -*-
from typing import Any

import grpc
from grpc import aio

from anniegodfather.auth import AuthInterceptor, AddApiKeyInterceptor
from anniegodfather.exceptions import DadClientRegistrationError, DadClientRegistrationAlreadyExistException
from anniegodfather.logger import logger
from anniegodfather.proto import (
    anniedad_pb2_grpc as father_grpc,
    anniedad_pb2 as father_pb2,
    auth_pb2_grpc as auth_grpc,
    auth_pb2 as auth_pb2
)


class DadClient:
    def __init__(self, server: str, bot_api_key: str):
        self.auth_interceptor = AuthInterceptor(server, bot_api_key)
        api_key_interceptor = AddApiKeyInterceptor(bot_api_key)
        aio_channel = aio.insecure_channel(server, interceptors=[api_key_interceptor, self.auth_interceptor])
        auth_stub = auth_grpc.AuthServiceStub(aio_channel)
        self.media_stub = father_grpc.MediaStub(aio_channel)
        self.auth_stub = auth_stub
        self._api_key_metadata = ('x-api-key', bot_api_key)


    async def register_user(self, telegram_id: int, username: str):
        request = auth_pb2.TelegramRegisterRequest(telegram_id=telegram_id, username=username)
        try:
            resp = await self.auth_stub.RegisterTelegram(request)
            await self.auth_interceptor.save_tokens(telegram_id, resp.access_token, resp.refresh_token)
        except grpc.aio.AioRpcError as err:
            if err.code() == grpc.StatusCode.ALREADY_EXISTS:
                logger.info(f"Bad request to register new user {username} and id {telegram_id} - already exists")
                raise DadClientRegistrationAlreadyExistException("user already exist")
        except Exception as err:
            logger.error("Failed to register new user:", err)
            raise DadClientRegistrationError()

    async def fetch_post_url(self, filename: str, telegram_id: int = None):
        await self.auth_interceptor.set_current_user(telegram_id)
        request = father_pb2.PostMediaRequest(filename=filename)
        resp = await self.media_stub.PostURL(request)
        return resp.url

    async def fetch_get_url(self, filename: str, telegram_id=None) -> Any:
        """Gets presighned S3 get url from anniedad backend"""
        await self.auth_interceptor.set_current_user(telegram_id)
        request = father_pb2.GetMediaRequest(filename=filename)
        resp = await self.media_stub.GetURL(request)

        return resp