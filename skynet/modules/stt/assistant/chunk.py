from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class Chunk:
    raw: bytes
    silent: bool
    speech_duration: float

    def __init__(self, chunk: bytes):
        self.raw = chunk
        self.silent, speech_timestamps = utils.is_silent(self.raw)
        self.speech_duration = sum([round(y.get('end') - y.get('start'), 1) for y in speech_timestamps])
