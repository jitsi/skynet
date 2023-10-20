import asyncio

from concurrent.futures import ThreadPoolExecutor

from langchain.chains.summarize import load_summarize_chain
from langchain.llms import LlamaCpp

from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

from skynet.env import llama_path, llama_n_gpu_layers, llama_n_batch

from .v1.models import Job, JobType
from .prompts.action_items import action_items_template
from .prompts.summary import summary_template

executor = None
llm = None


def initialize():
    global executor, llm
    executor = ThreadPoolExecutor(max_workers=1)

    llm = LlamaCpp(
        model_path=llama_path,
        temperature=0.01,
        max_tokens=4096,
        n_ctx=4096,
        n_gpu_layers=llama_n_gpu_layers,
        n_batch=llama_n_batch,
    )


async def process(job: Job) -> str:
    text = job.payload.text

    if not text:
        return ""

    loop = asyncio.get_running_loop()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=100)
    docs = text_splitter.create_documents([text])
    template = summary_template if job.type is JobType.SUMMARY else action_items_template

    prompt = PromptTemplate(template=template, input_variables=["text"])

    chain = load_summarize_chain(llm, chain_type="map_reduce", combine_prompt=prompt)

    return await loop.run_in_executor(executor, chain.run, docs)
