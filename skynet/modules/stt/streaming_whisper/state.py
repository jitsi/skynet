import asyncio
import base64
import time
from typing import List

from skynet.env import whisper_return_transcribed_audio as return_audio

from skynet.logs import get_logger
from skynet.modules.monitoring import TRANSCRIBE_DURATION_METRIC
from skynet.modules.stt.streaming_whisper.chunk import Chunk
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class State:
    working_audio: bytes
    silent_chunks: int
    transcription_id: str
    long_silence: bool
    chunk_count: int
    working_audio_starts_at: int
    chunk_duration: float
    last_received_chunk: int

    def __init__(
        self,
        participant_id: str,
        lang: str = 'en',
        # number of silent chunks which can be appended
        # before starting to drop them
        add_max_silent_chunks: int = 1,
        final_after_x_silent_chunks: int = 2,
    ):
        self.working_audio_starts_at = 0
        self.participant_id = participant_id
        self.silent_chunks = 0
        self.chunk_count = 0
        self.working_audio = b''
        self.lang = lang
        self.long_silence = False
        self.chunk_duration = 0.0
        # silence count before starting to drop incoming silent chunks
        self.silence_count_before_ignore = add_max_silent_chunks
        self.final_after_x_silent_chunks = final_after_x_silent_chunks
        self.uuid = utils.Uuid7()
        self.transcription_id = str(self.uuid.get())
        self.last_received_chunk = utils.now()
        self.is_transcribing = False

    def _extract_transcriptions(
        self, last_pause: utils.CutMark, ts_result: utils.WhisperResult
    ) -> List[utils.TranscriptionResponse]:
        if ts_result is None:
            return []
        results = []
        final = ''
        interim = ''
        final_starts_at = None
        interim_starts_at = None
        for word in ts_result.words:
            space = ' ' if ' ' not in word.word else ''
            # search for final up to silence
            if word.end < last_pause.end:
                final_starts_at = word.start if final_starts_at is None else final_starts_at
                final += word.word + space
                log.debug(f'Participant {self.participant_id}: final is "{final}"')
            # consider everything else as interim
            else:
                interim_starts_at = word.start if interim_starts_at is None else interim_starts_at
                interim += word.word + space
                log.debug(f'Participant {self.participant_id}: interim is "{interim}"')

        if final.strip():
            cut_mark_bytes = self.get_num_bytes_for_slicing(last_pause.end)
            if cut_mark_bytes > 0:
                log.debug(f'Participant {self.participant_id}: cut mark set at {cut_mark_bytes} bytes')
                final_start_timestamp = self.working_audio_starts_at + int(final_starts_at * 1000)
                final_audio = None
                final_raw_audio = self.trim_working_audio(cut_mark_bytes)
                if return_audio:
                    final_audio_length = utils.convert_bytes_to_seconds(final_raw_audio)
                    final_audio = utils.get_wav_header([final_raw_audio], final_audio_length) + final_raw_audio
                results.append(
                    self.get_response_payload(
                        final, final_start_timestamp, final_audio, True, probability=last_pause.probability
                    )
                )
                # advance the start timestamp of the working audio to the start of the interim
                if self.working_audio_starts_at:
                    self.working_audio_starts_at += int(last_pause.end * 1000)
            else:
                # return everything as interim if failed to slice and acquire cut mark
                results.append(
                    self.get_response_payload(
                        final + interim, self.working_audio_starts_at + int(ts_result.words[0].start * 1000)
                    )
                )
                return results
        if interim.strip() != '':
            results.append(
                self.get_response_payload(interim, self.working_audio_starts_at + int(interim_starts_at * 1000))
            )
        return results

    def should_transcribe(self) -> bool:
        # prevents hallucinations at the start of the audio
        if self.silent_chunks == self.chunk_count:
            return False
        working_audio_duration = utils.convert_bytes_to_seconds(self.working_audio)
        if working_audio_duration >= 1 and not self.long_silence:
            return True
        return False

    async def force_transcription(self, previous_tokens) -> List[utils.TranscriptionResponse] | None:
        results = None
        if self.is_transcribing:
            return results
        ts_result = await self.do_transcription(self.working_audio, previous_tokens)
        if ts_result.text.strip():
            results = []
            start_timestamp = int(ts_result.words[0].start * 1000) + self.working_audio_starts_at
            final_audio = None
            if return_audio:
                final_audio_length = utils.convert_bytes_to_seconds(self.working_audio)
                final_audio = utils.get_wav_header([self.working_audio], final_audio_length) + self.working_audio
            results.append(
                self.get_response_payload(
                    ts_result.text,
                    start_timestamp,
                    final_audio,
                    True,
                    probability=utils.get_phrase_prob(len(ts_result.words) - 1, ts_result.words),
                )
            )
        self.reset()
        return results

    async def process(self, chunk: Chunk, previous_tokens: list[int]) -> List[utils.TranscriptionResponse] | None:
        self.last_received_chunk = self.last_received_chunk if chunk.silent else utils.now()
        self.chunk_count += 1
        if self.chunk_duration == 0:
            self.chunk_duration = chunk.duration
        log.debug(
            f'Participant {self.participant_id}: chunk length {chunk.size} bytes, '
            f'duration {chunk.duration}s, '
            f'total chunks {self.chunk_count}.'
        )
        self.add_to_store(chunk)

        if self.should_transcribe() and not self.is_transcribing:
            ts_result = await self.do_transcription(self.working_audio, previous_tokens)
            last_pause = utils.get_cut_mark_from_segment_probability(ts_result)
            results = self._extract_transcriptions(last_pause, ts_result)
            if len(results) > 0:
                return results
        log.debug(f'Participant {self.participant_id}: no ts results')
        return None

    def add_to_store(self, chunk: Chunk):
        if not chunk.silent or (chunk.silent and self.silent_chunks < self.silence_count_before_ignore):
            self.working_audio += chunk.raw
            log.debug(
                f'Participant {self.participant_id}: the audio buffer is '
                + f'{utils.convert_bytes_to_seconds(self.working_audio)}s long'
            )
        if chunk.silent:
            log.debug(f'Participant {self.participant_id}: the chunk is silent.')
            self.silent_chunks += 1
            if self.silent_chunks > self.final_after_x_silent_chunks:
                self.long_silence = True
        else:
            if self.working_audio_starts_at == 0:
                self.working_audio_starts_at = chunk.timestamp - int(chunk.duration * 1000)
            self.long_silence = False
            self.silent_chunks = 0

    def trim_working_audio(self, bytes_to_cut: int) -> bytes:
        log.debug(
            f'Participant {self.participant_id}: '
            + f'trimming the audio buffer, current length is {len(self.working_audio)} bytes.'
        )
        dropped_chunk = self.working_audio[:bytes_to_cut]
        self.working_audio = self.working_audio[bytes_to_cut:]
        if len(self.working_audio) == 0:
            self.working_audio_starts_at = 0
        log.debug(
            f'Participant {self.participant_id}: '
            + f'the audio buffer after cut is now {len(self.working_audio)} bytes'
        )
        return dropped_chunk

    def get_response_payload(
        self, transcription: str, start_timestamp: int, final_audio: bytes | None = None, final: bool = False, **kwargs
    ) -> utils.TranscriptionResponse:
        prob = kwargs.get('probability', 0.5)
        if not self.transcription_id:
            self.transcription_id = str(self.uuid.get(start_timestamp))
        ts_id = self.transcription_id
        if final:
            self.transcription_id = ''
        return utils.TranscriptionResponse(
            id=ts_id,
            participant_id=self.participant_id,
            ts=start_timestamp,
            text=transcription,
            audio=base64.b64encode(final_audio).decode('ASCII') if final_audio else '',
            type='final' if final else 'interim',
            variance=prob,
        )

    def reset(self):
        """
        Empties the working audio buffer
        """
        log.debug(f'Participant {self.participant_id}: flushing working audio')
        self.working_audio_starts_at = 0
        self.working_audio = b''

    @staticmethod
    def get_num_bytes_for_slicing(cut_mark: float) -> int:
        byte_threshold = utils.convert_seconds_to_bytes(cut_mark)
        # the resulting value needs to be a multiple of 2048
        sliceable_bytes_multiplier, _ = divmod(byte_threshold, 2048)
        sliceable_bytes = sliceable_bytes_multiplier * 2048
        log.debug(f'Sliceable bytes: {sliceable_bytes}')
        return sliceable_bytes

    async def do_transcription(self, audio: bytes, previous_tokens: list[int]) -> utils.WhisperResult | None:
        self.is_transcribing = True
        start = time.perf_counter_ns()
        loop = asyncio.get_running_loop()
        log.debug(f'Participant {self.participant_id}: starting transcription of {len(audio)} bytes.')
        try:
            ts_result = await loop.run_in_executor(None, utils.transcribe, [audio], self.lang, previous_tokens)
        except RuntimeError as e:
            log.error(f'Participant {self.participant_id}: failed to transcribe {e}')
            self.is_transcribing = False
            return None
        end = time.perf_counter_ns()
        processing_time = (end - start) / 1e6 / 1000
        TRANSCRIBE_DURATION_METRIC.observe(processing_time)
        log.debug(ts_result)
        self.is_transcribing = False
        return ts_result
