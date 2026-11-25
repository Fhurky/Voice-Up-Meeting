"""PRD 037 pure rules: capture bounds, the part chain, chunk order and channel-selective reading."""

import hashlib
import io
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.domain.meeting import (
    CAPTURE_CHAIN_START,
    capture_frames,
    capture_max_frames,
    capture_wav_header,
    meeting_tracks,
    next_capture_chain,
    previous_track_chunk,
    track_windows,
)
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.speaker_ports import SpeakerError

RATE = 16000


def test_capture_bounds_follow_duration_and_byte_limits() -> None:
    assert capture_max_frames(RATE, 14400, 2 * 1024**3) == RATE * 14400
    assert capture_max_frames(192000, 14400, 2 * 1024**3) == (2 * 1024**3 - 44) // 4
    assert capture_frames(0) == 0 and capture_frames(44) == 0 and capture_frames(44 + 8) == 2


def test_the_chain_matches_the_browser_definition() -> None:
    parts = [b"\x01\x02\x03\x04", b"\x05\x06\x07\x08"]
    chain = CAPTURE_CHAIN_START
    for part in parts:
        chain = next_capture_chain(chain, hashlib.sha256(part).hexdigest())
    expected = bytes(32)
    for part in parts:
        expected = hashlib.sha256(expected + hashlib.sha256(part).digest()).digest()
    assert chain == expected.hex()


def test_the_header_describes_two_channel_pcm16() -> None:
    pcm = np.array([[1, -1], [2, -2]], dtype="<i2").tobytes()
    with sf.SoundFile(io.BytesIO(capture_wav_header(RATE, 2) + pcm)) as source:
        assert (source.channels, source.samplerate, source.frames) == (2, RATE, 2)
        assert source.subtype == "PCM_16"


def test_chunks_alternate_channels_inside_each_window() -> None:
    assert meeting_tracks("file") == (None,) and meeting_tracks("two_channel") == (0, 1)
    chunks = track_windows(330, (0, 1))
    assert [(window[0], window[2], channel) for window, channel in chunks] == [
        (0, 0.0, 0),
        (1, 0.0, 1),
        (2, 300.0, 0),
        (3, 300.0, 1),
    ]
    assert [previous_track_chunk(chunks, index) for index in range(4)] == [None, None, 0, 1]
    single = track_windows(330, (None,))
    assert [window[0] for window, _ in single] == [0, 1]
    assert [previous_track_chunk(single, index) for index in range(2)] == [None, 0]


@pytest.fixture
def stereo_storage(tmp_path: Path) -> tuple[MeetingAudioStorage, str]:
    storage = MeetingAudioStorage(tmp_path)
    key = "0" * 32 + ".meeting"
    frames = RATE
    samples = np.empty((frames, 2), dtype="float32")
    samples[:, 0], samples[:, 1] = 0.1, 0.5
    sf.write(tmp_path / key, samples, RATE, format="WAV", subtype="PCM_16")
    return storage, key


def level(wav: bytes) -> float:
    with sf.SoundFile(io.BytesIO(wav)) as source:
        assert source.channels == 1
        return round(float(np.abs(source.read(dtype="float32")).mean()), 2)


def test_reading_one_channel_keeps_the_other_out(stereo_storage) -> None:
    storage, key = stereo_storage
    assert level(storage.window(key, 0, 1, channel=0)) == 0.1
    assert level(storage.window(key, 0, 1, channel=1)) == 0.5
    assert level(storage.window(key, 0, 1)) == 0.3
    assert level(storage.sample(key, [(0, RATE)], RATE, channel=1)) == 0.5
    blocks = b"".join(storage.recording_blocks(key, channel=0))
    assert round(float(np.abs(np.frombuffer(blocks, dtype="<i2")).mean()) / 32768, 2) == 0.1
    with pytest.raises(SpeakerError):
        storage.window(key, 0, 1, channel=2)


def test_a_streamed_source_gets_its_header_without_touching_samples(tmp_path: Path) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "1" * 32 + ".meeting"
    pcm = np.array([[100, -100]] * 8, dtype="<i2").tobytes()
    payload = bytes(44) + pcm
    storage.append(key, 0, payload, hashlib.sha256(payload).hexdigest())
    assert storage.read_range(key, 44, 8) == pcm[:8]
    storage.write_header(key, capture_wav_header(RATE, 8))
    info = storage.validate(key, len(payload), "WAV")
    assert (info.channels, info.sample_rate, info.duration_seconds) == (2, RATE, 8 / RATE)
    assert (tmp_path / key).read_bytes()[44:] == pcm
    with pytest.raises(SpeakerError):
        storage.write_header(key, b"short")
