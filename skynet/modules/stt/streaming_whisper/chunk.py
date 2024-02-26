from skynet.modules.stt.streaming_whisper.utils import utils
from skynet.logs import get_logger

log = get_logger(__name__)


class Chunk:
    raw: bytes
    timestamp: int
    duration: float
    size: int
    silent: bool
    speech_timestamps: iter
    participant_id: str
    language: str

    def __init__(self, chunk: bytes, chunk_timestamp: int):
        self._extract(chunk)
        self.timestamp = chunk_timestamp
        self.duration = utils.convert_bytes_to_seconds(self.raw)
        self.size = len(self.raw)
        self.silent, self.speech_timestamps = utils.is_silent(self.raw)

    def _extract(self, chunk: bytes):
        header = chunk[0:60].decode('utf-8').strip('\x00')
        log.debug(f'Chunk header {header}')
        self.raw = chunk[60:]
        header_arr = header.split('|')
        self.participant_id = header_arr[0]
        self.language = utils.get_lang(header_arr[1])
