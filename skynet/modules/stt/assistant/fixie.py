#!/usr/bin/env python
import time
from collections.abc import Iterator

from ultravox.data import datasets
from ultravox.inference import base, ultravox_infer

from skynet.env import fixie_path


def run(
    inference: base.VoiceInference,
    audio: bytes,
    prompt: str,
) -> Iterator[str]:
    sample = datasets.VoiceSample.from_prompt_and_buf(prompt, audio)

    first_token_time = None
    stats = None

    # Run streaming inference and print the output as it arrives.
    stream = inference.infer_stream(sample)

    for msg in stream:
        if isinstance(msg, base.InferenceChunk):
            if first_token_time is None:
                first_token_time = time.time()

            print(msg.text, end="", flush=True)

            yield msg.text
        elif isinstance(msg, base.InferenceStats):
            stats = msg

    print("\n")

    if first_token_time is None or stats is None:
        raise ValueError("No tokens received")


def init():
    global inference

    inference = ultravox_infer.UltravoxInference(fixie_path)


def oneshot(audio: bytes) -> Iterator[str]:
    prompt = 'Listen to <|audio|>. If it contains a question, answer it, else respond with "."'

    return run(inference, audio, prompt)
