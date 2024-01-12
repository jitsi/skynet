import time

import websockets.exceptions
from fastapi import WebSocket
from loguru import logger as log

from asap import jwt_auth
from livets.MeetingConnection import MeetingConnection
from monitor.prometheus_metrics import CONNECTIONS_METRIC, TRANSCRIBE_DURATION_METRIC
from utils import utils


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, MeetingConnection] = {}

    async def connect(self, websocket: WebSocket, meeting_id: str, auth_token: str):
        if jwt_auth.authorize(auth_token):
            await websocket.accept()
            self.connections[meeting_id] = MeetingConnection(websocket)
            CONNECTIONS_METRIC.set(len(self.connections))
            log.info(f'Client {meeting_id} connected. Connection count {len(self.connections)}')
        else:
            await websocket.close(401, 'Bad JWT token')

    async def process(self, meeting_id: str, chunk: bytes):
        if meeting_id not in self.connections:
            log.warning(f'No such meeting id {meeting_id}, the connection was probably closed.')
            return
        start = time.perf_counter_ns()
        results = await self.connections[meeting_id].process(chunk)
        end = time.perf_counter_ns()
        processing_time = (end - start) / 1e6 / 1000
        TRANSCRIBE_DURATION_METRIC.observe(processing_time)
        if results is not None:
            for result in results:
                await self.send(meeting_id, result)

    async def send(self, meeting_id: str, result: utils.TranscriptionResponse):
        try:
            await self.connections[meeting_id].ws.send_json(result.model_dump())
        except websockets.exceptions.ConnectionClosed as e:
            log.warning(f'The connection was closed before sending all results: {e}')
            self.disconnect(meeting_id)
        except Exception as ex:
            log.error(f'Exception while sending transcription results {ex}')

    def disconnect(self, meeting_id: str):
        try:
            del self.connections[meeting_id]
        except KeyError:
            log.warning(f"The key {meeting_id} doesn't exist anymore.")
        CONNECTIONS_METRIC.set(len(self.connections))
