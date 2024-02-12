from datetime import datetime, timezone
from typing import List, Tuple

import numpy as np
from numpy import ndarray
from pydantic import BaseModel

import skynet.modules.stt.streaming_whisper.cfg as cfg
from skynet.env import whisper_beam_size
from skynet.logs import get_logger

log = get_logger(__name__)


class WhisperWord(BaseModel):
    probability: float
    word: str
    start: float
    end: float


class WhisperSegment(BaseModel):
    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: List[int]
    temperature: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float
    words: List


class TranscriptionResponse(BaseModel):
    id: str
    participant_id: str
    ts: int
    text: str
    type: str
    variance: float


class WhisperResult:
    text: str
    segments: list[WhisperSegment]
    words: list[WhisperWord]
    confidence: float
    language: str

    def __init__(self, ts_result):
        self.text = ''.join([segment.text for segment in ts_result])
        self.segments = [WhisperSegment.model_validate(segment._asdict()) for segment in ts_result]
        self.words = [WhisperWord.model_validate(word._asdict()) for segment in ts_result for word in segment.words]
        self.confidence = self.get_confidence()

    def __str__(self):
        return (
            f'Text: {self.text}\n'
            + f'Confidence avg: {self.confidence}\n'
            + f'Segments: {self.segments}\n'
            + f'Words: {self.words}'
        )

    def get_confidence(self) -> float:
        if len(self.words) > 0:
            return float(sum(word.probability for word in self.words) / len(self.words))
        return 0.0


LANGUAGES = {
    "en": "english",
    "zh": "chinese",
    "de": "german",
    "es": "spanish",
    "ru": "russian",
    "ko": "korean",
    "fr": "french",
    "ja": "japanese",
    "pt": "portuguese",
    "tr": "turkish",
    "pl": "polish",
    "ca": "catalan",
    "nl": "dutch",
    "ar": "arabic",
    "sv": "swedish",
    "it": "italian",
    "id": "indonesian",
    "hi": "hindi",
    "fi": "finnish",
    "vi": "vietnamese",
    "he": "hebrew",
    "uk": "ukrainian",
    "el": "greek",
    "ms": "malay",
    "cs": "czech",
    "ro": "romanian",
    "da": "danish",
    "hu": "hungarian",
    "ta": "tamil",
    "no": "norwegian",
    "th": "thai",
    "ur": "urdu",
    "hr": "croatian",
    "bg": "bulgarian",
    "lt": "lithuanian",
    "la": "latin",
    "mi": "maori",
    "ml": "malayalam",
    "cy": "welsh",
    "sk": "slovak",
    "te": "telugu",
    "fa": "persian",
    "lv": "latvian",
    "bn": "bengali",
    "sr": "serbian",
    "az": "azerbaijani",
    "sl": "slovenian",
    "kn": "kannada",
    "et": "estonian",
    "mk": "macedonian",
    "br": "breton",
    "eu": "basque",
    "is": "icelandic",
    "hy": "armenian",
    "ne": "nepali",
    "mn": "mongolian",
    "bs": "bosnian",
    "kk": "kazakh",
    "sq": "albanian",
    "sw": "swahili",
    "gl": "galician",
    "mr": "marathi",
    "pa": "punjabi",
    "si": "sinhala",
    "km": "khmer",
    "sn": "shona",
    "yo": "yoruba",
    "so": "somali",
    "af": "afrikaans",
    "oc": "occitan",
    "ka": "georgian",
    "be": "belarusian",
    "tg": "tajik",
    "sd": "sindhi",
    "gu": "gujarati",
    "am": "amharic",
    "yi": "yiddish",
    "lo": "lao",
    "uz": "uzbek",
    "fo": "faroese",
    "ht": "haitian creole",
    "ps": "pashto",
    "tk": "turkmen",
    "nn": "nynorsk",
    "mt": "maltese",
    "sa": "sanskrit",
    "lb": "luxembourgish",
    "my": "myanmar",
    "bo": "tibetan",
    "tl": "tagalog",
    "mg": "malagasy",
    "as": "assamese",
    "tt": "tatar",
    "haw": "hawaiian",
    "ln": "lingala",
    "ha": "hausa",
    "ba": "bashkir",
    "jw": "javanese",
    "su": "sudanese",
}


def convert_bytes_to_seconds(byte_str: bytes) -> float:
    return round(len(byte_str) * cfg.one_byte_s, 3)


def convert_seconds_to_bytes(cut_mark: float) -> int:
    return int(cut_mark / cfg.one_byte_s)


def determine_chunk_duration(chunk: bytes) -> float:
    chunk_duration = round((len(chunk) * cfg.chunk_duration_s) / 8192, 3)
    log.debug(f'Chunk\'s length in bytes: {len(chunk)}')
    log.debug(f'Determined the chunk\'s duration to be {chunk_duration} seconds')
    return chunk_duration


def is_silent(audio: bytes) -> Tuple[bool, iter]:
    chunk_duration = determine_chunk_duration(audio)
    wav_header = get_wav_header([audio], chunk_duration_s=chunk_duration)
    stream = wav_header + b'' + audio
    audio = cfg.vad.read_audio(stream)
    st = cfg.vad.get_speech_timestamps(audio, model=cfg.vad_model, return_seconds=True)
    log.debug(f'Detected speech timestamps: {st}')
    silent = True if len(st) == 0 else False
    return silent, st


def find_biggest_gap_between_words(word_list: list[WhisperWord]) -> dict:
    prev_word = word_list[0]
    biggest_so_far = 0.0
    result = {'start': 0.0, 'end': 0.0}

    for word in word_list:
        diff = word.start - prev_word.end
        if diff > biggest_so_far:
            biggest_so_far = diff
            result = {'start': prev_word.end, 'end': word.start}
            log.debug(f'Biggest gap between words:\n{result}')
        prev_word = word
    return result


def get_last_silence_from_result(ts_result: WhisperResult, silence_threshold: float = 1.0) -> dict:
    result = {'start': 0.0, 'end': 0.0}
    last_word = {'start': 0.0, 'end': 0.0}
    # if the audio is longer than 10 seconds
    # force a final at the biggest gap between words found
    # instead of waiting for the silence_threshold
    if len(ts_result.words) > 0 and ts_result.words[-1].end >= 10:
        return find_biggest_gap_between_words(ts_result.words)
    # otherwise find a gap at least silence_threshold big
    for word in ts_result.words:
        if last_word['start'] > 0 and (word.start - last_word['end']) >= silence_threshold:
            result = {'start': last_word['end'], 'end': word.start}
        last_word = {'start': word.start, 'end': word.end}
    return result


def get_wav_header(chunks: List[bytes], chunk_duration_s: float = 0.256, sample_rate: int = 16000) -> bytes:
    duration = len(chunks) * chunk_duration_s
    samples = int(duration * sample_rate)
    bits_per_sample = 16
    channels = 1
    datasize = samples * channels * bits_per_sample // 8
    o = bytes("RIFF", 'ascii')  # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4, 'little')  # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE", 'ascii')  # (4byte) File type
    o += bytes("fmt ", 'ascii')  # (4byte) Format Chunk Marker
    o += (16).to_bytes(4, 'little')  # (4byte) Length of above format data
    o += (1).to_bytes(2, 'little')  # (2byte) Format type (1 - PCM)
    o += channels.to_bytes(2, 'little')  # (2byte)
    o += sample_rate.to_bytes(4, 'little')  # (4byte)
    o += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')  # (4byte)
    o += (channels * bits_per_sample // 8).to_bytes(2, 'little')  # (2byte)
    o += bits_per_sample.to_bytes(2, 'little')  # (2byte)
    o += bytes("data", 'ascii')  # (4byte) Data Chunk Marker
    o += datasize.to_bytes(4, 'little')  # (4byte) Data size in bytes
    return o


def load_audio(byte_array: bytes) -> ndarray:
    return np.frombuffer(byte_array, np.int16).flatten().astype(np.float32) / 32768.0


# returns now UTC timestamp since epoch in millis
def now() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def transcribe(buffer_list: List[bytes], lang: str = 'en') -> WhisperResult:
    audio_bytes = b''.join(buffer_list)
    audio = load_audio(audio_bytes)
    iterator, _ = cfg.model.transcribe(
        audio,
        language=lang,
        task='transcribe',
        word_timestamps=True,
        beam_size=whisper_beam_size,
        condition_on_previous_text=False,
    )
    res = list(iterator)
    ts_obj = WhisperResult(res)
    log.debug(f'Transcription results:\n{ts_obj}\n{res}')
    return ts_obj


def get_lang(lang: str, short=True) -> str:
    if len(lang) == 2 and short:
        return lang.lower().strip()
    if '-' in lang and short:
        return lang.split('-')[0].strip()
    if not short and '-' in lang:
        split_key = lang.split('-')[0]
        return LANGUAGES.get(split_key, 'english').lower().strip()
    return lang.lower().strip()
