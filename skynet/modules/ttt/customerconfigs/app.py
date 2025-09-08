from fastapi_versionizer.versionizer import Versionizer

from skynet.utils import create_app
from skynet.modules.ttt.persistence import db
from skynet.logs import get_logger
from .v1.router import router as v1_router

log = get_logger(__name__)

app = create_app()
app.include_router(v1_router)

Versionizer(app=app, prefix_format='/v{major}', sort_routes=True).versionize()

async def app_startup():
    """Startup function for Customer Configs module."""
    await db.initialize()
    log.info('Persistence initialized')
    log.info('customerconfigs module initialized')

async def app_shutdown():
    """Shutdown function for Customer Configs module."""
    await db.close()
    log.info('customerconfigs shut down')