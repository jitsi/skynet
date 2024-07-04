from collections.abc import Iterator
from typing import List

from skynet.logs import get_logger
from skynet.modules.stt.assistant.chunk import Chunk
from skynet.modules.stt.assistant.fixie import oneshot as ultravox
from skynet.modules.stt.assistant.models import AssistantResponse
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class State:
    working_audio: bytes
    silence: bool

    def __init__(self):
        self.working_audio = b''
        self.silence = True
        self.uuid = utils.Uuid7()

    def should_respond(self) -> bool:
        working_audio_duration = utils.convert_bytes_to_seconds(self.working_audio)

        if working_audio_duration >= 1 and self.silence:
            return True

        return False

    def process(self, chunk: Chunk) -> Iterator[AssistantResponse] | None:
        self.add_to_store(chunk)

        if self.should_respond():
            final_audio_length = utils.convert_bytes_to_seconds(self.working_audio)
            final_audio = utils.get_wav_header([self.working_audio], final_audio_length) + self.working_audio

            for text in ultravox(final_audio):
                yield AssistantResponse(text=text, ts=utils.now())

            self.reset()
        else:
            return None

    def add_to_store(self, chunk: Chunk):
        if chunk.silent:
            self.silence = True
        else:
            self.working_audio += chunk.raw
            self.silence = False

    def reset(self):
        log.debug('flushing working audio')

        self.working_audio = b''
