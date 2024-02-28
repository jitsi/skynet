from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from skynet.env import app_uuid, openai_api_base_url
from skynet.logs import get_logger

from .prompts.action_items import action_items_conversation_prompt, action_items_text_prompt
from .prompts.summary import summary_conversation_prompt, summary_text_prompt
from .v1.models import DocumentPayload, HintType, JobType

llm = None
map_reduce_threshold = 12000
log = get_logger(__name__)


hint_type_to_prompt = {
    JobType.SUMMARY: {
        HintType.CONVERSATION: summary_conversation_prompt,
        HintType.TEXT: summary_text_prompt,
    },
    JobType.ACTION_ITEMS: {
        HintType.CONVERSATION: action_items_conversation_prompt,
        HintType.TEXT: action_items_text_prompt,
    },
}


def initialize():
    global llm

    llm = ChatOpenAI(
        api_key='placeholder',  # use a placeholder value to bypass validation, and allow the custom base url to be used
        base_url=openai_api_base_url,
        default_headers={"X-Skynet-UUID": app_uuid},
        temperature=0,
    )


async def process(payload: DocumentPayload, job_type: JobType, model: ChatOpenAI = None) -> str:
    current_model = model or llm
    chain = None
    text = payload.text

    if not text:
        return ""

    system_message = hint_type_to_prompt[job_type][payload.hint]
    prompt = ChatPromptTemplate.from_messages([("system", system_message), ("user", "{text}")])

    if len(text) < map_reduce_threshold:
        chain = load_summarize_chain(current_model, chain_type="stuff", prompt=prompt)
        docs = [Document(page_content=text)]
    else:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=map_reduce_threshold, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(current_model, chain_type="map_reduce", combine_prompt=prompt, map_prompt=prompt)

    result = await chain.ainvoke(input={"input_documents": docs})

    return result['output_text'].strip()


async def process_open_ai(payload: DocumentPayload, job_type: JobType, api_key: str) -> str:
    llm = ChatOpenAI(
        api_key=api_key,
        temperature=0,
    )

    return await process(payload, job_type, llm)
