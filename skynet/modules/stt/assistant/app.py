from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from skynet.logs import get_logger
from skynet.modules.stt.assistant.connection_manager import ConnectionManager
from .fixie import init

log = get_logger(__name__)

ws_connection_manager = ConnectionManager()
app = FastAPI()


@app.websocket('/ws/{session_id}')
async def websocket_endpoint(websocket: WebSocket, session_id: str, auth_token: str | None = None):
    await ws_connection_manager.connect(websocket, session_id, auth_token)
    try:
        while True:
            try:
                chunk = await websocket.receive_bytes()
            except Exception as err:
                log.warning(f'Expected bytes, received something else, disconnecting {session_id}. Error: \n{err}')
                ws_connection_manager.disconnect(session_id)
                break
            if len(chunk) == 1 and ord(b'' + chunk) == 0:
                log.info(f'Received disconnect message for {session_id}')
                ws_connection_manager.disconnect(session_id)
                break
            await ws_connection_manager.process(session_id, chunk)
    except WebSocketDisconnect:
        ws_connection_manager.disconnect(session_id)
        log.info(f'Session {session_id} has ended')


def app_startup():
    init()

    log.info('assistant module initialized')


__all__ = ['app', 'app_startup']
