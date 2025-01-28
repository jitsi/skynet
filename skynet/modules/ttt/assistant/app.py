from fastapi_versionizer.versionizer import Versionizer

from skynet.env import embeddings_model_n_ctx, embeddings_model_path, openai_embeddings_api_port

from skynet.logs import get_logger
from skynet.modules.ttt.openai_api.app import initialize as initialize_openai_api, TaskType
from skynet.utils import create_app
from ..persistence import db
from .v1.router import router as v1_router


log = get_logger(__name__)

app = create_app()
app.include_router(v1_router)

Versionizer(app=app, prefix_format='/v{major}', sort_routes=True).versionize()


async def app_startup():
    initialize_openai_api(
        model_path=embeddings_model_path,
        max_model_len=embeddings_model_n_ctx,
        port=openai_embeddings_api_port,
        task=TaskType.EMBEDDING,
    )

    await db.initialize()
    log.info('Persistence initialized')

    log.info('assistant module initialized')


__all__ = ['app', 'app_startup']
