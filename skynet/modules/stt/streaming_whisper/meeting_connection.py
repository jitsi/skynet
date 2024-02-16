from typing import List

from starlette.websockets import WebSocket

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.state import State
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class MeetingConnection:
    participants: dict[str, State] = {}

    def __init__(self, ws: WebSocket):
        self.participants = {}
        self.ws = ws

    @staticmethod
    def _extract_from_chunk(chunk: bytes):
        header = chunk[0:60].decode('utf-8').strip('\x00')
        log.debug(f'Chunk header {header}')
        audio = chunk[60:]
        header_arr = header.split('|')
        participant_id = header_arr[0]
        received_language = header_arr[1]
        log.debug(f'Received language is {received_language}')
        whisper_language = utils.get_lang(received_language)
        log.debug(f'Determined whisper language to be {whisper_language}')
        return participant_id, whisper_language, audio

    async def process(self, chunk: bytes) -> List[utils.TranscriptionResponse] | None:
        participant_id, lang, audio_chunk = self._extract_from_chunk(chunk)
        log.debug(f'Extracted from chunk: participant={participant_id}, language={lang}, len_chunk={len(audio_chunk)}')
        if participant_id not in self.participants:
            log.debug(f'The participant {participant_id} is not in the participants list, creating a new state.')
            self.participants[participant_id] = State(participant_id, lang)
        payloads = await self.participants[participant_id].process(audio_chunk)
        return payloads
