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


class RagS3:
    def __init__(self):
        self.s3 = S3()

    async def replicate(self, prefix_function: callable):
        stored_keys = await db.lrange(STORED_RAG_KEY, 0, -1)

        for key in stored_keys:
            folder = prefix_function(key)
            os.makedirs(folder, exist_ok=True)

            for filename in filenames[vector_store_type]:
                self.s3.download_file(f'{folder}/{filename}')

    def upload(self, folder):
        for filename in filenames[vector_store_type]:
            self.s3.upload_file(f'{folder}/{filename}')

    def delete(self, folder):
        for filename in filenames[vector_store_type]:
            self.s3.delete_file(f'{folder}/{filename}')


__all__ = ['RagS3']
