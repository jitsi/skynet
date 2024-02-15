import asyncio
from typing import List

import uuid6

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.utils import utils

log = get_logger(__name__)


class State:
    working_audio: bytes = b''
    silent_chunks = 0
    transcription_id = str(uuid6.uuid7())
    transcription_ts = utils.now()
    all_final = ''
    long_silence = False
    received_last_chunk = utils.now()
    chunk_count = 0

    def __init__(
        self,
        participant_id: str,
        lang: str = 'en',
        # number of silent chunks which can be appended
        # before starting to drop them
        add_max_silent_chunks: int = 1,
        final_after_x_silent_chunks: int = 2,
        force_final_duration_threshold: int = 29,
        perform_final_after_silent_seconds: float = 0.8,
    ):
        self.participant_id = participant_id
        self.lang = lang
        # silence count before starting to drop incoming silent chunks
        self.silence_count_before_ignore = add_max_silent_chunks
        self.final_after_x_silent_chunks = final_after_x_silent_chunks
        self.force_final_duration_threshold = force_final_duration_threshold
        self.perform_final_after_silent_seconds = perform_final_after_silent_seconds

    def _extract_transcriptions(
        self, last_pause: dict, ts_result: utils.WhisperResult
    ) -> List[utils.TranscriptionResponse]:
        if ts_result is None:
            return []
        results = []
        final = ''
        interim = ''
        # return a final and flush the working audio if too many silent chunks
        # or if the buffer is over the max length threshold
        if (
            self.silent_chunks >= self.final_after_x_silent_chunks
            or utils.convert_bytes_to_seconds(self.working_audio) > self.force_final_duration_threshold
        ):
            if ts_result.text.strip() != '':
                results.append(self.get_response_payload(ts_result.text, True))
                self.all_final += ts_result.text
                self.reset(True)
                return results
        if self.silent_chunks > self.final_after_x_silent_chunks:
            self.long_silence = True
        for word in ts_result.words:
            space = ' ' if ' ' not in word.word else ''
            # search for final up to silence
            if word.end <= last_pause['end']:
                final += word.word + space
                log.debug(f'Participant {self.participant_id}: final is "{final}"')
            # consider everything else as interim
            else:
                interim += word.word + space
                log.debug(f'Participant {self.participant_id}: interim is "{interim}"')

        if final.strip():
            cut_mark = self.get_num_bytes_for_slicing(last_pause['end'])
            if cut_mark > 0:
                log.debug(f'Participant {self.participant_id}: cut mark set at {cut_mark} bytes')
                results.append(self.get_response_payload(final, True))
                self.all_final += final
                self.trim_working_audio(cut_mark)
                # add 1 second of silence to the start of the working audio
                self.working_audio = (b'\x00' * 32768) + self.working_audio
                self.reset()
            else:
                results.append(self.get_response_payload(final + interim))
                return results
        if interim.strip() != '':
            results.append(self.get_response_payload(interim))
        return results

    def should_transcribe(self, working_audio_duration: float) -> bool:
        # prevents hallucinations at the start of the audio
        if self.silent_chunks == self.chunk_count:
            return False
        if working_audio_duration >= 1 and not self.long_silence:
            return True
        return False

    async def process(self, chunk: bytes) -> List[utils.TranscriptionResponse] | None:
        self.chunk_count += 1
        log.debug(f'Participant {self.participant_id}: received chunks {self.chunk_count}')
        self.received_last_chunk = utils.now()
        self.add_to_store(chunk)
        working_audio_duration = utils.convert_bytes_to_seconds(self.working_audio)
        if self.should_transcribe(working_audio_duration):
            ts_result = await self.do_transcription(self.working_audio)
            last_pause = utils.get_last_silence_from_result(ts_result, self.perform_final_after_silent_seconds)
            results = self._extract_transcriptions(last_pause, ts_result)
            if len(results) > 0:
                return results
        log.debug(f'Participant {self.participant_id}: no ts results')
        return None

    def add_to_store(self, chunk: bytes):
        is_silent, _ = utils.is_silent(chunk)
        if not is_silent or (is_silent and self.silent_chunks < self.silence_count_before_ignore):
            self.working_audio += chunk
            log.debug(
                f'Participant {self.participant_id}: the audio buffer is '
                + f'{utils.convert_bytes_to_seconds(self.working_audio)}s long'
            )
        if is_silent:
            log.debug(f'Participant {self.participant_id}: the chunk is silent.')
            self.silent_chunks += 1
        else:
            self.long_silence = False
            self.silent_chunks = 0

    def trim_working_audio(self, bytes_to_cut: int):
        log.debug(
            f'Participant {self.participant_id}: '
            + f'trimming the audio buffer, current length is {len(self.working_audio)} bytes.'
        )
        self.working_audio = bytearray(self.get_num_bytes_for_slicing(1.0)) + self.working_audio[bytes_to_cut:]
        log.debug(
            f'Participant {self.participant_id}: '
            + f'the audio buffer after cut is now {len(self.working_audio)} bytes'
        )

    def get_response_payload(self, transcription: str, final: bool = False) -> utils.TranscriptionResponse:
        return utils.TranscriptionResponse(
            id=self.transcription_id,
            participant_id=self.participant_id,
            ts=self.transcription_ts if final else utils.now(),
            text=transcription,
            type='final' if final else 'interim',
            variance=1.0 if final else 0.5,
        )

    def reset(self, flush_working_audio: bool = False):
        self.transcription_id = str(uuid6.uuid7())
        self.transcription_ts = utils.now()
        # empty working audio
        if flush_working_audio:
            log.debug(f'Participant {self.participant_id}: flushing working audio')
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
