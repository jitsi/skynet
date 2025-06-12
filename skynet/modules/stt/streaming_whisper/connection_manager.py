import asyncio
from asyncio import Task

from fastapi import WebSocket, WebSocketDisconnect

from skynet.auth.jwt import authorize
from skynet.env import bypass_auth, whisper_flush_interval
from skynet.logs import get_logger
from skynet.modules.monitoring import dec_ws_conn_count, inc_ws_conn_count
from skynet.modules.stt.streaming_whisper.meeting_connection import MeetingConnection
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class ConnectionManager:
    connections: dict[str, MeetingConnection]
    flush_audio_task: Task | None

    def __init__(self):
        self.connections: dict[str, MeetingConnection] = {}
        self.flush_audio_task = None

    async def connect(self, websocket: WebSocket, meeting_id: str, auth_token: str | None):
        if not bypass_auth:
            jwt_token = utils.get_jwt(websocket.headers, auth_token)
            authorized = await authorize(jwt_token)
            if not authorized:
                await websocket.close(401, 'Bad JWT token')
                return
        await websocket.accept()
        self.connections[meeting_id] = MeetingConnection(websocket)
        if self.flush_audio_task is None:
            loop = asyncio.get_running_loop()
            self.flush_audio_task = loop.create_task(self.flush_working_audio_worker())
        inc_ws_conn_count()
        log.info(f'Meeting with id {meeting_id} started. Ongoing meetings {len(self.connections)}')

    async def process(self, meeting_id: str, chunk: bytes, chunk_timestamp: int):
        log.debug(f'Processing chunk for meeting {meeting_id}')
        if meeting_id not in self.connections:
            log.warning(f'No such meeting id {meeting_id}, the connection was probably closed.')
            return
        results = await self.connections[meeting_id].process(chunk, chunk_timestamp)
        await self.send(meeting_id, results)

    async def send(self, meeting_id: str, results: list[utils.TranscriptionResponse] | None):
        if results is not None:
            for result in results:
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
        dec_ws_conn_count()

    async def flush_working_audio_worker(self):
        """
        Will force a transcription for all participants that haven't received any chunks for more than `flush_after_ms`
        but have accumulated some spoken audio without a transcription. This avoids merging un-transcribed "left-overs"
        to the next utterance when the participant resumes speaking.
        """
        while True:
            for meeting_id in self.connections:
                for participant in self.connections[meeting_id].participants:
                    state = self.connections[meeting_id].participants[participant]
                    diff = utils.now() - state.last_received_chunk
                    log.debug(
                        f'Participant {participant} in meeting {meeting_id} has been silent for {diff} ms and has {len(state.working_audio)} bytes of audio'
                    )
                    if diff > whisper_flush_interval and len(state.working_audio) > 0 and not state.is_transcribing:
                        log.info(f'Forcing a transcription in meeting {meeting_id} for {participant}')
                        results = await self.connections[meeting_id].force_transcription(participant)
                        await self.send(meeting_id, results)
            await asyncio.sleep(1)
