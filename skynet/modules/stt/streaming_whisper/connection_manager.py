import time
from fastapi import WebSocket, WebSocketDisconnect

from skynet.auth.jwt import authorize
from skynet.env import bypass_auth
from skynet.logs import get_logger
from skynet.modules.monitoring import CONNECTIONS_METRIC, TRANSCRIBE_DURATION_METRIC
from skynet.modules.stt.streaming_whisper.meeting_connection import MeetingConnection
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class ConnectionManager:
    connections: dict[str, MeetingConnection]

    def __init__(self):
        self.connections: dict[str, MeetingConnection] = {}

    async def connect(self, websocket: WebSocket, meeting_id: str, auth_token: str | None):
        if not bypass_auth:
            authorized = await authorize(auth_token)
            if not authorized:
                await websocket.close(401, 'Bad JWT token')
                return
        await websocket.accept()
        self.connections[meeting_id] = MeetingConnection(websocket)
        CONNECTIONS_METRIC.set(len(self.connections))
        log.info(f'Meeting with id {meeting_id} started. Ongoing meetings {len(self.connections)}')

    async def process(self, meeting_id: str, chunk: bytes, chunk_timestamp: int):
        log.debug(f'Processing chunk for meeting {meeting_id}')
        if meeting_id not in self.connections:
            log.warning(f'No such meeting id {meeting_id}, the connection was probably closed.')
            return
        start = time.perf_counter_ns()
        results = await self.connections[meeting_id].process(chunk, chunk_timestamp)
        end = time.perf_counter_ns()
        processing_time = (end - start) / 1e6 / 1000
        TRANSCRIBE_DURATION_METRIC.observe(processing_time)
        if results is not None:
            for result in results:
                await self.send(meeting_id, result)

    async def send(self, meeting_id: str, result: utils.TranscriptionResponse):
        try:
            await self.connections[meeting_id].ws.send_json(result.model_dump())
        except WebSocketDisconnect as e:
            log.warning(f'Meeting {meeting_id}: the connection was closed before sending all results: {e}')
            self.disconnect(meeting_id)
        except Exception as ex:
            log.error(f'Meeting {meeting_id}: exception while sending transcription results {ex}')

    def disconnect(self, meeting_id: str):
        try:
            del self.connections[meeting_id]
        except KeyError:
            log.warning(f'The meeting {meeting_id} doesn\'t exist anymore.')
        CONNECTIONS_METRIC.set(len(self.connections))
