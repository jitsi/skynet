from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.connection_manager import ConnectionManager
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)

ws_connection_manager = ConnectionManager()
app = FastAPI()  # No need for CORS middleware


@app.websocket('/ws/{meeting_id}')
async def websocket_endpoint(websocket: WebSocket, meeting_id: str, auth_token: str | None = None):
    await ws_connection_manager.connect(websocket, meeting_id, auth_token)
    try:
        while True:
            try:
                chunk = await websocket.receive_bytes()
            except Exception as err:
                log.warning(f'Expected bytes, received something else, disconnecting {meeting_id}. Error: \n{err}')
                ws_connection_manager.disconnect(meeting_id)
                break
            if len(chunk) == 1 and ord(b'' + chunk) == 0:
                log.info(f'Received disconnect message for {meeting_id}')
                ws_connection_manager.disconnect(meeting_id)
                break
            await ws_connection_manager.process(meeting_id, chunk, utils.now())
    except WebSocketDisconnect:
        ws_connection_manager.disconnect(meeting_id)
        log.info(f'Meeting {meeting_id} has ended')
