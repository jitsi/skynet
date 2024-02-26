from typing import List

from starlette.websockets import WebSocket

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.chunk import Chunk
from skynet.modules.stt.streaming_whisper.state import State
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class MeetingConnection:
    participants: dict[str, State] = {}

    def __init__(self, ws: WebSocket):
        self.participants = {}
        self.ws = ws

    async def process(self, chunk: bytes, chunk_timestamp: int) -> List[utils.TranscriptionResponse] | None:
        a_chunk = Chunk(chunk, chunk_timestamp)
        if a_chunk.participant_id not in self.participants:
            log.debug(
                f'The participant {a_chunk.participant_id} is not in the participants list, creating a new state.'
            )
            self.participants[a_chunk.participant_id] = State(a_chunk.participant_id, a_chunk.language)
        payloads = await self.participants[a_chunk.participant_id].process(a_chunk)
        return payloads
