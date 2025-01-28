from skynet.env import vector_store_type
from skynet.modules.ttt.rag.vector_store import SkynetVectorStore

vector_store = None


def get_vector_store() -> SkynetVectorStore:
    global vector_store

    if vector_store_type == 'faiss':
        from skynet.modules.ttt.rag.stores.faiss import FAISSVectorStore

        if not vector_store:
            vector_store = FAISSVectorStore()

        return vector_store
    else:
        raise ValueError(f'Unsupported vector store type: {vector_store_type}')


__all__ = ['get_vector_store']
