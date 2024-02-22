import asyncio
from asyncio import Queue

from fastapi import WebSocket, WebSocketDisconnect

from skynet.auth.jwt import authorize
from skynet.env import bypass_auth
from skynet.logs import get_logger
from skynet.modules.monitoring import CONNECTIONS_METRIC
from skynet.modules.stt.streaming_whisper.meeting_connection import MeetingConnection
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class ConnectionManager:
    connections: dict[str, MeetingConnection]
    processing_queues: dict[str, Queue[tuple[bytes, int]]]
    result_queues: dict[str, Queue[[list[utils.TranscriptionResponse]]]]

    def __init__(self):
        self.connections = {}
        self.processing_queues = {}
        self.result_queues = {}

    async def connect(self, websocket: WebSocket, meeting_id: str, auth_token: str | None):
        if not bypass_auth:
            authorized = await authorize(auth_token)
            if not authorized:
                await websocket.close(401, 'Bad JWT token')
                return
        await websocket.accept()

        self.connections[meeting_id] = MeetingConnection(websocket)
        self.processing_queues[meeting_id] = Queue()
        self.result_queues[meeting_id] = Queue()

        loop = asyncio.get_running_loop()
        loop.create_task(self.process_worker(meeting_id))
        loop.create_task(self.response_worker(meeting_id))

        CONNECTIONS_METRIC.set(len(self.connections))
        log.info(f'Meeting with id {meeting_id} started. Ongoing meetings {len(self.connections)}')

    async def process(self, meeting_id: str, chunk: bytes, chunk_timestamp: int):
        log.debug(f'Processing chunk for meeting {meeting_id}')
        if meeting_id not in self.connections:
            log.warning(f'No such meeting id {meeting_id}, the connection was probably closed.')
            return
        await self.processing_queues[meeting_id].put((chunk, chunk_timestamp))

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
            del self.processing_queues[meeting_id]
            del self.result_queues[meeting_id]
        except KeyError:
            log.warning(f'The meeting {meeting_id} doesn\'t exist anymore.')
        CONNECTIONS_METRIC.set(len(self.connections))

    async def process_worker(self, meeting_id):
        process_q = self.processing_queues[meeting_id]
        result_q = self.result_queues[meeting_id]
        while True:
            chunk, chunk_timestamp = await process_q.get()
            results = await self.connections[meeting_id].process(chunk, chunk_timestamp)
            await result_q.put(results)
            process_q.task_done()

    async def response_worker(self, meeting_id):
        while True:
            results = await self.result_queues[meeting_id].get()
            if results is not None:
                for result in results:
                    await self.send(meeting_id, result)
            self.result_queues[meeting_id].task_done()
