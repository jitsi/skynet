import os

import torch
from faster_whisper import WhisperModel

from skynet.env import whisper_compute_type, whisper_device, whisper_gpu_indices, whisper_model_name, whisper_model_path
from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.utils import vad_utils as vad

log = get_logger(__name__)


def get_device() -> str:
    if torch.cuda.is_available():
        log.debug('CUDA device found.')
        return 'cuda'
    log.warning('No CUDA device found, defaulting to CPU.')
    return 'cpu'


vad_model = vad.init_jit_model(f'{os.getcwd()}/skynet/modules/stt/streaming_whisper/models/vad/silero_vad.jit')

device = whisper_device if whisper_device != 'auto' else get_device()
log.info(f'Using {device}')
num_workers = 1
gpu_indices = [0]

if whisper_gpu_indices is not None:
    gpu_indices = whisper_gpu_indices.strip().split(',')
    # one worker per gpu core
    num_workers = len(gpu_indices)

path_or_model_name = whisper_model_name if whisper_model_name is not None else whisper_model_path

model = WhisperModel(
    path_or_model_name,
    device=device,
    device_index=gpu_indices,
    compute_type=whisper_compute_type,
    num_workers=num_workers,
    download_root=whisper_model_path,
)

one_byte_s = 0.00003125  # the equivalent of one byte in seconds
