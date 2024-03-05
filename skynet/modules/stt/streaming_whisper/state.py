import asyncio
import base64
from typing import List

from skynet.env import whisper_return_transcribed_audio as return_audio

from skynet.logs import get_logger
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

    def __init__(
        self,
        participant_id: str,
        lang: str = 'en',
        # number of silent chunks which can be appended
        # before starting to drop them
        add_max_silent_chunks: int = 1,
        final_after_x_silent_chunks: int = 2,
        force_final_duration_threshold: int = 15,
        perform_final_after_silent_seconds: float = 0.8,
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
        self.force_final_duration_threshold = force_final_duration_threshold
        self.perform_final_after_silent_seconds = perform_final_after_silent_seconds
        self.uuid = utils.Uuid7()
        self.transcription_id = str(self.uuid.get())

    def _extract_transcriptions(
        self, last_pause: dict, ts_result: utils.WhisperResult
    ) -> List[utils.TranscriptionResponse]:
        if ts_result is None:
            return []
        results = []
        final = ''
        interim = ''
        # return a final and flush the working audio if too many silent chunks
        # or if the working audio is over the max duration threshold
        if (
            self.silent_chunks >= self.final_after_x_silent_chunks
            or utils.convert_bytes_to_seconds(self.working_audio) > self.force_final_duration_threshold
        ):
            if ts_result.text.strip() != '':
                start_timestamp = int(ts_result.words[0].start * 1000) + self.working_audio_starts_at
                final_audio = None
                if return_audio:
                    final_audio_length = utils.convert_bytes_to_seconds(self.working_audio)
                    final_audio = utils.get_wav_header([self.working_audio], final_audio_length) + self.working_audio
                results.append(self.get_response_payload(ts_result.text, start_timestamp, final_audio, True))
                self.reset()
                return results
        if self.silent_chunks > self.final_after_x_silent_chunks:
            self.long_silence = True

        final_starts_at = None
        interim_starts_at = None
        for word in ts_result.words:
            space = ' ' if ' ' not in word.word else ''
            # search for final up to silence
            if word.end <= last_pause['end']:
                final_starts_at = word.start if final_starts_at is None else final_starts_at
                final += word.word + space
                log.debug(f'Participant {self.participant_id}: final is "{final}"')
            # consider everything else as interim
            else:
                interim_starts_at = word.start if interim_starts_at is None else interim_starts_at
                interim += word.word + space
                log.debug(f'Participant {self.participant_id}: interim is "{interim}"')

        if final.strip():
            cut_mark = self.get_num_bytes_for_slicing(last_pause['end'])
            if cut_mark > 0:
                log.debug(f'Participant {self.participant_id}: cut mark set at {cut_mark} bytes')
                final_start_timestamp = self.working_audio_starts_at + int(final_starts_at * 1000)
                final_audio = None
                final_raw_audio = self.trim_working_audio(cut_mark)
                if return_audio:
                    final_audio_length = utils.convert_bytes_to_seconds(final_raw_audio)
                    final_audio = utils.get_wav_header([final_raw_audio], final_audio_length) + final_raw_audio
                results.append(self.get_response_payload(final, final_start_timestamp, final_audio, True))
                # advance the start timestamp of the working audio to the start of the interim,
                self.working_audio_starts_at += int(last_pause['end'] * 1000)
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

    async def process(self, chunk: Chunk) -> List[utils.TranscriptionResponse] | None:
        self.chunk_count += 1
        if self.chunk_duration == 0:
            self.chunk_duration = chunk.duration
        log.debug(
            f'Participant {self.participant_id}: chunk length {chunk.size} bytes, '
            f'duration {chunk.duration}s, '
            f'total chunks {self.chunk_count}.'
        )
        self.add_to_store(chunk)
        if self.should_transcribe():
            ts_result = await self.do_transcription(self.working_audio)
            last_pause = utils.get_last_silence_from_result(ts_result, self.perform_final_after_silent_seconds)
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
        log.debug(
            f'Participant {self.participant_id}: '
            + f'the audio buffer after cut is now {len(self.working_audio)} bytes'
        )
        return dropped_chunk

    def get_response_payload(
        self, transcription: str, start_timestamp: int, final_audio: bytes | None = None, final: bool = False
    ) -> utils.TranscriptionResponse:
        if final:
            self.transcription_id = str(self.uuid.get(start_timestamp))
        return utils.TranscriptionResponse(
            id=self.transcription_id,
            participant_id=self.participant_id,
            ts=start_timestamp,
            text=transcription,
            audio=base64.b64encode(final_audio).decode('ASCII') if final_audio else '',
            type='final' if final else 'interim',
            variance=1.0 if final else 0.5,
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
        sliceable_bytes = 0
        while sliceable_bytes < byte_threshold:
            # the resulting value needs to be a multiple of 2048
            sliceable_bytes += 2048
        return sliceable_bytes

    async def do_transcription(self, audio: bytes) -> utils.WhisperResult | None:
        loop = asyncio.get_running_loop()
        log.debug(f'Participant {self.participant_id}: starting transcription of {len(audio)} bytes.')
        try:
            ts_result = await loop.run_in_executor(None, utils.transcribe, [audio], self.lang)
        except RuntimeError as e:
            log.error(f'Participant {self.participant_id}: failed to transcribe {e}')
            return None
        log.debug(ts_result)
        return ts_result
