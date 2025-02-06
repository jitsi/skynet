from skynet.env import use_s3, vector_store_type
from skynet.logs import get_logger
from skynet.modules.ttt.rag.vector_store import SkynetVectorStore

vector_store = None
log = get_logger(__name__)


async def get_vector_store() -> SkynetVectorStore:
    global vector_store

    if vector_store_type == 'faiss':
        if not vector_store:
            from skynet.modules.ttt.rag.stores.faiss import FAISSVectorStore

            vector_store = FAISSVectorStore()
            await vector_store.initialize()
            log.info('FAISS vector store initialized')

        return vector_store
    else:
        raise ValueError(f'Unsupported vector store type: {vector_store_type}')


__all__ = ['get_vector_store']
