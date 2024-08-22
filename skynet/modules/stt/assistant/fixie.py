#!/usr/bin/env python
import time
from collections.abc import Iterator

from ultravox.data import datasets
from ultravox.inference import base, ultravox_infer

from skynet.env import fixie_path

history = []


def run(
    inference: base.VoiceInference,
    audio: bytes,
) -> Iterator[str]:
    transcribe_message = [{"role": "user", "content": "Transcribe |audio|"}]
    answer_request = [{"role": "user", "content": "Listen to |audio| and answer it"}]

    sample = datasets.VoiceSample(history + transcribe_message + answer_request, datasets.audio_from_buf(audio))

    first_token_time = None

    # Run streaming inference and print the output as it arrives.
    stream = inference.infer_stream(sample)

    history.append({"role": "assistant", "content": ""})

    for msg in stream:
        if isinstance(msg, base.InferenceChunk):
            if first_token_time is None:
                first_token_time = time.time()

            print(msg.text, end="", flush=True)

            # add message to last entry in history
            history[-1]["content"] += f'{msg.text} '

            yield msg.text

    print("\n")

    if first_token_time is None:
        raise ValueError("No tokens received")


def init():
    global inference

    inference = ultravox_infer.UltravoxInference(fixie_path)


def oneshot(audio: bytes) -> Iterator[str]:
    return run(inference, audio)
