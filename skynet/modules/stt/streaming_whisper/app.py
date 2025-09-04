from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.connection_manager import ConnectionManager
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)

ws_connection_manager = ConnectionManager()
app = FastAPI()  # No need for CORS middleware


@app.websocket('/ws/{meeting_id}')
async def websocket_endpoint(websocket: WebSocket, meeting_id: str, auth_token: str | None = None):
    connection = await ws_connection_manager.connect(websocket, meeting_id, auth_token)
    if connection:
        connected = True
        while connected:
            try:
                chunk = await websocket.receive_bytes()
            except WebSocketDisconnect as dc:
                log.info(f'Meeting {connection.meeting_id} has ended')
                await ws_connection_manager.disconnect(connection, already_closed=True)
                connected = False
                break 
            except Exception as err:
                log.warning(f'Expected bytes, received something else, disconnecting {connection.meeting_id}. Error: \n{err}')
                await ws_connection_manager.disconnect(connection)
                connected = False
                break
            if len(chunk) == 1 and ord(b'' + chunk) == 0:
                log.info(f'Received disconnect message for {connection.meeting_id}')
                await ws_connection_manager.disconnect(connection)
                connected = False
                break
            await ws_connection_manager.process(connection, chunk, utils.now())
