from itertools import chain
from typing import List

from faster_whisper.tokenizer import Tokenizer

from starlette.websockets import WebSocket

from skynet.env import whisper_max_finals_in_initial_prompt as max_finals

from skynet.logs import get_logger
from skynet.modules.stt.shared.models.transcription_response import TranscriptionResponse
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
    recording: bool

    def __init__(self, ws: WebSocket, is_recording: bool = False):
        self.participants = {}
        self.ws = ws
        self.previous_transcription_tokens = []
        self.previous_transcription_store = []
        self.meeting_language = None
        self.tokenizer = None
        self.recording = is_recording

    async def update_initial_prompt(self, previous_payloads: list[TranscriptionResponse]):
        for payload in previous_payloads:
            if payload.type == 'final' and not any(prompt in payload.text for prompt in utils.black_listed_prompts):
                self.previous_transcription_store.append(self.tokenizer.encode(f' {payload.text.strip()}'))
                if len(self.previous_transcription_tokens) > max_finals:
                    self.previous_transcription_store.pop(0)
                # flatten the list of lists
                self.previous_transcription_tokens = list(chain.from_iterable(self.previous_transcription_store))

    async def process(self, chunk: bytes, chunk_timestamp: int) -> List[TranscriptionResponse] | None:
        a_chunk = Chunk(chunk, chunk_timestamp)
        participant_id = a_chunk.participant_id

        # The first chunk sets the meeting language and initializes the Tokenizer
        if not self.meeting_language:
            self.meeting_language = a_chunk.language
            self.tokenizer = Tokenizer(
                model.hf_tokenizer, multilingual=False, task='transcribe', language=self.meeting_language
            )

        if participant_id not in self.participants:
            log.debug(f'The participant {participant_id} is not in the participants list, creating a new state.')
            self.participants[participant_id] = State(participant_id, a_chunk.language)

        if self.recording:
            await self.participants[participant_id].process_recording(a_chunk)
            return None

        payloads = await self.participants[participant_id].process(a_chunk, self.previous_transcription_tokens)
        if payloads:
            await self.update_initial_prompt(payloads)
        return payloads

    async def force_transcription(self, participant_id: str):
        if participant_id in self.participants:
            payloads = await self.participants[participant_id].force_transcription(self.previous_transcription_tokens)
            if payloads:
                await self.update_initial_prompt(payloads)
            return payloads
        return None
