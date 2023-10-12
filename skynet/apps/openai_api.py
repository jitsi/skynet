from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from skynet.modules.monitoring import PROMETHEUS_NAMESPACE, PROMETHEUS_OPENAI_API_SUBSYSTEM
from skynet.routers.utils import dependencies, responses
from skynet.env import enable_metrics, llama_path, llama_n_batch, llama_n_gpu_layers

from llama_cpp.server.app import Settings, router as llama_router, create_app as create_llama_cpp_app

create_llama_cpp_app(Settings(model=llama_path, n_gpu_layers=llama_n_gpu_layers, n_batch=llama_n_batch, n_ctx=4096))

app = FastAPI()
app.include_router(llama_router, dependencies=dependencies, responses=responses)

if enable_metrics:
    from skynet.modules.monitoring import instrumentator

    instrumentator.instrument(
        app, metric_namespace=PROMETHEUS_NAMESPACE, metric_subsystem=PROMETHEUS_OPENAI_API_SUBSYSTEM
    ).expose(app, should_gzip=True)


@app.get("/")
def root():
    return RedirectResponse(url='docs')


__all__ = ['app']
