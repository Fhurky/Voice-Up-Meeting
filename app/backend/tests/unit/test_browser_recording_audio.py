"""Browser PCM byte contracts through the real on-premise WAV decoder."""

import hashlib
import io
import struct
from pathlib import Path

import pytest
import soundfile as sf

from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.speaker_ports import SpeakerError


def pcm_wav(rate: int = 16000) -> bytes:
    """Independent equivalent of the browser's little-endian DataView writer."""
    samples = struct.pack("<8h", 0, 8192, -8192, 16384, -16384, 4096, -4096, 0)
    pcm = samples * (rate * 2 // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(pcm),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        rate,
        rate * 2,
        2,
        16,
        b"data",
        len(pcm),
    )
    assert len(header) == 44
    return header + pcm


@pytest.mark.parametrize("rate", [16000, 44100, 48000])
def test_browser_pcm_header_preserves_actual_rate_and_window_fidelity(
    tmp_path: Path, rate: int
) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "a" * 32 + ".meeting"
    source = pcm_wav(rate)
    storage.append(key, 0, source, hashlib.sha256(source).hexdigest())
    info = storage.validate(key, len(source), "WAV")
    assert (info.duration_seconds, info.sample_rate, info.channels) == (2, rate, 1)
    assert info.sha256 == hashlib.sha256(source).hexdigest()
    decoded, decoded_rate = sf.read(
        io.BytesIO(storage.window(key, 0.25, 1.25)), dtype="int16", always_2d=True
    )
    expected = struct.unpack(f"<{rate * 2}h", source[44:])
    assert decoded_rate == rate
    assert decoded.shape == (rate, 1)
    assert decoded[:, 0].tolist() == list(expected[rate // 4 : rate // 4 + rate])
    assert storage.path(key).read_bytes() == source


@pytest.mark.parametrize(
    "damage",
    ["header", "body", "body-with-correct-riff-size", "trailing-bytes", "partial-chunk"],
)
def test_incomplete_browser_wav_cannot_be_silently_decoded(tmp_path: Path, damage: str) -> None:
    source = pcm_wav()
    if damage == "header":
        source = source[:40]
    elif damage == "body":
        source = source[:-2]
    elif damage == "body-with-correct-riff-size":
        source = source[:-2]
        source = source[:4] + struct.pack("<I", len(source) - 8) + source[8:]
    elif damage == "trailing-bytes":
        source += b"\x00\x00"
    else:
        source += b"JUNK"
        source = source[:4] + struct.pack("<I", len(source) - 8) + source[8:]
    storage = MeetingAudioStorage(tmp_path)
    key = "b" * 32 + ".meeting"
    storage.path(key).write_bytes(source)
    with pytest.raises(SpeakerError, match="invalid_audio"):
        storage.validate(key, len(source), "WAV")


def test_legal_noncanonical_riff_chunks_and_odd_padding_remain_accepted(
    tmp_path: Path,
) -> None:
    source = pcm_wav()
    before = b"JUNK" + struct.pack("<I", 3) + b"abc\x00"
    after = b"LIST" + struct.pack("<I", 4) + b"INFO"
    source = source[:12] + before + source[12:] + after
    source = source[:4] + struct.pack("<I", len(source) - 8) + source[8:]
    storage = MeetingAudioStorage(tmp_path)
    key = "c" * 32 + ".meeting"
    storage.path(key).write_bytes(source)
    info = storage.validate(key, len(source), "WAV")
    assert (info.duration_seconds, info.sample_rate, info.channels) == (2, 16000, 1)
    assert info.sha256 == hashlib.sha256(source).hexdigest()


def test_existing_rf64_container_keeps_its_separate_size_contract(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    sf.write(buffer, [0.25] * 8000, 8000, format="RF64", subtype="PCM_16")
    source = buffer.getvalue()
    assert source[:4] == b"RF64"
    storage = MeetingAudioStorage(tmp_path)
    key = "d" * 32 + ".meeting"
    storage.path(key).write_bytes(source)
    info = storage.validate(key, len(source), "WAV")
    assert (info.duration_seconds, info.sample_rate, info.channels) == (1, 8000, 1)
