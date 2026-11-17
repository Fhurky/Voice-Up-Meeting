"""Read a whole meeting as a mono PCM16 stream and keep only its 16 kHz samples in memory."""

from math import ceil, gcd

import numpy as np
from scipy.signal import resample_poly

from voiceup.audio import Audio

from .errors import InferenceError

TARGET_RATE = 16000
MAX_RECORDING_SECONDS = 4 * 3600
# Context on each side of a block; scipy's default filter reaches far less than this.
CONTEXT_SAMPLES = 4096
BLOCK_SECONDS = 30
# The same rejection rule as one decoded chunk (audio.decode_audio).
CLIPPED_SHARE = 0.05
CLIPPED_LEVEL = 0.999


class PcmRecordingReader:
    """Resample block by block with overlapping context so the result equals one long resample."""

    def __init__(self, rate: int, size_bytes: int) -> None:
        if not 8000 <= rate <= 192000:
            raise InferenceError("invalid_audio", "Unsupported audio dimensions", 400)
        if size_bytes <= 0 or size_bytes % 2:
            raise InferenceError("invalid_audio", "Recording must be whole PCM16 samples", 400)
        self.frames = size_bytes // 2
        if self.frames / rate > MAX_RECORDING_SECONDS:
            raise InferenceError("audio_limit", "Recording exceeds the duration limit", 413)
        factor = gcd(rate, TARGET_RATE)
        self.up, self.down = TARGET_RATE // factor, rate // factor
        self.block = self.down * ceil(rate * BLOCK_SECONDS / self.down)
        self.context = self.down * ceil(CONTEXT_SAMPLES / self.down)
        self.output = np.empty(ceil(self.frames * self.up / self.down), dtype=np.float32)
        self.written = 0
        self.received = 0
        self.clipped = 0
        self.pending = b""
        # Source samples from `base`; the next block to resample starts at `start`.
        self.buffer = np.empty(0, dtype=np.float64)
        self.base = 0
        self.start = 0

    def push(self, data: bytes) -> None:
        data = self.pending + data
        whole = len(data) - len(data) % 2
        self.pending = data[whole:]
        if self.received + whole // 2 > self.frames:
            raise InferenceError("audio_limit", "Recording exceeds its declared size", 413)
        if not whole:
            return
        samples = np.frombuffer(data[:whole], dtype="<i2").astype(np.float64) / 32768
        self.received += len(samples)
        self.clipped += int(np.count_nonzero(np.abs(samples) >= CLIPPED_LEVEL))
        self.buffer = np.concatenate([self.buffer, samples])
        while self.received >= self.start + self.block + self.context:
            self._emit(self.start + self.block)

    def finish(self) -> Audio:
        if self.pending or self.received != self.frames:
            raise InferenceError("invalid_audio", "Recording ended before its declared size", 400)
        if self.start < self.frames:
            self._emit(self.frames)
        if self.written != len(self.output):
            raise InferenceError("invalid_audio", "Recording could not be resampled", 400)
        if self.clipped / self.frames > CLIPPED_SHARE:
            raise InferenceError("clipped_audio", "Audio is heavily clipped")
        if np.max(np.abs(self.output)) > 1.05:
            raise InferenceError("clipped_audio", "Audio has excessive full-scale peaks")
        np.clip(self.output, -1, 1, out=self.output)
        return Audio(self.output)

    def _emit(self, end: int) -> None:
        left = max(0, self.start - self.context)
        right = min(self.received, end + self.context)
        source = self.buffer[left - self.base : right - self.base]
        if (self.up, self.down) == (1, 1):
            produced = source
        else:
            produced = resample_poly(source, self.up, self.down)
        offset = (self.start - left) * self.up // self.down
        count = ceil((end - self.start) * self.up / self.down)
        self.output[self.written : self.written + count] = produced[offset : offset + count]
        self.written += count
        self.start = end
        keep = max(0, self.start - self.context)
        self.buffer = self.buffer[keep - self.base :]
        self.base = keep
