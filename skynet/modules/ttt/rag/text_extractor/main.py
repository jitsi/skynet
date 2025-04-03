import asyncio

from multiprocessing import cpu_count
from pathlib import Path

from kreuzberg import batch_extract_file
from langchain_core.documents import Document

from skynet.logs import get_logger
from skynet.modules.ttt.rag.utils import split_documents

log = get_logger(__name__)

MAX_CONCURRENT_PROCESSES = max(1, cpu_count() - 1)  # Leave one core free for other tasks
cpu_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PROCESSES)


async def extract(files: list[str]) -> list[Document]:
    """
    Extract text from files.
    """

    documents = []

    # Process files in smaller chunks to prevent long blocking operations
    chunk_size = 10  # Adjust based on performance testing
    for i in range(0, len(files), chunk_size):
        files_chunk = files[i : i + chunk_size]

        async with cpu_semaphore:
            chunk_results = await batch_extract_file(files_chunk)

        for file, result in zip(files_chunk, chunk_results):
            documents.append(Document(result.content, metadata={'source': Path(file).name}))

        # Yield control back to the event loop to allow healthchecks to run
        await asyncio.sleep(0.01)

    splits = split_documents(documents)

    log.info(f'Extracted text from {len(documents)} files.')
    log.info(f'Split count: {len(splits)}')

    return splits


__all__ = ['extract']
