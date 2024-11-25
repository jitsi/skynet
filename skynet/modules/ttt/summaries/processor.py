from langchain import hub
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI, ChatOpenAI, OpenAIEmbeddings

from skynet.env import app_uuid, azure_openai_api_version, llama_n_ctx, llama_path, openai_api_base_url
from skynet.logs import get_logger

from .prompts.action_items import (
    action_items_conversation,
    action_items_emails,
    action_items_meeting,
    action_items_text,
)
from .prompts.completion import completion_conversation, completion_emails, completion_meeting, completion_text
from .prompts.summary import summary_conversation, summary_emails, summary_meeting, summary_text
from .v1.models import DocumentPayload, HintType, JobType

llm = None
log = get_logger(__name__)

trek_docs = [
    "Domane+ bike description: Shrink hills, hit new milestones and take the long way home on smooth, fast and fun Domane+ electric road bikes. Informed by decades of research and development, these e-road bikes provide a natural-feeling assist that lets you ride further and faster than you ever thought possible.. Price: $12499.99 ",
    "Checkpoint bike description: Take the road less travelled with Checkpoint. No matter if you’re exploring remote gravel roads, gravel racing or bikepacking, this adventure rig can do it all. Plus, with plenty of mounts and storage options alongside ample tyre clearance, you’ll be able to ride wherever you roam.. Price: $5999.99 ",
    "Allant+ bike description: If you're looking for a purpose-built commuter bike with the hill-flattening boost of electric power, you're looking for the Allant+. Its comfortable riding position and handy features like the included lights, mudguards, rack and removable battery make it fun to do more by bike instead of taking the car.. Price: $5999.99 ",
    "Speed Concept bike description: With drag-defying aero shapes perfected in the wind tunnel and proven in the world's toughest races, the Speed Concept is your triathlon secret weapon. You get refined aerodynamic integration, super-adjustable fit and loads of free speed for your next PR.. Price: $4699.99 ",
    "Madone bike description: You want nothing less than the very best. Meet Madone – the ultimate race bike. The Madone is the fastest road race bike we’ve ever made. It’s fast, light, smooth and designed to give you every advantage in speed and handling. Of the world’s most sophisticated road bikes, only the Madone delivers a triple threat of advanced aerodynamics, superior ride quality and unbeatable speed.. Price: $12499.99 ",
    "1120 bike description: You think the limits are best when they’re pushed, that’s why the 1120 is right for you. The 1120 is a touring bike with unlimited off-road capability. Smart, secure packing options, thoughtfully designed racks and a mountain-ready spec make it the ideal tool for your wildest adventures.. Price: $2699.99 ",
    "520 bike description: Your dream steed awaits. The 520 is a classic touring bike built for the open road. Disc brakes, a road-smoothing steel frame, rack and mudguard mounts, and a stable touring geometry make 520 the versatile choice for loaded multi-day trips and comfortable all-day adventures.. Price: $1679.99 ",
    "Dual Sport bike description: You don’t need to choose between the road and the trail. Dual Sport is an adventure-loving hybrid bike that rides both and rides both well. From path to road and dirt to doubletrack, this bike delivers a versatile, stable, comfort-first experience wherever you roam.. Price: $1159.99 ",
    "Émonda bike description: If you're looking for an ultralight, race-ready ride, Émonda is for you. This lightweight racing machine is designed to go fast on the flats and crush every climb. Plus, its aerodynamic tubing allows it to slice through the wind and shine where the road meets the sky.. Price: $11999.99 ",
    "Verve bike description: When you’re ready for everyday adventures, the Verve is your answer. The Verve is a hybrid bike built with comfort in mind. It’s perfect for cruising roads and paths in style, getting outside more and enjoying your time in the saddle. From path to road, the Verve delivers comfort, confidence and style.. Price: $819.99 ",
]

trek_docs = [Document(page_content=doc) for doc in trek_docs]


hint_type_to_prompt = {
    JobType.SUMMARY: {
        HintType.CONVERSATION: summary_conversation,
        HintType.EMAILS: summary_emails,
        HintType.MEETING: summary_meeting,
        HintType.TEXT: summary_text,
    },
    JobType.COMPLETION: {
        HintType.CONVERSATION: completion_conversation,
        HintType.EMAILS: completion_emails,
        HintType.MEETING: completion_meeting,
        HintType.TEXT: completion_text,
    },
    JobType.ACTION_ITEMS: {
        HintType.CONVERSATION: action_items_conversation,
        HintType.EMAILS: action_items_emails,
        HintType.MEETING: action_items_meeting,
        HintType.TEXT: action_items_text,
    },
}


def initialize():
    global llm

    llm = ChatOpenAI(
        model=llama_path,
        api_key='placeholder',  # use a placeholder value to bypass validation, and allow the custom base url to be used
        base_url=f'{openai_api_base_url}/v1',
        default_headers={"X-Skynet-UUID": app_uuid},
        frequency_penalty=1,
        max_retries=0,
        temperature=0,
    )


async def process(payload: DocumentPayload, job_type: JobType, model: ChatOpenAI = None) -> str:
    current_model = model or llm
    chain = None
    text = payload.text

    if not text:
        return ""

    vectorstore = Chroma.from_documents(
        documents=trek_docs,
        embedding=OpenAIEmbeddings(
            api_key='placeholder',
            base_url=f'{openai_api_base_url}',  # use a placeholder value to bypass validation, and allow the custom base url to be used
        ),
    )
    # Retrieve and generate using the relevant snippets of the blog.
    retriever = vectorstore.as_retriever()
    prompt = hub.pull("rlm/rag-prompt")

    def format_docs():
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | current_model
        | StrOutputParser()
    )

    test = rag_chain.invoke("Could you please recommend a good bike for hilly city?")
    breakpoint()

    system_message = payload.prompt or hint_type_to_prompt[job_type][payload.hint]

    prompt = ChatPromptTemplate(
        [
            ("system", system_message),
            ("human", "{text}"),
        ]
    )

    # this is a rough estimate of the number of tokens in the input text, since llama models will have a different tokenization scheme
    num_tokens = current_model.get_num_tokens(text)

    # allow some buffer for the model to generate the output
    threshold = llama_n_ctx * 3 / 4

    if num_tokens < threshold:
        chain = load_summarize_chain(current_model, chain_type="stuff", prompt=prompt)
        docs = [Document(page_content=text)]
    else:
        # split the text into roughly equal chunks
        num_chunks = num_tokens // threshold + 1
        chunk_size = num_tokens // num_chunks

        log.info(f"Splitting text into {num_chunks} chunks of {chunk_size} tokens")

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=chunk_size, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(current_model, chain_type="map_reduce", combine_prompt=prompt, map_prompt=prompt)

    result = await chain.ainvoke(input={"input_documents": docs})
    formatted_result = result['output_text'].replace('Response:', '', 1).strip()

    log.info(f'input length: {len(system_message) + len(text)}')
    log.info(f'output length: {len(formatted_result)}')

    return formatted_result


async def process_open_ai(payload: DocumentPayload, job_type: JobType, api_key: str, model_name=None) -> str:
    llm = ChatOpenAI(
        api_key=api_key,
        model_name=model_name,
        temperature=0,
    )

    return await process(payload, job_type, llm)


async def process_azure(
    payload: DocumentPayload, job_type: JobType, api_key: str, endpoint: str, deployment_name: str
) -> str:
    llm = AzureChatOpenAI(
        api_key=api_key,
        api_version=azure_openai_api_version,
        azure_endpoint=endpoint,
        azure_deployment=deployment_name,
        temperature=0,
    )

    return await process(payload, job_type, llm)
