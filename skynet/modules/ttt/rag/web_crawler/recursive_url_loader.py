import asyncio
import io
from typing import List, Optional, Set
from urllib.parse import urljoin

import aiohttp
import requests
from fake_useragent import UserAgent

from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain_core.documents import Document
from langchain_core.utils.html import extract_sub_links
from pypdf import PdfReader

from skynet.logs import get_logger
from skynet.modules.ttt.rag.web_crawler.url_validator import URLValidationError, validate_url

ua = UserAgent()
log = get_logger(__name__)


MAX_REDIRECTS = 5


def is_safe_url(url: str) -> bool:
    """Check if a URL passes validation."""
    try:
        validate_url(url)
        return True
    except URLValidationError as e:
        log.warning(f"Blocked URL: {url} - {e}")
        return False


async def fetch_with_validated_redirects(
    session: aiohttp.ClientSession, url: str, timeout: int
) -> tuple[aiohttp.ClientResponse, str]:
    """Fetch a URL, validating each redirect target before following."""
    current_url = url
    for _ in range(MAX_REDIRECTS):
        response = await session.get(current_url, timeout=timeout, allow_redirects=False)
        if response.status not in (301, 302, 303, 307, 308):
            return response, current_url
        location = response.headers.get('Location')
        if not location:
            return response, current_url
        redirect_url = urljoin(current_url, location)
        if not is_safe_url(redirect_url):
            raise URLValidationError(f"Redirect to blocked URL: {redirect_url}")
        current_url = redirect_url
        await response.release()
    raise URLValidationError(f"Too many redirects for URL: {url}")


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

        close_session = session is None
        session = (
            session
            if session is not None
            else aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self.headers,
            )
        )

        visited.add(url)

        text = ''
        metadata = {}
        results = []
        final_url = url

        try:
            response, final_url = await fetch_with_validated_redirects(session, url, timeout=120)
            visited.add(final_url)
            async with response:
                metadata = self.metadata_extractor('', final_url, response)
                text = await response.text()
        except (aiohttp.client_exceptions.InvalidURL, URLValidationError, Exception) as e:
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
                    metadata=self.metadata_extractor(text, final_url, response),
                )
            )
        if depth < self.max_depth - 1:
            sub_links = extract_sub_links(
                text,
                final_url,
                base_url=self.base_url,
                pattern=self.link_regex,
                prevent_outside=self.prevent_outside,
                exclude_prefixes=self.exclude_dirs,
                continue_on_failure=self.continue_on_failure,
            )

            # Recursively call the function to get the children of the children
            sub_tasks = []
            to_visit = set(sub_links).difference(visited)
            to_visit = {link for link in to_visit if is_safe_url(link)}
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
