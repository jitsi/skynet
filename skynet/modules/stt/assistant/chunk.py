from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class Chunk:
    raw: bytes
    timestamp: int
    duration: float
    size: int
    silent: bool
    speech_timestamps: iter

    def __init__(self, chunk: bytes, chunk_timestamp: int):
        self.raw = chunk
        self.timestamp = chunk_timestamp
        self.duration = utils.convert_bytes_to_seconds(self.raw)
        self.size = len(self.raw)
        self.silent, self.speech_timestamps = utils.is_silent(self.raw)
