from fastapi import WebSocketDisconnect

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.connection_manager import ConnectionManager as BaseConnectionManager
from skynet.modules.stt.streaming_whisper.utils.utils import TranscriptionResponse

log = get_logger(__name__)


class ConnectionManager(BaseConnectionManager):
    async def send(self, session_id: str, results: list[TranscriptionResponse] | None):
        if results is None:
            return

        final_results = [r for r in results if r.type == 'final']
        connections = [conn for conn in self.connections if conn.meeting_id == session_id]
        
        for connection in connections:
            for result in final_results:
                try:
                    await connection.ws.send_json(
                        {
                            'timestamp': result.ts,
                            'tag': result.participant_id,
                            'final': result.text,
                            'language': 'en',
                        }
                    )
                    log.debug(f'Participant {result.participant_id} result: {result.text}')
                except WebSocketDisconnect as e:
                    log.warning(f'Session {session_id}: the connection was closed before sending all results: {e}')
                    self.disconnect_connection(connection)
                except Exception as ex:
                    log.error(f'Session {session_id}: exception while sending transcription results {ex}')
