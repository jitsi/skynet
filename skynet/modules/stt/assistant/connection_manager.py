from fastapi import WebSocket, WebSocketDisconnect

from skynet.auth.jwt import authorize
from skynet.env import bypass_auth
from skynet.logs import get_logger
from skynet.modules.stt.assistant.models import AssistantResponse
from skynet.modules.stt.assistant.session_connection import SessionConnection
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class ConnectionManager:
    connections: dict[str, SessionConnection]

    def __init__(self):
        self.connections: dict[str, SessionConnection] = {}

    async def connect(self, websocket: WebSocket, session_id: str, auth_token: str | None):
        if not bypass_auth:
            jwt_token = utils.get_jwt(websocket.headers, auth_token)
            authorized = await authorize(jwt_token)
            if not authorized:
                await websocket.close(401, 'Bad JWT token')
                return
        await websocket.accept()
        self.connections[session_id] = SessionConnection(websocket)

        log.info(f'Session with id {session_id} started. Ongoing sessions {len(self.connections)}')

    async def process(self, session_id: str, chunk: bytes):
        log.debug(f'Processing chunk for session {session_id}')

        if session_id not in self.connections:
            log.warning(f'No such session id {session_id}, the connection was probably closed.')
            return

        for result in self.connections[session_id].process(chunk):
            await self.send(session_id, result)

    async def send(self, session_id: str, result: AssistantResponse | None):
        if result is not None:
            try:
                await self.connections[session_id].ws.send_json(AssistantResponse.model_dump(result))
            except WebSocketDisconnect as e:
                log.warning(f'Session {session_id}: the connection was closed before sending all results: {e}')
                self.disconnect(session_id)
            except Exception as ex:
                log.error(f'Session {session_id}: exception while sending transcription results {ex}')

    def disconnect(self, session_id: str):
        try:
            del self.connections[session_id]
        except KeyError:
            log.warning(f'The session {session_id} doesn\'t exist anymore.')
