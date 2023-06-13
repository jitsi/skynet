import logging

from langchain.chains.summarize import load_summarize_chain
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

from skynet.models.summary import SummaryPayload

class Langchain:
    def __init__(self):
        self.chains = {}

    def summarize(self, payload: SummaryPayload):
        if not payload.text:
            return ""

        text_splitter = RecursiveCharacterTextSplitter()
        docs = text_splitter.create_documents([payload.text])
        chain = load_summarize_chain(OpenAI(temperature=0), chain_type="map_reduce")

        return chain.run(docs)

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
