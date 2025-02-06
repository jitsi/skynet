import re
import time
from typing import List

from bs4 import BeautifulSoup as bs4
from fake_useragent import UserAgent

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from skynet.logs import get_logger
from skynet.modules.ttt.assistant.v1.models import RagPayload
from skynet.modules.ttt.rag.web_crawler.recursive_url_loader import SkynetRecursiveUrlLoader

ua = UserAgent()
log = get_logger(__name__)


def extractor(raw_html: str) -> str:
    soup = bs4(raw_html, 'html.parser')
    output = soup.text
    output = re.sub(r'[\n]+', '\n', output)
    output = re.sub(r'[\s]+', ' ', output)

    return output


async def crawl_url(url: str, max_depth) -> List[Document]:
    """
    Crawl the given URL and return the list of documents.
    """

    start = time.perf_counter_ns()
    log.info(f"Starting to crawl {url}")

    loader = SkynetRecursiveUrlLoader(
        url=url, extractor=extractor, headers={'User-Agent': ua.random}, max_depth=max_depth, use_async=True, timeout=30
    )

    documents = []

    async for doc in loader.alazy_load():
        documents.append(doc)
        log.info(f"Loaded document: {doc.metadata['source']}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=100)

    splits = splitter.split_documents(documents)
    end = time.perf_counter_ns()
    duration = round((end - start) / 1e9)

    log.info(f'Initial document count for {url}: {len(documents)}')
    log.info(f'Split document count for {url}: {len(splits)}')
    log.info(f'Crawling took {duration} seconds')

    return splits


async def crawl(payload: RagPayload) -> List[Document]:
    """
    Crawl the given URLs and return the concatanated list of documents.
    """

    documents = []
    for url in payload.urls:
        docs = await crawl_url(url, payload.max_depth)
        documents.extend(docs)

    return documents


__all__ = ['crawl']
