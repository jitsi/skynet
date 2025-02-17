import asyncio
import json
import os

from skynet.env import app_uuid, vector_store_type
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
        self.listen_task = None

    def __del__(self):
        if self.listen_task:
            self.listen_task.cancel()

    async def listen(self):
        pubsub = db.db.pubsub()
        await pubsub.subscribe(**{'s3-upload': self.handleS3Upload})
        self.listen_task = asyncio.create_task(pubsub.run())

    async def replicate(self, prefix_function: callable):
        stored_keys = await db.lrange(STORED_RAG_KEY, 0, -1)

        for key in stored_keys:
            folder = prefix_function(key)
            os.makedirs(folder, exist_ok=True)

            async for filename in files_aiter():
                await self.s3.download_file(f'{folder}/{filename}')

    async def upload(self, folder):
        async for name in files_aiter():
            filename = f'{folder}/{name}'
            await self.s3.upload_file(filename)
            await db.db.publish('s3-upload', json.dumps({'filename': filename, 'app_uuid': app_uuid}))

    async def delete(self, folder):
        async for filename in files_aiter():
            await self.s3.delete_file(f'{folder}/{filename}')

    async def handleS3Upload(self, message):
        message = json.loads(message['data'])
        filename = message.get('filename')
        uuid = message.get('app_uuid')

        if uuid != app_uuid:
            await self.s3.download_file(filename)


__all__ = ['RagS3']
