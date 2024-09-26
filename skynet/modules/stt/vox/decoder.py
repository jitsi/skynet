import fractions
import time
from typing import List, Optional

from av import CodecContext
from av.audio.codeccontext import AudioCodecContext
from av.audio.frame import AudioFrame
from av.packet import Packet

SAMPLE_RATE = 8000
TIME_BASE = fractions.Fraction(1, 8000)


class PcmDecoder:
    def __init__(self, codec_name: str) -> None:
        self.codec: AudioCodecContext = CodecContext.create(codec_name, "r")
        self.codec.format = "s16"
        self.codec.layout = "mono"
        self.codec.sample_rate = SAMPLE_RATE

    def decode(self, data: bytes, timestamp: Optional[int] = None) -> List[AudioFrame]:
        packet = Packet(data)
        packet.pts = timestamp or int(time.time())
        packet.time_base = TIME_BASE
        return self.codec.decode(packet)


class PcmaDecoder(PcmDecoder):
    def __init__(self) -> None:
        super().__init__("pcm_alaw")


__all__ = ["PcmaDecoder"]
