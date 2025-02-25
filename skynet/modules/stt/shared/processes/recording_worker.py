import asyncio
from datetime import datetime, timezone

from faster_whisper import WhisperModel

from skynet.env import whisper_recorder_model_name, whisper_recorder_model_path, whisper_recorder_quantization
from skynet.modules.stt.shared.models.transcription_response import TranscriptionResponse
from skynet.modules.stt.shared.models.whisper import WhisperResult
from skynet.modules.stt.shared.utils import load_audio, Uuid7
from logging import getLogger, handlers, Formatter

def setup_logger(worker_name: str):
    log = getLogger(worker_name)
    log_handler = handlers.TimedRotatingFileHandler(f'/tmp/{worker_name}.log', when='midnight', backupCount=3)
    log_handler.setFormatter(Formatter(fmt='%(asctime)s - %(message)s'))
    log.addHandler(log_handler)
    log.setLevel('DEBUG')
    return log

async def recording_transcriber_worker(audio_queue: asyncio.Queue, transcription_queue: asyncio.Queue, name: str):
    log = setup_logger(name)
    path_or_model_name = whisper_recorder_model_name if whisper_recorder_model_name else whisper_recorder_model_path
    log.info(f'Loading Whisper model from {path_or_model_name}')
    recording_model = WhisperModel(
        model_size_or_path=path_or_model_name,
        device='cpu',
        compute_type=whisper_recorder_quantization,
        num_workers=4,
        download_root=whisper_recorder_model_path,
    )
    log.info('Recording transcriber worker started')
    while True:
        try:
            data = audio_queue.get_nowait()
            log.debug(f'Got data from the audio queue: {data}')
        except Exception:
            await asyncio.sleep(1)
            continue
        meeting_id = data['meeting_id']
        participant_id = data['participant_id']
        try:
            with open(data['audio_path'], 'rb') as f:
                audio_bytes = f.read()
        except Exception as e:
            log.error(f'Error reading audio file {data["audio_path"]}:\n{e}')
            continue
        audio = load_audio(audio_bytes)
        audio_start_timestamp = data['start_timestamp']
        lang = data.get('language', None)
        previous_tokens = data.get('previous_tokens', [])
        segments, _ = recording_model.transcribe(
            audio,
            language=lang,
            task='transcribe',
            word_timestamps=True,
            beam_size=5,
            initial_prompt=previous_tokens,
            condition_on_previous_text=False,
            vad_filter=True,
            language_detection_segments=2,
            language_detection_threshold=0.7,
        )
        ts_result = WhisperResult([res for res in segments])
        if ts_result.text.strip():
            log.debug(f'Transcription results:\n{ts_result.text}')
            results = []
            temp_result_words = []
            start_timestamp = None
            for word in ts_result.words:
                if not start_timestamp:
                    start_timestamp = int(word.start * 1000) + audio_start_timestamp
                temp_result_words.append(word)
                temp_result_prob = sum([word.probability for word in temp_result_words]) / len(temp_result_words)
                if word.word[-1] in ['.', '!', '?']:
                    uuid = Uuid7()
                    results.append(
                        TranscriptionResponse(
                            id=str(uuid.get(start_timestamp)),
                            participant_id=participant_id,
                            ts=start_timestamp,
                            text=''.join([w.word for w in temp_result_words]),
                            audio='',
                            type='final',
                            variance=temp_result_prob,
                        )
                    )
                    temp_result_words = []
                    start_timestamp = None
            try:
                log.info(f'Adding {len(results)} results to the transcription queue')
                transcription_queue.put_nowait({'meeting_id': meeting_id, 'results': results})
            except Exception as e:
                log.error(f'Result queue exception: {e}')
                continue
            audio_queue.task_done()
