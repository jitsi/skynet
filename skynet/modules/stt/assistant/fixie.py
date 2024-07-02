#!/usr/bin/env python

import simple_parsing

from ultravox.inference import ultravox_infer
from ultravox.tools.infer_tool import InferArgs, oneshot_infer

from skynet.modules.stt.assistant.v1.models import TestPayload


def init():
    global inference

    inference = ultravox_infer.UltravoxInference(
        '/home/tavram/fixie/ultravox-v0.2',
    )


def test(payload: TestPayload):
    oneshot_infer(inference, InferArgs(audio_file=open(payload.audio, 'rb'), prompt=payload.prompt))


__all__ = ['init', 'test']
