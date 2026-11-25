"""A whole recording is resampled block by block to the same samples as one long resample."""

import numpy as np
import pytest
from scipy.signal import resample_poly

from voiceup_inference.errors import InferenceError
from voiceup_inference.recording_audio import PcmRecordingReader


def pcm(seconds: float, rate: int, seed: int = 3) -> np.ndarray:
    generator = np.random.default_rng(seed)
    return (generator.uniform(-0.5, 0.5, round(seconds * rate)) * 32767).astype("<i2")


def read(samples: np.ndarray, rate: int, pieces: list[int]) -> np.ndarray:
    data = samples.tobytes()
    reader = PcmRecordingReader(rate, len(data))
    offset = 0
    for size in pieces:
        reader.push(data[offset : offset + size])
        offset += size
    reader.push(data[offset:])
    return reader.finish().samples


@pytest.mark.parametrize("rate", [8000, 22050, 44100, 48000])
def test_block_resampling_matches_one_long_resample(rate):
    samples = pcm(75.3, rate)
    expected = resample_poly(samples.astype(np.float64) / 32768, 16000 // np.gcd(rate, 16000), rate // np.gcd(rate, 16000))
    actual = read(samples, rate, [1, 3, 4097, 1_000_001])
    assert actual.dtype == np.float32 and len(actual) == len(expected)
    assert np.max(np.abs(actual - expected)) < 1e-5


def test_sixteen_kilohertz_passes_through_unchanged():
    samples = pcm(12.0, 16000)
    actual = read(samples, 16000, [7, 9])
    assert np.array_equal(actual, samples.astype(np.float32) / 32768)


def test_declared_length_must_match_the_stream():
    reader = PcmRecordingReader(16000, 32000)
    reader.push(b"\0" * 31998)
    with pytest.raises(InferenceError) as error:
        reader.finish()
    assert error.value.code == "invalid_audio"
    with pytest.raises(InferenceError) as error:
        PcmRecordingReader(16000, 32000).push(b"\0" * 32002)
    assert error.value.code == "audio_limit"


def test_heavily_clipped_recording_is_rejected_like_a_chunk():
    samples = pcm(10.0, 16000)
    samples[: len(samples) // 10] = 32767
    with pytest.raises(InferenceError) as error:
        read(samples, 16000, [])
    assert error.value.code == "clipped_audio"


@pytest.mark.parametrize(
    ("rate", "size"), [(7999, 2), (192001, 2), (16000, 0), (16000, 3), (8000, 4 * 3600 * 8000 * 2 + 2)]
)
def test_invalid_dimensions_are_refused_before_reading(rate, size):
    with pytest.raises(InferenceError):
        PcmRecordingReader(rate, size)
