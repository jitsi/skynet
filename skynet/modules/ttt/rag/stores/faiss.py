import shutil
import time

from uuid import uuid4

import faiss

from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document

from skynet.env import use_s3, vector_store_path
from skynet.logs import get_logger
from skynet.modules.ttt.rag.vector_store import SkynetVectorStore

log = get_logger(__name__)


class FAISSVectorStore(SkynetVectorStore):
    s3 = None

    def __init__(self):
        super().__init__()

        if use_s3:
            from skynet.modules.ttt.rag.stores.s3 import RagS3

            log.info('Using S3 for vector store persistence')
            self.s3 = RagS3()

    def get_vector_store_path(self, store_id):
        return f'{vector_store_path}/faiss/{store_id}'

    async def cleanup(self):
        await super().cleanup()

        if self.s3:
            await self.s3.cleanup()

    async def initialize(self):
        await super().initialize()

        if self.s3:
            await self.s3.replicate(self.get_vector_store_path)
            await self.s3.listen()

    async def get(self, store_id):
        try:
            return FAISS.load_local(
                self.get_vector_store_path(store_id), self.embedding, allow_dangerous_deserialization=True
            )
        except RuntimeError:
            log.info(f'Vector store with id {store_id} not found')
            return None

    async def create(self, store_id, documents: list[Document]):
        if not documents:
            log.info('No documents to create vector store')
            return None

        start = time.perf_counter_ns()
        index = faiss.IndexFlatL2(len(await self.embedding.aembed_query(store_id)))
        vector_store = FAISS(
            embedding_function=self.embedding,
            distance_strategy=DistanceStrategy.COSINE,  # better for full-text search
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
            normalize_L2=True,
        )

        uuids = [str(uuid4()) for _ in range(len(documents))]

        batch_size = 100  # this is purely for logging the progress
        for i in range(0, len(documents), batch_size):
            await vector_store.aadd_documents(documents=documents[i : i + batch_size], ids=uuids[i : i + batch_size])
            log.info(f'Embeddings for {store_id} progress: {i + batch_size} / {len(documents)} documents')

        vector_store.save_local(self.get_vector_store_path(store_id))
        end = time.perf_counter_ns()
        duration = round((end - start) / 1e9)

        if self.s3:
            await self.s3.upload(self.get_vector_store_path(store_id))

        log.info(f'Saving vector store took {duration} seconds')

        return vector_store

    async def delete(self, store_id):
        await super().delete(store_id)

        path = self.get_vector_store_path(store_id)
        shutil.rmtree(path, ignore_errors=True)

        if self.s3:
            await self.s3.delete(path)


__all__ = ['FAISSVectorStore']
