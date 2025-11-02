
import asyncio

import jwt
import time

from collections import defaultdict
from dataclasses import dataclass, field

from typing import Optional, Any, get_type_hints

import grpc

from anniegodfather.exceptions import AuthManagerError, AuthLoginUserNotFoundError, AuthRefreshAccessTokenError, AuthBotLoginError
from anniegodfather.proto import auth_pb2_grpc, auth_pb2
from grpc import aio
from anniegodfather.logger import logger


@dataclass
class TokenData:
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    _access_expires_at: Optional[float] = field(default=None, init=False)  # Unix timestamp
    _refresh_expires_at: Optional[float] = field(default=None, init=False)

    @property
    def access_expires_at(self) -> Optional[float]:
        """Только для чтения"""
        return self._access_expires_at

    @property
    def refresh_expires_at(self) -> Optional[float]:
        """Только для чтения"""
        return self._refresh_expires_at

    @staticmethod
    def decode_jwt_exp(token: str) -> float:
        try:
            # Декодируем без проверки подписи, только для получения exp
            payload = jwt.JWT().decode(message=token, do_verify=False)
            exp = payload.get('exp')
            return float(exp)
        except Exception as err:
            raise AuthManagerError(err)

    def safe_update(self, **kwargs):
        """Безопасное обновление с проверкой типов и None"""
        type_hints = get_type_hints(self.__class__)

        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                # update expires fields
                match key:
                    case "access_token":
                        self._access_expires_at = self.decode_jwt_exp(value) - 10
                    case "refresh_token":
                        self._refresh_expires_at = self.decode_jwt_exp(value) - 300
                # Проверка типа
                expected_type = type_hints.get(key)
                if expected_type and not isinstance(value, expected_type):
                    # Для Optional типов проверяем внутренний тип
                    if hasattr(expected_type, '__args__'):
                        inner_type = expected_type.__args__[0]
                        if not isinstance(value, inner_type):
                            continue
                setattr(self, key, value)
        return self

class TokenInMemoryStorage:
    def __init__(self):
        self.token_storage = defaultdict(TokenData)
        self.lock = asyncio.Lock()

    async def upsert_tokens(self, user_id: int, access: str = None, refresh: str = None):
        async with self.lock:

            data = self.token_storage[user_id]
            data.safe_update(access_token=access, refresh_token=refresh)
            return data

    async def clear(self, key: Any) -> TokenData | None:
        async with self.lock:
            return self.token_storage.pop(key)

    async def get_tokens(self, key: Any) -> tuple[str | None, str | None]:
        async with self.lock:
            data = self.token_storage.get(key)
            if not data:
                return None, None

            # Check for expiration
            if data.access_token and time.time() > data.access_expires_at:
                data.access_token = None
            if data.refresh_token and time.time() > data.refresh_expires_at:
                data.refresh_token = None

            return data.access_token, data.refresh_token

class AuthInterceptor(aio.UnaryUnaryClientInterceptor):
    def __init__(self, server: str, api_key: str):
        # создаём отдельный канал и stub для AuthService
        self.token_storage = TokenInMemoryStorage()
        self._auth_channel = grpc.aio.insecure_channel(server)
        self._auth_stub = auth_pb2_grpc.AuthServiceStub(self._auth_channel)
        self._current_user: int = None
        self._api_key_metadata = ('x-api-key', api_key)
        self.whitelistmethods = ["/main.AuthService/RegisterTelegram"]

    async def save_tokens(self, user_id: int, access: str, refresh: str):
        await self.token_storage.upsert_tokens(user_id, access, refresh)

    async def set_current_user(self, user_id: int) -> None:
        self._current_user = user_id

    async def _refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        req = auth_pb2.RefreshRequest(refresh_token=refresh_token)
        try:
            resp = await self._auth_stub.RefreshToken(req, metadata=[self._api_key_metadata])
            await self.token_storage.upsert_tokens(user_id=self._current_user, access=resp.access_token, refresh=resp.refresh_token)
            return resp.access_token, resp.refresh_token
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                return await self._login_user()
        except Exception as err:
            raise AuthRefreshAccessTokenError(err)

    async def _login_user(self) -> tuple[str, str]:
        req = auth_pb2.TelegramLoginRequest(telegram_id=self._current_user)
        try:
            resp = await self._auth_stub.LoginTelegram(req, metadata=[self._api_key_metadata])
            await self.token_storage.upsert_tokens(user_id=self._current_user, access=resp.access_token, refresh=resp.refresh_token)
            return resp.access_token, resp.refresh_token
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise AuthLoginUserNotFoundError()
            raise AuthBotLoginError(e)
        except Exception as err:
            raise AuthBotLoginError(err)


    # === перехват gRPC вызовов ===
    async def intercept_unary_unary(self, continuation, client_call_details, request):
        logger.debug(f"AUTH INTERCEPTOR: serve method {client_call_details.method}")
        if client_call_details.method.decode("utf-8") in self.whitelistmethods:
            return await continuation(client_call_details, request)

        access_token, refresh_token = await self.token_storage.get_tokens(self._current_user)
        match access_token, refresh_token:
            case None, None:
                access_token, refresh_token = await self._login_user()
            case None, str():
                access_token, refresh_token = await self._refresh_access_token(refresh_token=refresh_token)
            case str(), str():
                pass

        # метаданные
        metadata = list(client_call_details.metadata or [])
        if access_token:
            metadata.append(('authorization', f'{access_token}'))

        new_details = grpc.aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=tuple(metadata),
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )

        return await continuation(new_details, request)

class AddApiKeyInterceptor(aio.UnaryUnaryClientInterceptor):
    def __init__(self, api_key):
        self.api_key = ('x-api-key', api_key)

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        metadata = list(client_call_details.metadata or [])
        metadata.append(self.api_key)

        new_details = grpc.aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=tuple(metadata),
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )

        return await continuation(new_details, request)