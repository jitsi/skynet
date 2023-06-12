from langchain.chains.summarize import load_summarize_chain
from langchain.llms import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter

class Langchain:
    def summarize(self, text: str):
        text_splitter = RecursiveCharacterTextSplitter()
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(OpenAI(temperature=0), chain_type="map_reduce")

        return chain.run(docs)
