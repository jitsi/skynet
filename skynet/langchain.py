import os

from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI

from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

from skynet.models.summary import SummaryPayload

OPENAI_LLM = os.environ.get('OPENAI_LLM', 'gpt-3.5-turbo')

class Langchain:
    def __init__(self):
        self.chains = {}

    def summarize(self, payload: SummaryPayload):
        if not payload.text:
            return ""

        llm = ChatOpenAI(temperature=0, model_name=OPENAI_LLM)
        text_splitter = RecursiveCharacterTextSplitter()
        docs = text_splitter.create_documents([payload.text])
        chain = load_summarize_chain(llm, chain_type="map_reduce")

        summary = chain.run(docs)

        if payload.retrieveActionItems:
            action_items_chain = load_summarize_chain(
                llm,
                chain_type="map_reduce",
                combine_prompt=PromptTemplate(input_variables=["text"], template="Return relevant action items, if any, for the following text: {text}"))

            action_items = action_items_chain.run(docs)
        else:
            action_items = []

        return { "summary": summary, "action_items": action_items }

    def get_summary(self, id: str, retrieveActionItems: bool = False):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        history = memory.load_memory_variables({}).get("history")

        return self.summarize(SummaryPayload(text=history, retrieveActionItems=retrieveActionItems))

    def update_summary(self, id: str, payload: SummaryPayload):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        memory.save_context({"input": payload.text }, {"output": ""})

        return memory.load_memory_variables({}).get("history")

    def delete_summary(self, id: str):
        if (id in self.chains):
            del self.chains[id]
            return True

        return False
