import logging

from langchain.chains.summarize import load_summarize_chain
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

class Langchain:
    def __init__(self):
        self.chains = {}

    def summarize(self, text: str):
        if not text:
            return ""

        text_splitter = RecursiveCharacterTextSplitter()
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(OpenAI(temperature=0), chain_type="map_reduce")

        return chain.run(docs)

    def get_summary(self, id: str):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        history = memory.load_memory_variables({}).get("history")

        return self.summarize(history)

    def update_summary(self, id: str, text: str):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        memory.save_context({"input": text }, {"output": ""})

        return memory.load_memory_variables({}).get("history")

    def delete_summary(self, id: str):
        if (id in self.chains):
            del self.chains[id]
            return True

        return False
