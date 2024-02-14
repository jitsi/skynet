from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from skynet.env import openai_api_base_url, openai_api_key
from skynet.logs import get_logger

from .prompts.action_items import action_items_system_message
from .prompts.summary import summary_system_message
from .v1.models import Job, JobType

llm = None
map_reduce_threshold = 12000
log = get_logger(__name__)


def initialize():
    global llm

    llm = ChatOpenAI(
        api_key=openai_api_key
        or 'placeholder',  # if no key is set, use a placeholder value to bypass validation, and allow the custom base url to be used
        base_url=None if openai_api_key else openai_api_base_url,
        temperature=0,
    )


async def process(job: Job) -> str:
    text = job.payload.text
    chain = None

    if not text:
        return ""

    system_message = summary_system_message if job.type is JobType.SUMMARY else action_items_system_message
    prompt = ChatPromptTemplate.from_messages([("system", system_message), ("user", "{text}")])

    if len(text) < map_reduce_threshold:
        chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt)
        docs = [Document(page_content=text)]
    else:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=map_reduce_threshold, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(llm, chain_type="map_reduce", combine_prompt=prompt, map_prompt=prompt)

    result = await chain.ainvoke(input={"input_documents": docs})

    return result['output_text'].strip()
