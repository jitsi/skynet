import json
import math
import os
import re
import secrets
import tempfile
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch
import torchaudio
from numpy import ndarray
from pydantic import BaseModel
from silero_vad import get_speech_timestamps, read_audio
from uuid6 import UUID

import skynet.modules.stt.streaming_whisper.cfg as cfg
from skynet.env import (
    whisper_beam_size, 
    whisper_min_probability,
    vad_threshold,
    vad_min_speech_duration,
    vad_min_silence_duration,
    vad_speech_pad,
    streaming_whisper_save_transcripts,
    streaming_whisper_output_dir,
    streaming_whisper_output_formats,
)
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
    audio: str
    type: str
    variance: float


class CutMark(BaseModel):
    start: float = 0.0
    end: float = 0.0
    probability: float = 0.0


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

# List of final transcriptions which should not be included in the initial prompt.
# This is to prevent the model from repeating the same text over and over or become
# biased towards a specific way of transcribing.
black_listed_prompts = ['. .']


def convert_bytes_to_seconds(byte_str: bytes) -> float:
    return round(len(byte_str) * cfg.one_byte_s, 3)


def convert_seconds_to_bytes(cut_mark: float) -> int:
    return int(cut_mark / cfg.one_byte_s)


def is_silent(audio: bytes) -> Tuple[bool, iter]:
    chunk_duration = convert_bytes_to_seconds(audio)
    wav_header = get_wav_header([audio], chunk_duration_s=chunk_duration)
    stream = wav_header + b'' + audio
    audio = read_audio(stream)
    
    # Enhanced VAD with configurable parameters
    st = get_speech_timestamps(
        audio, 
        model=cfg.vad_model, 
        return_seconds=True,
        threshold=vad_threshold,
        min_speech_duration_ms=int(vad_min_speech_duration * 1000),
        min_silence_duration_ms=int(vad_min_silence_duration * 1000),
        speech_pad_ms=int(vad_speech_pad * 1000)
    )
    
    log.debug(f'Enhanced VAD - Detected speech timestamps: {st}')
    log.debug(f'VAD Settings - Threshold: {vad_threshold}, Min Speech: {vad_min_speech_duration}s, Min Silence: {vad_min_silence_duration}s')
    
    silent = True if len(st) == 0 else False
    return silent, st


def is_speech_segment_valid(speech_timestamps: list, min_duration: float = 0.1) -> bool:
    """
    Check if speech segment meets minimum duration requirements
    """
    if not speech_timestamps:
        return False
    
    total_speech_duration = sum(
        segment['end'] - segment['start'] for segment in speech_timestamps
    )
    
    return total_speech_duration >= min_duration


def get_phrase_prob(last_word_idx: int, words: list[WhisperWord]) -> float:
    word_number = last_word_idx + 1
    return sum([word.probability for word in words[:word_number]]) / word_number


def find_biggest_gap_between_words(word_list: list[WhisperWord]) -> CutMark:
    prev_word = word_list[0]
    biggest_gap_so_far = 0.0
    result = CutMark()
    for i, word in enumerate(word_list):
        if i == 0:
            continue
        diff = word.start - prev_word.end
        probability = get_phrase_prob(i - 1, word_list)
        if diff > biggest_gap_so_far:
            biggest_gap_so_far = diff
            result = CutMark(start=prev_word.end, end=word.start, probability=probability)
            log.debug(f'Biggest gap between words:\n{result}')
        prev_word = word
    return result


def get_cut_mark_from_segment_probability(ts_result: WhisperResult) -> CutMark:
    check_len = len(ts_result.words) - 1
    phrase = ''
    if len(ts_result.words) > 1:
        # force a final at the biggest gap between words found if the audio is longer than 10 seconds
        if ts_result.words[-1].end >= 10:
            return find_biggest_gap_between_words(ts_result.words)
        for i, word in enumerate(ts_result.words):
            if i == check_len:
                break
            phrase += word.word
            avg_probability = get_phrase_prob(i, ts_result.words)
            if len(phrase) >= 48:
                if (
                    avg_probability >= whisper_min_probability
                    and word.word[-1] in ['.', '!', '?']
                    and word.end < ts_result.words[i + 1].start
                ):
                    log.debug(f'Found split at {word.word} ({word.end} - {ts_result.words[i+1].start})')
                    log.debug(f'Avg probability: {avg_probability}')
                    return CutMark(start=word.end, end=ts_result.words[i + 1].start, probability=avg_probability)
                else:
                    if ts_result.words[-1].end >= 15:
                        return find_biggest_gap_between_words(ts_result.words)
    return CutMark()


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


def transcribe(buffer_list: List[bytes], lang: str = 'en', previous_tokens=None) -> WhisperResult:
    if previous_tokens is None:
        previous_tokens = []
    audio_bytes = b''.join(buffer_list)
    audio = load_audio(audio_bytes)
    iterator, _ = cfg.model.transcribe(
        audio,
        language=lang,
        task='transcribe',
        word_timestamps=True,
        beam_size=whisper_beam_size,
        initial_prompt=previous_tokens,
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


class Uuid7:
    def __init__(self):
        self.last_v7_timestamp = None

    def get(self, time_arg_millis: int = None) -> UUID:
        nanoseconds = time.time_ns()
        timestamp_ms = nanoseconds // 10**6

        if time_arg_millis is not None:
            timestamp_ms = time_arg_millis

        if self.last_v7_timestamp is not None and timestamp_ms <= self.last_v7_timestamp:
            timestamp_ms = self.last_v7_timestamp + 1
        self.last_v7_timestamp = timestamp_ms
        uuid_int = (timestamp_ms & 0xFFFFFFFFFFFF) << 80
        uuid_int |= secrets.randbits(76)
        return UUID(int=uuid_int, version=7)


def get_jwt(ws_headers, ws_url_param=None) -> str:
    auth_header = ws_headers.get('authorization', None)
    if auth_header is not None:
        return auth_header.split(' ')[-1]
    return ws_url_param if ws_url_param is not None else ''


def save_transcript_to_file(meeting_id: str, transcript_response: 'TranscriptionResponse'):
    """
    Saves transcript to file based on meeting_id and configured formats.
    Creates folders by meeting name (room name).
    """
    if not streaming_whisper_save_transcripts:
        return
    
    try:
        # Create meeting-specific directory
        meeting_dir = Path(streaming_whisper_output_dir) / meeting_id
        meeting_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.fromtimestamp(transcript_response.ts / 1000.0, tz=timezone.utc)
        
        for format_type in streaming_whisper_output_formats:
            format_type = format_type.strip().lower()
            
            if format_type == 'jsonl':
                save_transcript_jsonl(meeting_dir, transcript_response, timestamp)
            elif format_type == 'srt':
                save_transcript_srt(meeting_dir, transcript_response, timestamp)
            else:
                log.warning(f'Unsupported transcript format: {format_type}')
                
    except Exception as e:
        log.error(f'Failed to save transcript for meeting {meeting_id}: {e}')


def save_transcript_jsonl(meeting_dir: Path, transcript_response: 'TranscriptionResponse', timestamp: datetime):
    """Save transcript in JSONL format"""
    jsonl_file = meeting_dir / f'{meeting_dir.name}.jsonl'
    
    transcript_data = {
        'id': transcript_response.id,
        'participant_id': transcript_response.participant_id,
        'timestamp': transcript_response.ts,
        'timestamp_iso': timestamp.isoformat(),
        'text': transcript_response.text,
        'type': transcript_response.type,
        'variance': transcript_response.variance
    }
    
    with open(jsonl_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(transcript_data, ensure_ascii=False) + '\n')
    
    log.debug(f'Saved transcript to JSONL: {jsonl_file}')


def save_transcript_srt(meeting_dir: Path, transcript_response: 'TranscriptionResponse', timestamp: datetime):
    """Save transcript in SRT format (only final transcriptions)"""
    if transcript_response.type != 'final':
        return
        
    srt_file = meeting_dir / f'{meeting_dir.name}.srt'
    
    # Read existing SRT to get the next subtitle number
    subtitle_number = 1
    if srt_file.exists():
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Count existing subtitles by counting subtitle numbers
                subtitle_numbers = re.findall(r'^(\d+)$', content, re.MULTILINE)
                if subtitle_numbers:
                    subtitle_number = max(int(num) for num in subtitle_numbers) + 1
        except Exception as e:
            log.warning(f'Failed to read existing SRT file: {e}')
    
    # Estimate duration (you may want to adjust this based on your needs)
    estimated_duration_ms = len(transcript_response.text.split()) * 500  # ~500ms per word
    start_time_ms = transcript_response.ts
    end_time_ms = start_time_ms + estimated_duration_ms
    
    def format_srt_timestamp(timestamp_ms):
        """Convert milliseconds to SRT timestamp format (HH:MM:SS,mmm)"""
        total_seconds = timestamp_ms / 1000.0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}'
    
    start_timestamp = format_srt_timestamp(start_time_ms)
    end_timestamp = format_srt_timestamp(end_time_ms)
    
    subtitle_entry = f'\n{subtitle_number}\n{start_timestamp} --> {end_timestamp}\n{transcript_response.text}\n'
    
    with open(srt_file, 'a', encoding='utf-8') as f:
        f.write(subtitle_entry)
    
    log.debug(f'Saved transcript to SRT: {srt_file}')
