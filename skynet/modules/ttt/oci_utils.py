import asyncio

from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional

from langchain_community.chat_models import ChatOCIGenAI

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

executor = None
executor_max_workers = 10  # Matches the connection pool size used by Requests


class AsyncChatOCIGenAI(ChatOCIGenAI):
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        global executor

        if executor is None:
            executor = ThreadPoolExecutor(max_workers=executor_max_workers)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, self._generate, messages, stop, run_manager, **kwargs)
        return result


__all__ = ['AsyncChatOCIGenAI']
