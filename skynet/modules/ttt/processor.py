from operator import itemgetter

from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import FlashrankRerank
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.chat_models import ChatOCIGenAI
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from skynet.auth.user_info import CredentialsType, get_credentials
from skynet.env import (
    app_uuid,
    azure_openai_api_version,
    llama_n_ctx,
    llama_path,
    oci_auth_type,
    oci_compartment_id,
    oci_config_profile,
    oci_model_id,
    oci_service_endpoint,
    openai_api_base_url,
    use_oci,
)
from skynet.logs import get_logger

from skynet.modules.ttt.rag.app import get_vector_store
from skynet.modules.ttt.summaries.prompts.action_items import (
    action_items_conversation,
    action_items_emails,
    action_items_meeting,
    action_items_text,
)
from skynet.modules.ttt.summaries.prompts.summary import (
    summary_conversation,
    summary_emails,
    summary_meeting,
    summary_text,
)
from skynet.modules.ttt.summaries.v1.models import DocumentPayload, HintType, JobType, Processors

log = get_logger(__name__)


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
}


def format_docs(docs: list[Document]) -> str:
    for doc in docs:
        log.debug(doc.metadata.get('source'))

    return '\n\n'.join(doc.page_content for doc in docs)


def get_job_processor(customer_id: str) -> Processors:
    options = get_credentials(customer_id)
    secret = options.get('secret')
    api_type = options.get('type')

    if secret:
        if api_type == CredentialsType.OPENAI.value:
            return Processors.OPENAI
        elif api_type == CredentialsType.AZURE_OPENAI.value:
            return Processors.AZURE

    # OCI doesn't have a secret since it's provisioned for the instance as a whole.
    if api_type == CredentialsType.OCI.value:
        return Processors.OCI

    return Processors.LOCAL


# Cached instance since it performs some initialization we'd
# like to avoid on every request.
oci_llm = None


def get_oci_llm(max_tokens):
    global oci_llm

    if oci_llm is None:
        oci_llm = ChatOCIGenAI(
            model_id=oci_model_id,
            service_endpoint=oci_service_endpoint,
            compartment_id=oci_compartment_id,
            provider="meta",
            model_kwargs={"temperature": 0, "frequency_penalty": 1, "max_tokens": max_tokens},
            auth_type=oci_auth_type,
            auth_profile=oci_config_profile,
        )
    return oci_llm


def get_local_llm(**kwargs):
    # OCI hosted llama
    if use_oci:
        return get_oci_llm(kwargs['max_completion_tokens'])

    # Locally hosted llama
    return ChatOpenAI(
        model=llama_path,
        api_key='placeholder',  # use a placeholder value to bypass validation, and allow the custom base url to be used
        base_url=f'{openai_api_base_url}/v1',
        default_headers={'X-Skynet-UUID': app_uuid},
        frequency_penalty=1,
        max_retries=0,
        temperature=0,
        **kwargs,
    )


compressor = FlashrankRerank()


async def assist(payload: DocumentPayload, customer_id: str | None = None, model: BaseChatModel = None) -> str:
    current_model = model or get_local_llm(max_completion_tokens=payload.max_completion_tokens)

    store = await get_vector_store()
    vector_store = await store.get(customer_id)

    base_retriever = vector_store.as_retriever(search_kwargs={'k': 3}) if vector_store else None
    retriever = (
        ContextualCompressionRetriever(base_compressor=compressor, base_retriever=base_retriever)
        if base_retriever
        else None
    )

    prompt_template = '''
    Context: {context}
    Additional context: {additional_context}
    User prompt: {user_prompt}
    '''

    prompt = PromptTemplate(template=prompt_template, input_variables=['context', 'user_prompt', 'additional_context'])

    rag_chain = (
        {
            'context': (itemgetter('user_prompt') | retriever | format_docs) if retriever else lambda x: '',
            'user_prompt': itemgetter('user_prompt'),
            'additional_context': itemgetter('additional_context'),
        }
        | prompt
        | current_model
        | StrOutputParser()
    )

    return await rag_chain.ainvoke(input={'user_prompt': payload.prompt, 'additional_context': payload.text})


async def summarize(payload: DocumentPayload, job_type: JobType, model: BaseChatModel = None) -> str:
    current_model = model or get_local_llm(max_completion_tokens=payload.max_completion_tokens)
    chain = None
    text = payload.text

    if not text:
        return ''

    system_message = payload.prompt or hint_type_to_prompt[job_type][payload.hint]

    prompt = ChatPromptTemplate(
        [
            ('system', system_message),
            ('human', '{text}'),
        ]
    )

    # this is a rough estimate of the number of tokens in the input text, since llama models will have a different tokenization scheme
    num_tokens = current_model.get_num_tokens(text)

    # allow some buffer for the model to generate the output
    threshold = llama_n_ctx * 3 / 4

    if num_tokens < threshold:
        chain = load_summarize_chain(current_model, chain_type='stuff', prompt=prompt)
        docs = [Document(page_content=text)]
    else:
        # split the text into roughly equal chunks
        num_chunks = num_tokens // threshold + 1
        chunk_size = num_tokens // num_chunks

        log.info(f'Splitting text into {num_chunks} chunks of {chunk_size} tokens')

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=chunk_size, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(current_model, chain_type='map_reduce', combine_prompt=prompt, map_prompt=prompt)

    result = await chain.ainvoke(input={'input_documents': docs})
    formatted_result = result['output_text'].replace('Response:', '', 1).strip()

    log.info(f'input length: {len(system_message) + len(text)}')
    log.info(f'output length: {len(formatted_result)}')

    return formatted_result


async def process_open_ai(
    payload: DocumentPayload, job_type: JobType, api_key: str, model_name=None, customer_id: str | None = None
) -> str:
    llm = ChatOpenAI(
        api_key=api_key,
        max_completion_tokens=payload.max_completion_tokens,
        model_name=model_name,
        temperature=0,
    )

    if job_type == JobType.ASSIST:
        return await assist(payload, customer_id, llm)

    return await summarize(payload, job_type, llm)


async def process_azure(
    payload: DocumentPayload,
    job_type: JobType,
    api_key: str,
    endpoint: str,
    deployment_name: str,
    customer_id: str | None = None,
) -> str:
    llm = AzureChatOpenAI(
        api_key=api_key,
        api_version=azure_openai_api_version,
        azure_endpoint=endpoint,
        azure_deployment=deployment_name,
        max_completion_tokens=payload.max_completion_tokens,
        temperature=0,
    )

    if job_type == JobType.ASSIST:
        return await assist(payload, customer_id, llm)

    return await summarize(payload, job_type, llm)


async def process_oci(payload: DocumentPayload, job_type: JobType, customer_id: str | None = None) -> str:
    llm = get_oci_llm(payload.max_completion_tokens)

    if job_type == JobType.ASSIST:
        return await assist(payload, customer_id, llm)

    return await summarize(payload, job_type, llm)


async def process(payload: DocumentPayload, job_type: JobType, customer_id: str | None = None) -> str:
    processor = get_job_processor(customer_id)
    options = get_credentials(customer_id)

    secret = options.get('secret')

    if processor == Processors.OPENAI:
        log.info(f'Forwarding inference to OpenAI for customer {customer_id}')

        model = options.get('metadata').get('model')
        result = await process_open_ai(payload, job_type, secret, model, customer_id)
    elif processor == Processors.AZURE:
        log.info(f"Forwarding inference to Azure-OpenAI for customer {customer_id}")

        metadata = options.get('metadata')
        result = await process_azure(
            payload, job_type, secret, metadata.get('endpoint'), metadata.get('deploymentName'), customer_id
        )
    elif processor == Processors.OCI:
        log.info(f"Forwarding inference to OCI for customer {customer_id}")

        result = await process_oci(payload, job_type, customer_id)
    else:
        if customer_id:
            log.info(f'Customer {customer_id} has no API key configured, falling back to local processing')

        if job_type == JobType.ASSIST:
            result = await assist(payload, customer_id)
        else:
            result = await summarize(payload, job_type)

    return result
