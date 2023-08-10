from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_versionizer.versionizer import versionize

from skynet.routers.v1 import router as v1_router
from skynet.routers.utils import dependencies, responses
from skynet.env import llama_path, llama_n_batch, llama_n_gpu_layers

from llama_cpp.server.app import Settings, router as llama_router, create_app as create_llama_cpp_app

app = FastAPI()
app.include_router(v1_router)

versions = versionize(
    app=app,
    prefix_format='/summaries/v{major}',
    docs_url='/docs',
    enable_latest=True,
    sorted_routes=True
)


# Add additional routes after versioning so they are not versioned.

create_llama_cpp_app(Settings(model=llama_path,
                              n_gpu_layers=llama_n_gpu_layers,
                              n_batch=llama_n_batch,
                              n_ctx=2048))

# Need to create a new app in order to have our dependencies work
llama_app = FastAPI()
llama_app.include_router(llama_router, dependencies=dependencies, responses=responses)

app.mount("/openai-api", llama_app)

@app.get("/")
def root():
    return RedirectResponse(url='/latest/docs')

@app.get("/openai-api")
def root():
    return RedirectResponse(url='/openai-api/docs')

@app.get("/healthz")
def health():
    """
    Health checking for k8s.
    """

    return {"status": "ok"}
