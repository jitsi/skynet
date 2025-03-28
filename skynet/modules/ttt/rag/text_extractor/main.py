from pathlib import Path

from kreuzberg import batch_extract_file
from langchain_core.documents import Document

from skynet.logs import get_logger
from skynet.modules.ttt.rag.utils import split_documents

log = get_logger(__name__)


async def extract(files: list[str]) -> list[Document]:
    """
    Extract text from files.
    """

    documents = []

    results = await batch_extract_file(files)

    for file, result in zip(files, results):
        documents.append(Document(result.content, metadata={'source': Path(file).name}))

    splits = split_documents(documents)

    log.info(f'Extracted text from {len(documents)} files.')
    log.info(f'Split count: {len(splits)}')

    return splits


__all__ = ['extract']
