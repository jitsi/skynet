import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_core.documents import Document

from skynet.env import llama_n_batch, llama_n_gpu_layers, llama_path

from .prompts.action_items import action_items_template
from .prompts.summary import summary_template
from .v1.models import Job, JobType

executor = None
llm = None


def initialize():
    global executor, llm
    executor = ThreadPoolExecutor(max_workers=1)

    llm = LlamaCpp(
        model_path=llama_path,
        temperature=0,
        max_tokens=4096,
        n_ctx=4096,
        n_gpu_layers=llama_n_gpu_layers,
        n_batch=llama_n_batch,
    )


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


async def process(job: Job) -> str:
    text = job.payload.text

    if not text:
        return ""

    loop = asyncio.get_running_loop()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=100)
    docs = [Document(page_content=text)] if len(text) < 12000 else text_splitter.create_documents([text])
    template = summary_template if job.type is JobType.SUMMARY else action_items_template

    prompt = PromptTemplate(template=template, input_variables=["text"])

    # once langchain adds support for LCEL map reduce, update this by splitting the use cases for large and small docs
    chain = {"text": format_docs} | prompt | llm

    return await loop.run_in_executor(executor, chain.invoke, docs)
