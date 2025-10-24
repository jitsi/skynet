import asyncio
from asyncio import Task

from fastapi import WebSocket, WebSocketDisconnect

from skynet.auth.jwt import authorize
from skynet.env import bypass_auth, whisper_flush_interval
from skynet.logs import get_logger
from skynet.modules.monitoring import update_ws_conn_count
from skynet.modules.stt.streaming_whisper.meeting_connection import MeetingConnection
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class ConnectionManager:
    connections: list[MeetingConnection]
    flush_audio_task: Task | None

    def __init__(self):
        self.connections: list[MeetingConnection] = []
        self.flush_audio_task = None

    async def connect(self, websocket: WebSocket, meeting_id: str, auth_token: str | None):
        if not bypass_auth:
            jwt_token = utils.get_jwt(websocket.headers, auth_token)
            authorized = await authorize(jwt_token)
            if not authorized:
                await websocket.close(401, 'Bad JWT token')
                return
        await websocket.accept()
        connection = MeetingConnection(websocket, meeting_id)
        self.connections.append(connection)
        if self.flush_audio_task is None:
            loop = asyncio.get_running_loop()
            self.flush_audio_task = loop.create_task(self.flush_working_audio_worker())
        current_connections = len(self.connections)
        log.info(f'Meeting with id {meeting_id} started. Ongoing meetings {current_connections}')
        await update_ws_conn_count(current_connections)
        return connection

    async def process(self, connection: MeetingConnection, chunk: bytes, chunk_timestamp: int):
        log.debug(f'Processing chunk for meeting {connection.meeting_id}')

        try:
            results = await connection.process(chunk, chunk_timestamp)
            await self.send(connection, results)
        except Exception as e:
            log.error(f'Error processing chunk for meeting {connection.meeting_id}: {e}')
            await self.disconnect(connection)

    async def send(self, connection: MeetingConnection, results: list[utils.TranscriptionResponse] | None):
        if results is not None:
            for result in results:
                try:
                    await connection.ws.send_json(result.model_dump())
                except WebSocketDisconnect as e:
                    log.warning(
                        f'Meeting {connection.meeting_id}: the connection was closed before sending all results: {e}'
                    )
                    await self.disconnect(connection, True)
                    break  # stop trying to send results if websocket is disconnected
                except Exception as ex:
                    log.error(f'Meeting {connection.meeting_id}: exception while sending transcription results {ex}')

    async def disconnect(self, connection: MeetingConnection, already_closed=False):
        log.info(
            f"Closed {connection.meeting_id} | Audio: {connection.total_audio_received_s}s | "
            + f"Interims: {connection.total_interims} | Finals: {connection.total_finals}"
        )
        try:
            self.connections.remove(connection)
        except ValueError:
            log.warning(f'The connection for meeting {connection.meeting_id} doesn\'t exist in the list anymore.')
        if not already_closed:
            await connection.close()
        else:
            # mark connection as disconnected
            connection.disconnect()
        remaining_connections = len(self.connections)
        log.info(f'Disconnected meeting {connection.meeting_id}, remaining connections {remaining_connections}')
        await update_ws_conn_count(remaining_connections)

    async def flush_working_audio_worker(self):
        """
        Will force a transcription for all participants that haven't received any chunks for more than `flush_after_ms`
        but have accumulated some spoken audio without a transcription. This avoids merging un-transcribed "left-overs"
        to the next utterance when the participant resumes speaking.
        """
        while True:
            for connection in self.connections:
                for participant in connection.participants:
                    state = connection.participants[participant]
                    diff = utils.now() - state.last_received_chunk
                    log.debug(
                        f'Participant {participant} in meeting {connection.meeting_id} has been silent for {diff} ms and has {len(state.working_audio)} bytes of audio'
                    )
                    if diff > whisper_flush_interval and len(state.working_audio) > 0 and not state.is_transcribing:
                        log.info(f'Forcing a transcription in meeting {connection.meeting_id} for {participant}')
                        results = await connection.force_transcription(participant)
                        await self.send(connection, results)
            await asyncio.sleep(1)
