from collections.abc import Iterator
from typing import List
from functools import reduce

from skynet.logs import get_logger
from skynet.modules.stt.assistant.chunk import Chunk
from skynet.modules.stt.assistant.fixie import oneshot as ultravox
from skynet.modules.stt.assistant.models import AssistantResponse
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class State:
    working_audio: bytes
    speech_duration: int

    def __init__(self):
        self.working_audio = b''
        self.speech_duration = 0;
        self.uuid = utils.Uuid7()

    def should_respond(self) -> bool:
        return self.speech_duration >= 1

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
            self.speech_duration = 0;
        else:
            self.working_audio += chunk.raw
            self.speech_duration += reduce((lambda x, y: x + (round(y.get('end') - y.get('start')))), chunk.speech_timestamps, 0)

    def reset(self):
        log.debug('flushing working audio')

        self.working_audio = b''
