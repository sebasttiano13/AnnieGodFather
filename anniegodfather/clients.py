# -*- coding: utf-8 -*-

import grpc
from anniegodfather.proto import anniegodfather_pb2_grpc as godfather_grpc, anniegodfather_pb2 as godfather_pb

class DadClient:

    def __init__(self, server: str):
        self._stub = godfather_grpc.MediaStub(grpc.aio.insecure_channel(server))


    async def fetch_post_url(self) -> str:
        """Gets presighned S3 post url from anniedad backend"""
        request = godfather_pb.PostMediaRequest()
        presigned_url =  await self._stub.PostURL(request)
        return presigned_url

    async def fetch_get_url(self, filename: str) -> str:
        """Gets presighned S3 get url from anniedad backend"""
        request = godfather_pb.GetMediaRequest(filename=filename)
        get_url = await self._stub.GetURL(request)
        return get_url