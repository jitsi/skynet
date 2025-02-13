import os

from skynet.env import vector_store_type
from skynet.logs import get_logger
from skynet.modules.ttt.persistence import db
from skynet.modules.ttt.rag.constants import STORED_RAG_KEY
from skynet.modules.ttt.s3 import S3

log = get_logger(__name__)

filenames = dict(
    faiss=['index.faiss', 'index.pkl'],
)


async def files_aiter():
    for filename in filenames[vector_store_type]:
        yield filename


class RagS3:
    def __init__(self):
        self.s3 = S3()

    async def replicate(self, prefix_function: callable):
        stored_keys = await db.lrange(STORED_RAG_KEY, 0, -1)

        for key in stored_keys:
            folder = prefix_function(key)
            os.makedirs(folder, exist_ok=True)

            async for filename in files_aiter():
                await self.s3.download_file(f'{folder}/{filename}')

    async def upload(self, folder):
        async for filename in files_aiter():
            await self.s3.upload_file(f'{folder}/{filename}')

    async def delete(self, folder):
        async for filename in files_aiter():
            await self.s3.delete_file(f'{folder}/{filename}')


__all__ = ['RagS3']
