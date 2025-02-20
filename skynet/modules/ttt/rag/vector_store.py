import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from skynet.env import embeddings_model_path
from skynet.logs import get_logger
from skynet.modules.ttt.assistant.v1.models import RagConfig, RagPayload, RagStatus
from skynet.modules.ttt.rag.constants import ERROR_RAG_KEY, RUNNING_RAG_KEY, STORED_RAG_KEY
from skynet.modules.ttt.rag.web_crawler.main import crawl

from ..persistence import db

log = get_logger(__name__)


def bypass_ingestion(existing_payload: RagPayload, new_payload: RagPayload):
    existing_urls = existing_payload.urls
    new_urls = new_payload.urls

    existing_urls.sort()
    new_urls.sort()

    return (
        list(dict.fromkeys(existing_urls)) == list(dict.fromkeys(new_urls))
        and existing_payload.max_depth == new_payload.max_depth
    )


class SkynetVectorStore(ABC):
    embedding = HuggingFaceEmbeddings(
        model_name=embeddings_model_path, model_kwargs={'device': 'cpu', 'trust_remote_code': True}
    )
    tasks = set()

    @abstractmethod
    async def initialize(self):
        """
        Initialize the vector store.
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """
        Clean up the vector store.
        """
        pass

    @abstractmethod
    def get_vector_store_path(self, store_id: str):
        """
        Get the path where the vector store with the given id is saved.
        """
        pass

    @abstractmethod
    async def get(self, store_id: str) -> VectorStore:
        """
        Get a vector store with the given id.
        """
        pass

    @abstractmethod
    async def create(self, store_id: str, documents: List[Document]):
        """
        Create a vector store with the given id.
        """
        pass

    @abstractmethod
    async def delete(self, store_id: str):
        """
        Delete a vector store with the given id.
        """

        await db.delete(store_id)
        await db.lrem(STORED_RAG_KEY, 0, store_id)
        await db.lrem(ERROR_RAG_KEY, 0, store_id)
        await db.lrem(RUNNING_RAG_KEY, 0, store_id)

    async def update_config(self, store_id: str, **kwargs) -> RagConfig:
        """Update a config in the db."""
        config_json = await db.get(store_id)

        # deserialize and merge
        config = RagConfig(**(RagConfig.model_validate_json(config_json).model_dump() | kwargs))

        # serialize changes and save to db
        await db.set(store_id, RagConfig.model_dump_json(config))

        return config

    async def get_config(self, store_id: str) -> Optional[RagConfig]:
        """
        Get the configuration of the vector store with the given id.
        """
        store_config = await db.get(store_id)

        if store_config:
            return RagConfig.model_validate_json(store_config)

        return None

    async def workflow(self, payload: RagPayload, store_id: str):
        """
        Crawl the given URL and create a vector store with the generated embeddings.
        """

        try:
            documents = await crawl(payload)

            await self.create(store_id, documents)
            await db.lrem(STORED_RAG_KEY, 0, store_id)  # ensure no duplicates
            await db.rpush(STORED_RAG_KEY, store_id)
            await self.update_config(store_id, status=RagStatus.SUCCESS)
        except Exception as e:
            await db.rpush(ERROR_RAG_KEY, store_id)
            await self.update_config(store_id, status=RagStatus.ERROR, error=str(e))
            log.error(e)

        await db.lrem(RUNNING_RAG_KEY, 0, store_id)

    async def update_from_urls(self, payload: RagPayload, store_id: str) -> Optional[RagConfig]:
        """
        Create a vector store with the given id, using the documents crawled from the given URL.
        """

        config = await self.get_config(store_id)

        if store_id in await db.lrange(RUNNING_RAG_KEY, 0, -1):
            return config

        if config and config.status == RagStatus.SUCCESS and bypass_ingestion(config, payload):
            return await self.update_config(store_id, system_message=payload.system_message)

        await db.rpush(RUNNING_RAG_KEY, store_id)
        config = RagConfig(urls=payload.urls, max_depth=payload.max_depth)
        await db.set(store_id, RagConfig.model_dump_json(config))

        task = asyncio.create_task(self.workflow(payload, store_id))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)

        return config
