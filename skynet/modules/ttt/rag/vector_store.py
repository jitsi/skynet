import asyncio
import shutil
from abc import ABC, abstractmethod
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from skynet.env import embeddings_model_path
from skynet.logs import get_logger
from skynet.modules.ttt.assistant.v1.models import RagConfig, RagPayload, RagStatus
from skynet.modules.ttt.rag.constants import ERROR_RAG_KEY, RUNNING_RAG_KEY, STORED_RAG_KEY, supported_files

from skynet.modules.ttt.rag.text_extractor.main import extract as extract_text
from skynet.modules.ttt.rag.utils import save_files
from skynet.modules.ttt.rag.web_crawler.main import crawl
from skynet.modules.ttt.rag.zip_extractor.main import extract_files

from ..persistence import db

log = get_logger(__name__)


def bypass_files_ingestion(config: RagConfig, new_config: RagConfig):
    return set(config.files) == set(new_config.files)


def bypass_urls_ingestion(config: RagConfig, new_config: RagConfig):
    return set(config.urls) == set(new_config.urls) and config.max_depth == new_config.max_depth


def bypass_ingestion(config: RagConfig, new_config: RagConfig):
    return (
        config
        and config.status == RagStatus.SUCCESS
        and bypass_files_ingestion(config, new_config)
        and bypass_urls_ingestion(config, new_config)
    )


class SkynetVectorStore(ABC):
    embedding = HuggingFaceEmbeddings(model_name=embeddings_model_path, model_kwargs={'device': 'cpu'})
    tasks = set()

    @abstractmethod
    async def initialize(self):
        """
        Initialize the vector store.
        """

    @abstractmethod
    async def cleanup(self):
        """
        Clean up the vector store.
        """

    @abstractmethod
    def get_vector_store_path(self, store_id: str):
        """
        Get the path where the vector store with the given id is saved.
        """

    @abstractmethod
    async def get(self, store_id: str) -> VectorStore:
        """
        Get a vector store with the given id.
        """

    @abstractmethod
    async def create(self, store_id: str, documents: List[Document]):
        """
        Create a vector store with the given id.
        """

    @abstractmethod
    async def delete(self, store_id: str):
        """
        Delete a vector store with the given id.
        """

        await db.delete(store_id)
        await db.lrem(STORED_RAG_KEY, 0, store_id)
        await db.lrem(ERROR_RAG_KEY, 0, store_id)
        await db.lrem(RUNNING_RAG_KEY, 0, store_id)

    def get_temp_folder(self, store_id: str) -> str:
        """
        Get the path to the temp folder for the vector store with the given id.
        """

        return f'{self.get_vector_store_path(store_id)}/temp'

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

    async def workflow(self, store_id: str, files: list[str], urls: list[str], max_depth: int):
        """
        Extract text from the payload and create a vector store with the generated embeddings.
        """

        documents = []
        error = None

        try:
            zip_files = [f for f in files if f.endswith('.zip')]
            if zip_files:
                files = [f for f in files if f not in zip_files]
                files.extend(await extract_files(zip_files, self.get_temp_folder(store_id), min_size_kb=1))

            files = [f for f in files if any(f.endswith(ext) for ext in supported_files)]

            documents.extend(await extract_text(files))
            documents.extend(await crawl(urls, max_depth))

            await self.create(store_id, documents)
            await db.lrem(STORED_RAG_KEY, 0, store_id)  # ensure no duplicates
            await db.rpush(STORED_RAG_KEY, store_id)
            await self.update_config(store_id, status=RagStatus.SUCCESS)
        except ExceptionGroup as eg:
            error = str([str(e) for e in eg.exceptions])
        except Exception as e:
            error = str(e)

        if error:
            await self.update_config(store_id, status=RagStatus.ERROR, error=error)
            await db.rpush(ERROR_RAG_KEY, store_id)
            log.error(error)

        await db.lrem(RUNNING_RAG_KEY, 0, store_id)
        shutil.rmtree(self.get_temp_folder(store_id), ignore_errors=True)

    async def ingest(self, store_id: str, payload: RagPayload) -> Optional[RagConfig]:
        """
        Create a vector store with the given id, using the documents crawled from the given URL.
        """

        config = await self.get_config(store_id)

        if store_id in await db.lrange(RUNNING_RAG_KEY, 0, -1):
            return config

        updated_config = RagConfig(**payload.model_dump())

        if bypass_ingestion(config, updated_config):
            return await self.update_config(store_id, system_message=payload.system_message)

        await db.rpush(RUNNING_RAG_KEY, store_id)
        await db.set(store_id, RagConfig.model_dump_json(updated_config))

        temp_file_paths = await save_files(self.get_temp_folder(store_id), payload.files)

        task = asyncio.create_task(
            self.workflow(store_id, urls=payload.urls, max_depth=payload.max_depth, files=temp_file_paths)
        )
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)

        return updated_config
