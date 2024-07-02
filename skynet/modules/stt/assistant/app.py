from fastapi import FastAPI
from fastapi_versionizer.versionizer import Versionizer

from skynet.logs import get_logger
from .fixie import init

from .v1.router import router as v1_router

log = get_logger(__name__)

app = FastAPI()
app.include_router(v1_router)

Versionizer(app=app, prefix_format='/v{major}', sort_routes=True).versionize()


def app_startup():
    init()

    log.info('assistant module initialized')


__all__ = ['app', 'app_startup']
