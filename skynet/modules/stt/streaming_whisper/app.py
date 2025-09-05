from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException

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
        while connection.connected:
            try:
                chunk = await websocket.receive_bytes()
            except WebSocketDisconnect:
                log.info(f'Meeting {connection.meeting_id} has ended')
                await ws_connection_manager.disconnect(connection, already_closed=True)
                break
            except WebSocketException as wserr:
                log.warning(f'Error on websocket {connection.meeting_id}. Error {wserr.__class__}: \n{wserr}')
                await ws_connection_manager.disconnect(connection)
                break
            except Exception as err:
                log.warning(
                    f'Expected bytes, received something else, disconnecting {connection.meeting_id}. Error {err.__class__}: \n{err}'
                )
                await ws_connection_manager.disconnect(connection)
                break
            if len(chunk) == 1 and ord(b'' + chunk) == 0:
                log.info(f'Received disconnect message for {connection.meeting_id}')
                await ws_connection_manager.disconnect(connection)
                break
            await ws_connection_manager.process(connection, chunk, utils.now())
