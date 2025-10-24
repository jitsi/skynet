from itertools import cycle
from typing import Tuple

from faster_whisper import WhisperModel
from silero_vad import load_silero_vad

from skynet.env import (
    device,
    whisper_compute_type,
    whisper_device,
    whisper_gpu_indices,
    whisper_model_name,
    whisper_model_path,
    whisper_model_pool_size,
)
from skynet.logs import get_logger

log = get_logger(__name__)


vad_model = load_silero_vad(onnx=False)

device = whisper_device if whisper_device != 'auto' else device
log.info(f'Using {device}')
num_workers = 1
gpu_indices = [0]

if whisper_gpu_indices is not None:
    gpu_indices = whisper_gpu_indices.strip().split(',')
    # one worker per gpu core
    num_workers = len(gpu_indices)

path_or_model_name = whisper_model_name if whisper_model_name is not None else whisper_model_path

one_byte_s = 0.00003125  # the equivalent of one byte in seconds for 16kHz audio, 2 bytes per sample, mono


class ModelPool:
    """Pool of Whisper model instances for parallel processing using round-robin scheduling"""

    def __init__(self, num_instances: int):
        self.models = []

        log.info(f'Initializing ModelPool with {num_instances} instance(s)')

        for i in range(num_instances):
            log.info(f'Loading model instance {i + 1}/{num_instances}...')
            model_instance = WhisperModel(
                path_or_model_name,
                device=device,
                device_index=gpu_indices,
                compute_type=whisper_compute_type,
                num_workers=num_workers,
                download_root=whisper_model_path,
            )
            self.models.append(model_instance)

            if i == 0:
                log.info('====== WHISPER MODEL INFO ======')
                log.info(f'Model: {path_or_model_name}')
                log.info(f'Multilingual: {model_instance.model.is_multilingual}')
                log.info(f'Compute Type: {whisper_compute_type}')
                log.info(f'Device: {device}')
                log.info(f'Pool Size: {num_instances}')

        # Create round-robin iterator over model instances
        self.model_cycle = cycle(enumerate(self.models))

        log.info(f'ModelPool initialization complete')

    def get_next_model(self) -> Tuple[WhisperModel, int]:
        """Get next model in round-robin fashion"""
        idx, model = next(self.model_cycle)
        return model, idx

    def release_model(self, idx: int):
        """No-op in round-robin scheduling"""


# Initialize model pool (single instance by default, 3+ on GPU)
model_pool = ModelPool(num_instances=whisper_model_pool_size)
