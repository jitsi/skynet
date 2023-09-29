import timeit
import asyncio

from concurrent.futures import ThreadPoolExecutor

from langchain.chains.summarize import load_summarize_chain
from langchain.llms import LlamaCpp

from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

from skynet.models.v1.job import JobId, JobStatus, JobType
from skynet.models.v1.document import DocumentPayload
from skynet.env import llama_path, llama_n_gpu_layers, llama_n_batch
from skynet.modules.ttt.jobs import create_job, update_job
from skynet.prompts.action_items import action_items_template
from skynet.prompts.summary import summary_template

class SummariesChain:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)

        self.llm = LlamaCpp(
            model_path=llama_path,
            temperature=0.01,
            max_tokens=4096,
            n_ctx=4096,
            n_gpu_layers=llama_n_gpu_layers,
            n_batch=llama_n_batch,
        )

    async def process(self, text: str, template: str, job_id: str) -> str:
        if not text:
            return ""

        loop = asyncio.get_running_loop()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=100)
        docs = text_splitter.create_documents([text])

        prompt = PromptTemplate(template=template, input_variables=["text"])

        chain = load_summarize_chain(
            self.llm,
            chain_type="map_reduce",
            combine_prompt=prompt)

        has_failed = False
        result = None

        try:
            result = await loop.run_in_executor(self.executor, chain.run, docs)
        except Exception as e:
            has_failed = True
            result = str(e)

        await update_job(
            job_id,
            status=JobStatus.ERROR if has_failed else JobStatus.SUCCESS,
            result=result
        )

    async def start_summary_job(self, payload: DocumentPayload) -> JobId:
        job_id = await create_job(job_type=JobType.SUMMARY)

        task = self.process(payload.text, template=summary_template, job_id=job_id)
        asyncio.create_task(task)

        return JobId(id=job_id)

    async def start_action_items_job(self, payload: DocumentPayload) -> JobId:
        job_id = await create_job(job_type=JobType.ACTION_ITEMS)

        task = self.process(payload.text, template=action_items_template, job_id=job_id)
        asyncio.create_task(task)

        return JobId(id=job_id)
