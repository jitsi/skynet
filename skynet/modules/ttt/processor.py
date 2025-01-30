from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import FlashrankRerank
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from skynet.auth.user_info import CredentialsType, get_credentials
from skynet.env import app_uuid, azure_openai_api_version, llama_n_ctx, llama_path, openai_api_base_url
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
        log.info(doc.metadata.get('source'))

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

    return Processors.LOCAL


def get_local_llm(**kwargs):
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


async def assist(payload: DocumentPayload, customer_id: str | None = None, model: ChatOpenAI = None) -> str:
    current_model = model or get_local_llm(max_completion_tokens=payload.max_completion_tokens)
    text = payload.text

    if customer_id:
        vector_store = await get_vector_store().get(customer_id)

        if vector_store:
            base_retriever = vector_store.as_retriever(search_kwargs={'k': 5})
            retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=base_retriever)

            prompt_template = '''
            Use the following pieces of information to answer the user's question.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.

            Context: {rag_context}
            Question: {question}

            Answer the question and provide additional helpful information, based on the pieces of information, if applicable. Be succinct.
            '''

            prompt = PromptTemplate(template=prompt_template, input_variables=['rag_context', 'question'])

            rag_chain = (
                {'rag_context': retriever | format_docs, 'question': RunnablePassthrough()}
                | prompt
                | current_model
                | StrOutputParser()
            )

            return await rag_chain.ainvoke(text)

    return text


async def summarize(payload: DocumentPayload, job_type: JobType, model: ChatOpenAI = None) -> str:
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


async def process(payload: DocumentPayload, job_type: JobType, customer_id: str | None = None) -> str:
    processor = get_job_processor(customer_id)
    options = get_credentials(customer_id)

    secret = options.get('secret')

    if processor == Processors.OPENAI:
        log.info(f'Forwarding inference to OpenAI for customer {customer_id}')

        model = options.get('metadata').get('model')
        result = await process_open_ai(payload, job_type, secret, model, customer_id)
    elif processor == Processors.AZURE:
        log.info(f'Forwarding inference to Azure openai for customer {customer_id}')

        metadata = options.get('metadata')
        result = await process_azure(
            payload, job_type, secret, metadata.get('endpoint'), metadata.get('deploymentName'), customer_id
        )
    else:
        if customer_id:
            log.info(f'Customer {customer_id} has no API key configured, falling back to local processing')

        if job_type == JobType.ASSIST:
            result = await assist(payload, customer_id)
        else:
            result = await summarize(payload, job_type)

    return result
