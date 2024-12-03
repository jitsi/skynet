from itertools import chain
from typing import List

from faster_whisper.tokenizer import Tokenizer

from starlette.websockets import WebSocket

from skynet.env import whisper_max_finals_in_initial_prompt as max_finals

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.cfg import model
from skynet.modules.stt.streaming_whisper.chunk import Chunk
from skynet.modules.stt.streaming_whisper.state import State
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class MeetingConnection:
    participants: dict[str, State] = {}
    previous_transcription_tokens: List[int]
    previous_transcription_store: List[List[int]]
    tokenizer: Tokenizer | None
    meeting_language: str | None

    def __init__(self, ws: WebSocket):
        self.participants = {}
        self.ws = ws
        self.previous_transcription_tokens = []
        self.previous_transcription_store = []
        self.meeting_language = None
        self.tokenizer = None

    async def update_initial_prompt(self, new_transcription: str):
        self.previous_transcription_store.append(self.tokenizer.encode(f' {new_transcription.strip()}'))
        if len(self.previous_transcription_tokens) > max_finals:
            self.previous_transcription_store.pop(0)
        # flatten the list of lists
        self.previous_transcription_tokens = list(chain.from_iterable(self.previous_transcription_store))

    async def process(self, chunk: bytes, chunk_timestamp: int) -> List[utils.TranscriptionResponse] | None:
        a_chunk = Chunk(chunk, chunk_timestamp)

        # The first chunk sets the meeting language and initializes the Tokenizer
        if not self.meeting_language:
            self.meeting_language = a_chunk.language
            self.tokenizer = Tokenizer(
                model.hf_tokenizer, multilingual=False, task='transcribe', language=self.meeting_language
            )

        if a_chunk.participant_id not in self.participants:
            log.debug(
                f'The participant {a_chunk.participant_id} is not in the participants list, creating a new state.'
            )
            self.participants[a_chunk.participant_id] = State(a_chunk.participant_id, a_chunk.language)

        payloads = await self.participants[a_chunk.participant_id].process(a_chunk, self.previous_transcription_tokens)
        if payloads:
            for payload in payloads:
                if payload.type == 'final':
                    await self.update_initial_prompt(payload.text)
        return payloads
