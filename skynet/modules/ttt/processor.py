import json
from datetime import datetime, timedelta, timezone
from operator import itemgetter
from typing import List, Optional

from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_compressors import FlashrankRerank
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from oci.exceptions import TransientServiceError
from openai.types.chat import ChatCompletionMessageParam

from skynet.constants import response_prefix

from skynet.env import llama_n_ctx, modules, oci_blackout_fallback_duration, use_oci
from skynet.logs import get_logger
from skynet.modules.monitoring import MAP_REDUCE_CHUNKING_COUNTER
from skynet.modules.ttt.assistant.constants import assistant_rag_question_extractor
from skynet.modules.ttt.assistant.utils import get_assistant_chat_messages
from skynet.modules.ttt.assistant.v1.models import AssistantDocumentPayload
from skynet.modules.ttt.llm_selector import LLMSelector
from skynet.modules.ttt.summaries.prompts.action_items import (
    action_items_conversation,
    action_items_emails,
    action_items_meeting,
    action_items_text,
)
from skynet.modules.ttt.summaries.prompts.common import set_response_language
from skynet.modules.ttt.summaries.prompts.summary import (
    summary_conversation,
    summary_emails,
    summary_meeting,
    summary_text,
)
from skynet.modules.ttt.summaries.prompts.table_of_contents import (
    table_of_contents_conversation,
    table_of_contents_emails,
    table_of_contents_meeting,
    table_of_contents_text,
)
from skynet.modules.ttt.summaries.v1.models import DocumentPayload, HintType, Job, JobType, Processors

log = get_logger(__name__)

# Global OCI blackout state management
_oci_blackout_until: Optional[datetime] = None


def set_oci_blackout(duration_seconds: int) -> None:
    """Set OCI blackout for the specified duration."""
    global _oci_blackout_until
    _oci_blackout_until = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    log.warning(f"OCI blackout set until {_oci_blackout_until} ({duration_seconds} seconds)")


def is_oci_blackout_active() -> bool:
    """Check if OCI is currently in blackout period."""
    global _oci_blackout_until
    if _oci_blackout_until is None:
        return False

    now = datetime.now(timezone.utc)
    if now >= _oci_blackout_until:
        _oci_blackout_until = None  # Clear expired blackout
        log.info("OCI blackout period expired, resuming normal processing")
        return False

    return True


hint_type_to_prompt = {
    JobType.SUMMARY: {
        HintType.CONVERSATION: summary_conversation,
        HintType.EMAILS: summary_emails,
        HintType.MEETING: summary_meeting,
        HintType.TEXT: summary_text,
    },
    JobType.ACTION_ITEMS: {
        HintType.CONVERSATION: action_items_conversation,
        HintType.EMAILS: action_items_emails,
        HintType.MEETING: action_items_meeting,
        HintType.TEXT: action_items_text,
    },
    JobType.TABLE_OF_CONTENTS: {
        HintType.CONVERSATION: table_of_contents_conversation,
        HintType.EMAILS: table_of_contents_emails,
        HintType.MEETING: table_of_contents_meeting,
        HintType.TEXT: table_of_contents_text,
    },
}


def format_docs(docs: list[Document]) -> str:
    for doc in docs:
        log.debug(doc.metadata.get('source'))

    log.info(f'Using {len(docs)} documents for RAG')

    return '\n\n'.join(
        f"### Document source: {doc.metadata.get('source')}\n{doc.page_content}" for i, doc in enumerate(docs)
    )


compressor = FlashrankRerank() if 'assistant' in modules else None


async def assist(model: BaseChatModel, payload: AssistantDocumentPayload, customer_id: Optional[str] = None) -> str:
    from skynet.modules.ttt.rag.app import get_vector_store

    store = await get_vector_store()
    customer_store = await store.get(customer_id)
    retriever = None
    system_message = None
    question = payload.prompt
    is_generated_question = False

    if customer_store:
        config = await store.get_config(customer_id)
        system_message = config.system_message
        base_retriever = customer_store.as_retriever(search_kwargs={'k': payload.top_k})
        retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=base_retriever)

    if retriever and not question and payload.text:
        question_payload = DocumentPayload(prompt='\n'.join([payload.text, assistant_rag_question_extractor]), text='')
        question = await process_text(model, question_payload)
        question = question.replace(response_prefix, '').strip()
        is_generated_question = True

    log.info(
        f'Using {"generated " if is_generated_question else ""}question: {question}. System message: {system_message or "default"}'
    )

    template = ChatPromptTemplate(
        get_assistant_chat_messages(
            use_rag=bool(retriever),
            use_only_rag_data=payload.use_only_rag_data,
            text=payload.text,
            prompt=payload.prompt,
            system_message=system_message,
        )
    )

    log.debug(f'Using template: {template}')

    rag_chain = (
        {'context': (itemgetter('question') | retriever | format_docs) if retriever else lambda _: ''}
        | template
        | model
        | StrOutputParser()
    )

    return await rag_chain.ainvoke(input={'question': question})


async def summarize(model: BaseChatModel, payload: DocumentPayload, job_type: JobType, customer_id: str) -> str:
    chain = None
    text = payload.text

    # Fallback priority: payload.prompt -> customer's live_summary_prompt (if is_live_summary=True) -> hint_type_to_prompt[job_type][payload.hint]
    system_message = payload.prompt

    if not system_message and payload.is_live_summary:
        from skynet.modules.ttt.customer_configs.utils import get_existing_customer_config

        config = await get_existing_customer_config(customer_id)
        if config:
            system_message = config.get('live_summary_prompt')

    if not system_message:
        system_message = hint_type_to_prompt[job_type][payload.hint]

    prompt = ChatPromptTemplate(
        [
            ('system', set_response_language(payload.preferred_locale)),
            ('system', system_message),
            ('human', '{text}'),
        ]
    )

    # this is a rough estimate of the number of tokens in the input text, since llama models will have a different tokenization scheme
    num_tokens = model.get_num_tokens(text)

    # allow some buffer for the model to generate the output
    # TODO: adjust this to the actual model's context window
    threshold = llama_n_ctx * 3 / 4

    if num_tokens < threshold:
        chain = load_summarize_chain(model, chain_type='stuff', prompt=prompt)
        docs = [Document(page_content=text)]
    else:
        # split the text into roughly equal chunks
        num_chunks = num_tokens // threshold + 1
        chunk_size = num_tokens // num_chunks

        log.info(f'Splitting text into {num_chunks} chunks of {chunk_size} tokens')

        # Record map-reduce chunking metric
        MAP_REDUCE_CHUNKING_COUNTER.labels(job_type=job_type.value).inc()

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=chunk_size, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(model, chain_type='map_reduce', combine_prompt=prompt, map_prompt=prompt)

    result = await chain.ainvoke(input={'input_documents': docs})
    formatted_result = result['output_text'].replace(response_prefix, '').strip()

    log.info(f'input length: {len(system_message) + len(text)}')
    log.info(f'output length: {len(formatted_result)}')

    return formatted_result


async def process_text(model: BaseChatModel, payload: DocumentPayload) -> str:
    prompt = payload.prompt.strip()
    text = payload.text.strip()

    prompt_template = ChatPromptTemplate(
        [
            ('system', prompt),
            ('human', '{text}'),
        ]
    )

    chain = prompt_template | model | StrOutputParser()
    result = await chain.ainvoke(input={'text': text})

    log.info(f'input length: {len(prompt) + len(text)}')
    log.info(f'output length: {len(result)}')

    return result


async def process(job: Job) -> str:
    payload = job.payload
    job_type = job.type
    customer_id = job.metadata.customer_id

    llm = LLMSelector.select(
        customer_id,
        job_id=job.id,
        oci_blackout=is_oci_blackout_active(),
        **{'max_completion_tokens': payload.max_completion_tokens},
    )

    try:
        if job_type == JobType.ASSIST:
            result = await assist(llm, payload, customer_id)
        elif job_type in [JobType.SUMMARY, JobType.ACTION_ITEMS, JobType.TABLE_OF_CONTENTS]:
            result = await summarize(llm, payload, job_type, customer_id)
        elif job_type == JobType.PROCESS_TEXT:
            result = await process_text(llm, payload)
        else:
            raise ValueError(f'Invalid job type {job_type}')
    except TransientServiceError as e:
        log.warning(f"Job {job.id} hit TransientServiceError: {e}")

        # Set blackout using fallback duration
        blackout_duration = oci_blackout_fallback_duration
        log.info(f"TransientServiceError detected, setting {blackout_duration}s blackout")
        set_oci_blackout(blackout_duration)

        # Switch current job to local processing
        LLMSelector.override_job_processor(job.id, Processors.LOCAL)
        return await process(job)

    except Exception as e:
        log.warning(f"Job {job.id} failed: {e}")

        processor = LLMSelector.get_job_processor(customer_id, job.id)

        if processor == Processors.OCI and not use_oci:
            LLMSelector.override_job_processor(job.id, Processors.LOCAL)
            return await process(job)

        raise e

    return result


async def process_chat_completion(
    messages: List[ChatCompletionMessageParam], customer_id: Optional[str] = None, **model_kwargs
) -> str:
    llm = LLMSelector.select(customer_id, **model_kwargs)

    chain = llm | StrOutputParser()
    result = await chain.ainvoke(messages)

    return result


async def process_chat_completion_stream(
    messages: List[ChatCompletionMessageParam], customer_id: Optional[str] = None, **model_kwargs
):
    llm = LLMSelector.select(customer_id, **model_kwargs)
    chain = llm | StrOutputParser()

    try:
        async for message in chain.astream(messages):
            yield message
    except Exception as e:
        yield json.dumps(
            {'error': e.body if hasattr(e, 'body') else str(e), 'code': e.code if hasattr(e, 'code') else None}
        ) + '\n'
