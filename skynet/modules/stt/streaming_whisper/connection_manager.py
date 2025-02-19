import asyncio
from asyncio import Task

from fastapi import WebSocket, WebSocketDisconnect

from skynet.auth.jwt import authorize
from skynet.env import (
    bypass_auth,
    whisper_flush_interval,
    whisper_max_connections,
    whisper_recorder_transcribe_after_seconds as transcribe_after_s,
)
from skynet.logs import get_logger
from skynet.modules.monitoring import CONNECTIONS_METRIC, TRANSCRIBE_CONNECTIONS_COUNTER, TRANSCRIBE_STRESS_LEVEL_METRIC
from skynet.modules.stt.streaming_whisper.cfg import recording_audio_queue, recording_ts_messages_queue
from skynet.modules.stt.streaming_whisper.meeting_connection import MeetingConnection
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class ConnectionManager:
    connections: dict[str, MeetingConnection]
    flush_audio_task: Task | None
    recording_push_ts_job_task: Task | None
    recording_send_results_task: Task | None
    recording_transcriber_task: Task | None

    def __init__(self):
        self.connections: dict[str, MeetingConnection] = {}
        self.flush_audio_task = None
        self.recording_push_ts_job_task = None
        self.recording_send_results_task = None
        self.recording_transcriber_task = None

    def start_tasks(self):
        loop = asyncio.get_running_loop()
        if not self.flush_audio_task:
            log.info('Started the flush audio worker')
            self.flush_audio_task = loop.create_task(self.flush_working_audio_worker())
        if not self.recording_push_ts_job_task:
            log.info('Started the recording push job worker')
            self.recording_push_ts_job_task = loop.create_task(self.recording_push_job_worker())
        if not self.recording_send_results_task:
            log.info('Started the recording send results worker')
            self.recording_send_results_task = loop.create_task(self.recording_send_results_worker())
        if not self.recording_transcriber_task:
            log.info('Started the recording transcriber worker')
            self.recording_transcriber_task = asyncio.create_task(utils.recording_transcriber_worker())

    async def connect(self, websocket: WebSocket, meeting_id: str, auth_token: str | None, record: bool = False):
        if not bypass_auth:
            jwt_token = utils.get_jwt(websocket.headers, auth_token)
            authorized = await authorize(jwt_token)
            if not authorized:
                await websocket.close(401, 'Bad JWT token')
                return
        await websocket.accept()
        if record:
            log.info(f'Meeting with id {meeting_id} started in recording mode')
        self.connections[meeting_id] = MeetingConnection(websocket, is_recording=record)
        self.start_tasks()
        if not record:
            CONNECTIONS_METRIC.set(len(self.connections))
            TRANSCRIBE_STRESS_LEVEL_METRIC.set(len(self.connections) / whisper_max_connections)
            TRANSCRIBE_CONNECTIONS_COUNTER.inc()
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
        was_recording = self.connections[meeting_id].recording
        try:
            del self.connections[meeting_id]
        except KeyError:
            log.warning(f'The meeting {meeting_id} doesn\'t exist anymore.')
        if not was_recording:
            CONNECTIONS_METRIC.set(len(self.connections))
            TRANSCRIBE_STRESS_LEVEL_METRIC.set(len(self.connections) / whisper_max_connections)

    async def recording_push_job_worker(self):
        while True:
            for meeting_id, meeting in self.connections.items():
                if meeting.recording:
                    log.debug(f'Meeting {meeting_id} has {len(meeting.participants)} participants')
                    for participant in meeting.participants:
                        state = meeting.participants[participant]
                        if len(state.working_audio) == 0:
                            continue
                        _, voice_timestamps = utils.is_silent(state.working_audio)
                        if len(voice_timestamps) > 0:
                            last_voice_timestamp_millis = (
                                voice_timestamps[-1]['end'] * 1000 + state.working_audio_starts_at
                            )
                            diff = (utils.now() - last_voice_timestamp_millis) / 1000
                            log.debug(f'Participant {participant} in meeting {meeting_id} has been silent for {diff} s')
                            if diff >= transcribe_after_s and not state.is_transcribing:
                                audio = state.working_audio
                                start_timestamp = state.working_audio_starts_at
                                participant_id = participant
                                await recording_audio_queue.put(
                                    {
                                        'meeting_id': meeting_id,
                                        'participant_id': participant_id,
                                        'audio': audio,
                                        'start_timestamp': start_timestamp,
                                        'previous_tokens': meeting.previous_transcription_tokens,
                                        'language': meeting.meeting_language,
                                    }
                                )
                                state.reset()
            await asyncio.sleep(1)

    async def recording_send_results_worker(self):
        while True:
            try:
                data = recording_ts_messages_queue.get_nowait()
            except asyncio.QueueEmpty:
                log.debug(f'The send results queue is empty')
                await asyncio.sleep(1)
                continue
            meeting_id = data['meeting_id']
            results = data['results']
            if meeting_id in self.connections:
                await self.connections[meeting_id].update_initial_prompt(results)
                await self.send(meeting_id, results)
            else:
                log.warning(f'The meeting {meeting_id} doesn\'t exist anymore.')
            await asyncio.sleep(1)

    async def flush_working_audio_worker(self):
        """
        Will force a transcription for all participants that haven't received any chunks for more than `flush_after_ms`
        but have accumulated some spoken audio without a transcription. This avoids merging un-transcribed "left-overs"
        to the next utterance when the participant resumes speaking.
        """
        while True:
            for meeting_id, meeting in self.connections.items():
                if not meeting.recording:
                    for participant in meeting.participants:
                        state = meeting.participants[participant]
                        diff = utils.now() - state.last_received_chunk
                        log.debug(
                            f'Participant {participant} in meeting {meeting_id} has been silent for {diff} ms and has {len(state.working_audio)} bytes of audio'
                        )
                        if diff > whisper_flush_interval and len(state.working_audio) > 0 and not state.is_transcribing:
                            log.info(f'Forcing a transcription in meeting {meeting_id} for {participant}')
                            results = await meeting.force_transcription(participant)
                            await self.send(meeting_id, results)
            await asyncio.sleep(1)
