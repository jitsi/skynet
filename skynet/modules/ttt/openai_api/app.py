from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from llama_cpp.server.app import create_app as create_llama_cpp_app, router as llama_router, Settings

from skynet.env import llama_n_batch, llama_n_ctx, llama_n_gpu_layers, llama_path, model_chat_format
from skynet.utils import dependencies, responses

create_llama_cpp_app(
    Settings(
        chat_format=model_chat_format,
        model=llama_path,
        n_batch=llama_n_batch,
        n_ctx=llama_n_ctx,
        n_gpu_layers=llama_n_gpu_layers,
    )
)

app = FastAPI()
app.include_router(llama_router, dependencies=dependencies, responses=responses)


@app.get("/")
def root():
    return RedirectResponse(url='docs')


__all__ = ['app']
