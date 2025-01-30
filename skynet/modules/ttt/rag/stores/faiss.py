import shutil
import time

from uuid import uuid4

import faiss

from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy

from skynet.env import vector_store_path
from skynet.logs import get_logger
from skynet.modules.ttt.rag.vector_store import SkynetVectorStore

log = get_logger(__name__)


class FAISSVectorStore(SkynetVectorStore):
    def get_vector_store_path(self, store_id):
        return f'{vector_store_path}/faiss/{store_id}'

    async def get(self, store_id):
        try:
            return FAISS.load_local(
                self.get_vector_store_path(store_id), self.embedding, allow_dangerous_deserialization=True
            )
        except RuntimeError:
            log.info(f'Vector store with id {store_id} not found')
            return None

    async def create(self, store_id, documents):
        start = time.perf_counter_ns()
        index = faiss.IndexFlatL2(len(self.embedding.embed_query(store_id)))
        vector_store = FAISS(
            embedding_function=self.embedding,
            distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )

        uuids = [str(uuid4()) for _ in range(len(documents))]
        await vector_store.aadd_documents(documents=documents, ids=uuids)
        vector_store.save_local(self.get_vector_store_path(store_id))
        end = time.perf_counter_ns()
        duration = round((end - start) / 1e9)

        log.info(f'Saving vector store took {duration} seconds')

        return vector_store

    async def delete(self, store_id):
        await super().delete(store_id)

        shutil.rmtree(self.get_vector_store_path(store_id), ignore_errors=True)


__all__ = ['FAISSVectorStore']
