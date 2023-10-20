from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_versionizer.versionizer import versionize

from skynet.env import enable_metrics
from skynet.logs import get_logger
from skynet.modules.monitoring import PROMETHEUS_NAMESPACE, PROMETHEUS_SUMMARIES_SUBSYSTEM
from skynet.modules.persistence import db
from skynet.modules.ttt.jobs import start_monitoring_jobs
from skynet.modules.ttt.summaries import initialize as initialize_summaries
from skynet.routers.v1 import router as v1_router


log = get_logger('skynet.summaries')

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


async def app_startup():
    initialize_summaries()
    log.info('Summaries initialized')

    await db.initialize()
    log.info('Persistence initialized')

    start_monitoring_jobs()


__all__ = ['app', 'app_startup']
