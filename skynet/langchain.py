import os

from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI

from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

from skynet.models.summary import SummaryPayload

OPENAI_LLM = os.environ.get('OPENAI_LLM', 'gpt-3.5-turbo')

class Langchain:
    def __init__(self):
        self.chains = {}

    async def summarize(self, payload: SummaryPayload):
        if not payload.text:
            return ""

        llm = ChatOpenAI(temperature=0, model_name=OPENAI_LLM)
        text_splitter = RecursiveCharacterTextSplitter()
        docs = text_splitter.create_documents([payload.text])
        template = """
            For the following text, extract the following information:

            summary: Write a concise summary of the text.
            action_items: Return relevant action items from the text, as an array of strings.

            Format the output as JSON with the following keys:
            summary
            action_items

            text: {text}
        """

        parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(description="Summary of the text", name="summary", type="string"),
            ResponseSchema(description="Action items extracted from the text", name="action_items", type="array")
        ])

        chain = load_summarize_chain(
            llm,
            chain_type="map_reduce",
            combine_prompt=PromptTemplate(input_variables=["text"], template=template))

        result = await chain.arun(docs)
        result_json = parser.parse(result)

        summary, action_items = result_json.values()

        return { "summary": summary, "action_items": action_items }

    async def get_summary(self, id: str):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        history = memory.load_memory_variables({}).get("history")

        return await self.summarize(SummaryPayload(text=history))

    def update_summary(self, id: str, payload: SummaryPayload):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        memory.save_context({"input": payload.text }, {"output": ""})

        return memory.load_memory_variables({}).get("history")

    def delete_summary(self, id: str):
        if id in self.chains:
            del self.chains[id]
            return True

        return False
