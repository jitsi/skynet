import timeit
import asyncio

from concurrent.futures import ThreadPoolExecutor

from langchain.chains.summarize import load_summarize_chain
from langchain.llms import LlamaCpp

from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

from skynet.models.v1.action_items import ActionItemsPayload, ActionItemsResult
from skynet.models.v1.summary import SummaryPayload, SummaryResult
from skynet.env import llama_path
from skynet.prompts.action_items import action_items_template
from skynet.prompts.summary import summary_template

class SummariesChain:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.chains = {}

        self.llm = LlamaCpp(
            model_path=llama_path,
            temperature=0.01,
            max_tokens=1000,
            n_ctx=2048
        )

    async def process(self, text: str, template: str) -> str:
        if not text:
            return ""

        start = timeit.default_timer()

        loop = asyncio.get_running_loop()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=100)
        docs = text_splitter.create_documents([text])

        prompt = PromptTemplate(template=template, input_variables=["text"])

        chain = load_summarize_chain(
            self.llm,
            chain_type="map_reduce",
            combine_prompt=prompt)

        result = await loop.run_in_executor(self.executor, chain.run, docs)

        end = timeit.default_timer()

        print(f"Time to retrieve response: {end - start}")

        return result

    async def get_action_items_from_text(self, payload: ActionItemsPayload) -> ActionItemsResult:
        result = await self.process(payload.text, template=action_items_template)
        return ActionItemsResult(action_items=result)

    async def get_action_items_from_id(self, id: str) -> ActionItemsResult:
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        history = memory.load_memory_variables({}).get("history")

        return await self.get_action_items_from_text(ActionItemsPayload(text=history))

    async def get_summary_from_text(self, payload: SummaryPayload) -> SummaryResult:
        result = await self.process(payload.text, template=summary_template)
        return SummaryResult(summary=result)

    async def get_summary_from_id(self, id: str):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        history = memory.load_memory_variables({}).get("history")

        return await self.get_summary_from_text(SummaryPayload(text=history))

    def update_summary_context(self, id: str, payload: SummaryPayload):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        memory.save_context({"input": payload.text }, {"output": ""})

        return memory.load_memory_variables({}).get("history")

    def delete_summary_context(self, id: str):
        if id in self.chains:
            del self.chains[id]
            return True

        return False
