import asyncio
import io
from typing import List, Optional, Set

import aiohttp
import requests
from fake_useragent import UserAgent

from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain_core.documents import Document
from langchain_core.utils.html import extract_sub_links
from pypdf import PdfReader

from skynet.logs import get_logger

ua = UserAgent()
log = get_logger(__name__)


class SkynetRecursiveUrlLoader(RecursiveUrlLoader):
    async def _async_get_child_links_recursive(
        self,
        url: str,
        visited: Set[str],
        *,
        session: Optional[aiohttp.ClientSession] = None,
        depth: int = 0,
    ) -> List[Document]:
        if depth >= self.max_depth:
            return []

        # Disable SSL verification because websites may have invalid SSL certificates,
        # but won't cause any security issues for us.
        close_session = session is None
        session = (
            session
            if session is not None
            else aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self.headers,
            )
        )

        visited.add(url)

        text = ''
        metadata = {}
        results = []

        try:
            async with session.get(url, timeout=120) as response:
                metadata = self.metadata_extractor('', url, response)
                text = await response.text()
        except (aiohttp.client_exceptions.InvalidURL, Exception) as e:
            try:
                if close_session:
                    await session.close()

                content_type = metadata.get('content_type')
                if content_type and 'application/pdf' in content_type:
                    res = requests.get(url=url, timeout=120)
                    on_fly_mem_obj = io.BytesIO(res.content)
                    reader = PdfReader(on_fly_mem_obj)

                    for page in reader.pages:
                        text += page.extract_text() + '\n'
                else:
                    log.warning(f'Unable to load {url}. Received error {e} of type {e.__class__.__name__}')
                    return []

            except Exception as e:
                log.warning(f'Failed to use pdf extractor for {url}. Received error {e} of type {e.__class__.__name__}')

                return []

        content = self.extractor(text)

        if content:
            results.append(
                Document(
                    page_content=content,
                    metadata=self.metadata_extractor(text, url, response),
                )
            )
        if depth < self.max_depth - 1:
            sub_links = extract_sub_links(
                text,
                url,
                base_url=self.base_url,
                pattern=self.link_regex,
                prevent_outside=self.prevent_outside,
                exclude_prefixes=self.exclude_dirs,
                continue_on_failure=self.continue_on_failure,
            )

            # Recursively call the function to get the children of the children
            sub_tasks = []
            to_visit = set(sub_links).difference(visited)
            for link in to_visit:
                sub_tasks.append(self._async_get_child_links_recursive(link, visited, session=session, depth=depth + 1))
            next_results = await asyncio.gather(*sub_tasks)
            for sub_result in next_results:
                if isinstance(sub_result, Exception) or sub_result is None:
                    # We don't want to stop the whole process, so just ignore it
                    # Not standard html format or invalid url or 404 may cause this.
                    continue
                # locking not fully working, temporary hack to ensure deduplication
                results += [r for r in sub_result if r not in results]
        if close_session:
            await session.close()
        return results
