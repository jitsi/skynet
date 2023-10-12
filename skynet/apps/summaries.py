from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_versionizer.versionizer import versionize
from skynet.modules.monitoring import PROMETHEUS_NAMESPACE, PROMETHEUS_SUMMARIES_SUBSYSTEM

from skynet.routers.v1 import router as v1_router
from skynet.env import enable_metrics

app = FastAPI()
app.include_router(v1_router)

versionize(app=app, prefix_format='/v{major}', docs_url='/docs', enable_latest=False, sorted_routes=True)

if enable_metrics:
    from skynet.modules.monitoring import instrumentator

    instrumentator.instrument(
        app, metric_namespace=PROMETHEUS_NAMESPACE, metric_subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM
    ).expose(app, should_gzip=True)


@app.get("/")
def root():
    return RedirectResponse(url='v1/docs')


__all__ = ['app']
