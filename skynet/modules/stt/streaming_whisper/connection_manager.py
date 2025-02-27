import asyncio
from asyncio import Task

import aiofiles
import aiofiles.os
from aiomultiprocess import Worker
from aiomultiprocess.core import get_manager

from fastapi import WebSocket, WebSocketDisconnect

import skynet.modules.stt.shared.utils as shared_utils

from skynet.auth.jwt import authorize
from skynet.env import (
    bypass_auth,
    whisper_flush_interval,
    whisper_max_connections,
    whisper_recorder_audio_path as recording_audio_folder,
    whisper_recorder_num_processes,
    whisper_recorder_transcribe_after_seconds as transcribe_after_s,
)
from skynet.logs import get_logger
from skynet.modules.monitoring import CONNECTIONS_METRIC, TRANSCRIBE_CONNECTIONS_COUNTER, TRANSCRIBE_STRESS_LEVEL_METRIC
from skynet.modules.stt.shared.models.transcription_response import TranscriptionResponse
from skynet.modules.stt.shared.processes.recording_worker import recording_transcriber_worker
from skynet.modules.stt.streaming_whisper.meeting_connection import MeetingConnection
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class ConnectionManager:
    connections: dict[str, MeetingConnection]
    audio_queue: asyncio.Queue
    transcriptions_queue: asyncio.Queue
    running_tasks: set[Task]
    running_processes: set[Worker]

    def __init__(self):
        self.connections: dict[str, MeetingConnection] = {}
        self.audio_queue = get_manager().Queue()
        self.transcriptions_queue = get_manager().Queue()
        self.running_tasks = set()
        self.running_processes = set()
        self.create_task('flush_working_audio_worker')

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
            if not self.running_processes:
                self.create_task('recording_push_task')
                self.create_task('recording_send_results_task')
                self.create_task('recording_process_monitor')
                self.start_recording_processes()

        self.connections[meeting_id] = MeetingConnection(websocket, is_recording=record)
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

    async def send(self, meeting_id: str, results: list[TranscriptionResponse] | None):
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
                        diff = shared_utils.now() - state.last_received_chunk
                        log.debug(
                            f'Participant {participant} in meeting {meeting_id} has been silent for {diff} ms and has {len(state.working_audio)} bytes of audio'
                        )
                        if diff > whisper_flush_interval and len(state.working_audio) > 0 and not state.is_transcribing:
                            log.info(f'Forcing a transcription in meeting {meeting_id} for {participant}')
                            results = await meeting.force_transcription(participant)
                            await self.send(meeting_id, results)
            await asyncio.sleep(1)

    async def recording_push_task(self):
        sleep_for = 2
        while True:
            for meeting_id, meeting in self.connections.items():
                if meeting.recording:
                    log.debug(f'Meeting {meeting_id} has {len(meeting.participants)} participants')
                    for participant in meeting.participants:
                        state = meeting.participants[participant]
                        if len(state.working_audio) == 0:
                            await asyncio.sleep(sleep_for)
                            continue
                        _, voice_timestamps = await asyncio.to_thread(utils.is_silent, state.working_audio)
                        if len(voice_timestamps) > 0:
                            last_voice_timestamp_millis = (
                                voice_timestamps[-1]['end'] * 1000 + state.working_audio_starts_at
                            )
                            diff = (shared_utils.now() - last_voice_timestamp_millis) / 1000
                            log.debug(f'Participant {participant} in meeting {meeting_id} has been silent for {diff} s')
                            if diff >= transcribe_after_s:
                                audio = state.working_audio
                                start_timestamp = state.working_audio_starts_at
                                state.reset()
                                participant_id = participant
                                if not await aiofiles.os.path.exists(f'{recording_audio_folder}'):
                                    try:
                                        await aiofiles.os.mkdir(f'{recording_audio_folder}')
                                    except Exception as e:
                                        log.error(f'Failed to create folder {recording_audio_folder}: {e}')

                                audio_file_name = f'{meeting_id}-{participant_id}-{shared_utils.now()}'

                                try:
                                    async with aiofiles.open(f'{recording_audio_folder}/{audio_file_name}', 'wb') as f:
                                        await f.write(audio)
                                except Exception as e:
                                    log.error(
                                        f'Failed to write audio to {recording_audio_folder}/{audio_file_name}: {e}'
                                    )
                                    await asyncio.sleep(sleep_for)
                                    continue
                                metadata = {
                                    'meeting_id': meeting_id,
                                    'participant_id': participant_id,
                                    'audio_path': f'{recording_audio_folder}/{audio_file_name}',
                                    'start_timestamp': start_timestamp,
                                }
                                try:
                                    self.audio_queue.put_nowait(metadata)
                                except Exception as e:
                                    log.error(f'Failed to put metadata in the audio queue: {e}')
                                    await asyncio.sleep(sleep_for)
                                    continue
                        else:
                            state.reset()
                            await asyncio.sleep(sleep_for)
                            continue
            await asyncio.sleep(sleep_for)

    async def recording_send_results_task(self):
        while True:
            try:
                data = self.transcriptions_queue.get_nowait()
            except Exception:
                await asyncio.sleep(1)
                continue
            meeting_id = data['meeting_id']
            results = data['results']
            if meeting_id in self.connections:
                await self.connections[meeting_id].update_initial_prompt(results)
                await self.send(meeting_id, results)
            else:
                log.warning(f'The meeting {meeting_id} doesn\'t exist anymore, dropping the transcription results')
            self.transcriptions_queue.task_done()
            await asyncio.sleep(1)

    async def recording_process_monitor(self):
        while True:
            for worker in self.running_processes:
                if worker.is_alive():
                    continue
                name = worker.name
                log.error(f'Worker {worker.name} is dead.')
                self.running_processes.remove(worker)
                log.warning(f'Restarting worker {worker.name}')
                new_worker = Worker(
                    name=name,
                    target=recording_transcriber_worker,
                    args=(self.audio_queue, self.transcriptions_queue, name),
                )
                new_worker.start()
                self.running_processes.add(new_worker)
            await asyncio.sleep(1)

    def create_task(self, task: str):
        run = getattr(self, task)
        new_task = asyncio.create_task(run(), name=task)
        self.running_tasks.add(new_task)
        new_task.add_done_callback(self.task_exception_callback)

    def start_recording_processes(self):
        for i in range(whisper_recorder_num_processes):
            worker_name = f'recording_transcriber_worker-{i}'
            worker = Worker(
                name=worker_name,
                target=recording_transcriber_worker,
                args=(self.audio_queue, self.transcriptions_queue, worker_name),
            )
            worker.start()
            self.running_processes.add(worker)

    def task_exception_callback(self, task: Task):
        log.info(f'Task {task.get_name()} finished')
        if task.exception():
            name = task.get_name()
            log.error(f'Task {name} stopped with Exception: {task.exception()}')
            log.warning(f'Restarting task {name}')
            run = getattr(self, name)
            new_task = asyncio.create_task(run(), name=name)
            new_task.add_done_callback(self.task_exception_callback)
            self.running_tasks.add(new_task)
        self.running_tasks.remove(task)
