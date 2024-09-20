from av.audio.frame import AudioFrame
from av.audio.resampler import AudioResampler


class PcmResampler:
    def __init__(self, **kwargs) -> None:
        self.resampler = AudioResampler(**kwargs)
        self.layout = kwargs.get("layout")
        self.format = kwargs.get("format")

    def resample(self, frame: AudioFrame) -> bytes:
        resampled_raw = b''
        resampled_frames = self.resampler.resample(frame)

        for resampled_frame in resampled_frames:
            resampled_raw += bytes(resampled_frame.planes[0])

        return resampled_raw


__all__ = ["PcmResampler"]
