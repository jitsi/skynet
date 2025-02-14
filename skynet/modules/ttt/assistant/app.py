from fastapi_versionizer.versionizer import Versionizer

from skynet.logs import get_logger
from skynet.modules.ttt.rag.app import get_vector_store
from skynet.utils import create_app
from ..persistence import db
from .v1.router import router as v1_router


log = get_logger(__name__)

app = create_app()
app.include_router(v1_router)

Versionizer(app=app, prefix_format='/v{major}', sort_routes=True).versionize()


async def app_startup():
    await db.initialize()
    log.info('Persistence initialized')

    await get_vector_store()
    log.info('Vector store initialized')

    log.info('assistant module initialized')


__all__ = ['app', 'app_startup']
