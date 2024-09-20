from typing import List

from fastapi import WebSocketDisconnect

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.connection_manager import ConnectionManager as BaseConnectionManager
from skynet.modules.stt.streaming_whisper.utils.utils import TranscriptionResponse

log = get_logger(__name__)


class ConnectionManager(BaseConnectionManager):
    async def process(self, session_id: str, buffer: bytes, timestamp: int, tag: str):
        log.debug(f'Processing chunk for session {session_id}')

        if session_id not in self.connections:
            log.warning(f'No such session id {session_id}, the connection was probably closed.')
            return

        results: List[TranscriptionResponse] = await self.connections[session_id].process(buffer, timestamp)

        if results is not None:
            for result in results:
                if result.type == 'final':
                    log.info(f'Participant {tag} result: {result.text}')
                    await self.send(session_id, result, timestamp, tag)

    async def send(self, session_id: str, result: TranscriptionResponse | None, timestamp: int, tag: str):
        if result is not None:
            try:
                await self.connections[session_id].ws.send_json(
                    {
                        'timestamp': timestamp,
                        'tag': tag,
                        'final': result.text,
                        'language': 'en',
                    }
                )
            except WebSocketDisconnect as e:
                log.warning(f'Session {session_id}: the connection was closed before sending all results: {e}')
                self.disconnect(session_id)
            except Exception as ex:
                log.error(f'Session {session_id}: exception while sending transcription results {ex}')
