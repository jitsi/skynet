from faster_whisper import WhisperModel
import asyncio
from skynet.modules.stt.shared.models.transcription_response import TranscriptionResponse
from skynet.modules.stt.shared.models.whisper import WhisperResult
from skynet.modules.stt.shared.utils import Uuid7, load_audio
from skynet.env import (
    whisper_recorder_quantization,
    whisper_recorder_model_path,
    whisper_recorder_model_name
)

worker_name = 'recording_transcriber_worker'

def lognow(msg):
    with open(f'/tmp/{worker_name}.log', 'a') as f:
        f.write(f'{msg}\n')

async def recording_transcriber_worker(audio_queue: asyncio.Queue, transcription_queue: asyncio.Queue, name: str):
    global worker_name
    worker_name = name
    path_or_model_name = whisper_recorder_model_name if whisper_recorder_model_name else whisper_recorder_model_path
    recording_model = WhisperModel(
        model_size_or_path=path_or_model_name,
        device='cpu',
        compute_type=whisper_recorder_quantization,
        num_workers=4,
        download_root=whisper_recorder_model_path,
    )
    lognow('Recording transcriber worker started')
    while True:
        try:
            data = audio_queue.get_nowait()
            lognow(f'Got data from the audio queue: {data}')
        except Exception:
            await asyncio.sleep(1)
            continue
        meeting_id = data['meeting_id']
        participant_id = data['participant_id']
        with open(data['audio_path'], 'rb') as f:
            audio_bytes = f.read()
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
            language_detection_segments=3,
            language_detection_threshold=0.7
        )
        lognow('After transcribe')
        ts_result = WhisperResult([res for res in segments])
        lognow(f'Got result from the whisper model: {ts_result.text}')
        if ts_result.text.strip():
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
                lognow(f'Adding {len(results)} results to the transcription queue')
                transcription_queue.put_nowait({'meeting_id': meeting_id, 'results': results})
            except Exception as e:
                lognow(f'Queue exception: {e}')
                continue
            audio_queue.task_done()
