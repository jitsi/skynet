import timeit

from langchain.chains.summarize import load_summarize_chain
from langchain.llms import CTransformers

from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

from skynet.models.v1.summary import SummaryPayload, SummaryResult
from skynet.env import llama_path
from skynet.prompts.summary import summary_template

class SummariesChain:
    def __init__(self):
        self.chains = {}
        self.llm = CTransformers(
            model=llama_path,
            model_type='llama',
            config={'max_new_tokens': 1000, 'temperature': 0.01}
        )

    async def summarize(self, payload: SummaryPayload) -> SummaryResult:
        if not payload.text:
            return { "summary": "" }

        start = timeit.default_timer()

        text_splitter = RecursiveCharacterTextSplitter()
        docs = text_splitter.create_documents([payload.text])

        prompt = PromptTemplate(template=summary_template, input_variables=["text"])

        chain = load_summarize_chain(
            self.llm,
            chain_type="map_reduce",
            combine_prompt=prompt)

        result = chain.run(docs)

        end = timeit.default_timer()

        print(f"Time to retrieve response: {end - start}")

        return { "summary": result }

    async def get_summary(self, id: str):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        history = memory.load_memory_variables({}).get("history")

        return await self.summarize(SummaryPayload(text=history))

    def update_summary_context(self, id: str, payload: SummaryPayload):
        memory = self.chains.setdefault(id, ConversationBufferMemory())
        memory.save_context({"input": payload.text }, {"output": ""})

        return memory.load_memory_variables({}).get("history")

    def delete_summary_context(self, id: str):
        if id in self.chains:
            del self.chains[id]
            return True

        return False
