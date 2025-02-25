from fastapi import WebSocketDisconnect

from skynet.logs import get_logger
from skynet.modules.stt.shared.models.transcription_response import TranscriptionResponse
from skynet.modules.stt.streaming_whisper.connection_manager import ConnectionManager as BaseConnectionManager

log = get_logger(__name__)


class ConnectionManager(BaseConnectionManager):
    async def send(self, session_id: str, results: list[TranscriptionResponse] | None):
        if results is None:
            return

        final_results = [r for r in results if r.type == 'final']
        for result in final_results:
            try:
                await self.connections[session_id].ws.send_json(
                    {
                        'timestamp': result.ts,
                        'tag': result.participant_id,
                        'final': result.text,
                        'language': 'en',
                    }
                )
                log.info(f'Participant {result.participant_id} result: {result.text}')
            except WebSocketDisconnect as e:
                log.warning(f'Session {session_id}: the connection was closed before sending all results: {e}')
                self.disconnect(session_id)
            except Exception as ex:
                log.error(f'Session {session_id}: exception while sending transcription results {ex}')
