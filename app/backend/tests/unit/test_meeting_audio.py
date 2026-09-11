"""Real bounded-file behavior for the accepted uploaded meeting workflow."""

import hashlib
import io
from pathlib import Path

import pytest
import soundfile as sf

from app.domain.meeting import analysis_windows, clean_union
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.speaker_ports import SpeakerError


def wav(seconds: float = 2, channels: int = 1) -> bytes:
    stream = io.BytesIO()
    sf.write(stream, [[0.1] * channels] * int(seconds * 16000), 16000, format="WAV")
    return stream.getvalue()


def test_four_hour_windows_own_every_sample_once() -> None:
    windows = analysis_windows(14400)
    assert len(windows) == 48
    assert windows[0] == (0, 0.0, 0.0, 300.0, 305.0)
    assert windows[-1] == (47, 14095.0, 14100.0, 14400.0, 14400.0)
    assert sum(end - start for _, _, start, end, _ in windows) == 14400
    assert all(
        context_end - context_start <= 310 for _, context_start, _, _, context_end in windows
    )


def test_one_core_keeps_a_short_meeting_together_and_next_core_owns_only_new_source() -> None:
    assert analysis_windows(182.0250625) == [(0, 0.0, 0.0, 182.0250625, 182.0250625)]
    assert analysis_windows(301) == [
        (0, 0.0, 0.0, 300.0, 301.0),
        (1, 295.0, 300.0, 301.0, 301.0),
    ]


def test_legacy_core_boundaries_remain_addressable_without_changing_current_default() -> None:
    assert analysis_windows(121, core_seconds=60) == [
        (0, 0.0, 0.0, 60.0, 65.0),
        (1, 55.0, 60.0, 120.0, 121.0),
        (2, 115.0, 120.0, 121.0, 121.0),
    ]
    for invalid in (True, 0, 70, 300.0):
        with pytest.raises(ValueError, match="Invalid core duration"):
            analysis_windows(121, core_seconds=invalid)


def test_analysis_window_accepts_310_seconds_but_never_310_plus_one_frame(
    tmp_path: Path,
) -> None:
    import wave

    storage = MeetingAudioStorage(tmp_path)
    key = "3" * 32 + ".meeting"
    with wave.open(str(storage.path(key)), "wb") as source:
        source.setnchannels(1)
        source.setsampwidth(2)
        source.setframerate(8000)
        source.writeframes(b"\x00\x00" * (310 * 8000 + 1))
    with sf.SoundFile(io.BytesIO(storage.window(key, 0, 310))) as source:
        assert source.frames == 310 * 8000 and source.samplerate == 8000
    with pytest.raises(SpeakerError, match="invalid_audio"):
        storage.window(key, 0, 310 + 1 / 8000)


def test_clean_union_clips_context_deduplicates_and_excludes_overlap() -> None:
    assert clean_union([(0, 10), (5, 15), (20, 30)], [(8, 12), (25, 28)], 0, 26) == [
        (0, 8),
        (12, 15),
        (20, 25),
    ]
    assert clean_union([(0, 10), (0, 10)], [], 0, 10) == [(0, 10)]


@pytest.mark.parametrize("interval", [(1, 0), (0, float("nan")), (-1, 2)])
def test_invalid_sample_intervals_fail(interval: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        clean_union([interval], [], 0, 100)


def test_append_recovers_uncommitted_tail_and_verifies_digest(tmp_path: Path) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "a" * 32 + ".meeting"
    first, second = b"first", b"second"
    storage.append(key, 0, first, hashlib.sha256(first).hexdigest())
    storage.path(key).write_bytes(first + b"uncommitted tail")
    storage.append(key, len(first), second, hashlib.sha256(second).hexdigest())
    assert storage.path(key).read_bytes() == first + second
    with pytest.raises(SpeakerError, match="chunk_hash_mismatch"):
        storage.append(key, len(first + second), b"bad", "0" * 64)
    assert storage.path(key).read_bytes() == first + second


def test_append_missing_prefix_is_not_filled_with_silence(tmp_path: Path) -> None:
    storage = MeetingAudioStorage(tmp_path)
    with pytest.raises(SpeakerError, match="recording_unavailable"):
        storage.append("a" * 32 + ".meeting", 20, b"x", hashlib.sha256(b"x").hexdigest())


@pytest.mark.parametrize("key", ["../x", "/tmp/x", "a" * 32 + ".wav", "A" * 32 + ".meeting"])
def test_storage_rejects_non_owned_keys(tmp_path: Path, key: str) -> None:
    with pytest.raises(SpeakerError, match="recording_unavailable"):
        MeetingAudioStorage(tmp_path).path(key)


def test_source_validation_and_bounded_mono_window_preserve_original(
    tmp_path: Path,
) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "b" * 32 + ".meeting"
    source = wav(3, 2)
    storage.append(key, 0, source, hashlib.sha256(source).hexdigest())
    info = storage.validate(key, len(source), "WAV")
    assert (info.duration_seconds, info.sample_rate, info.channels) == (3, 16000, 2)
    assert info.sha256 == hashlib.sha256(source).hexdigest()
    output, rate = sf.read(io.BytesIO(storage.window(key, 1, 2)), always_2d=True)
    assert rate == 16000 and output.shape == (16000, 1)
    assert storage.path(key).read_bytes() == source
    with pytest.raises(SpeakerError, match="invalid_audio"):
        storage.window(key, 0, 311)


def test_selected_profile_sample_does_not_include_gaps_or_duplicate_ranges(
    tmp_path: Path,
) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "c" * 32 + ".meeting"
    source = wav(4)
    storage.append(key, 0, source, hashlib.sha256(source).hexdigest())
    selected = storage.sample(key, [(0, 16000), (0, 16000), (48000, 64000)], 16000)
    with sf.SoundFile(io.BytesIO(selected)) as audio:
        assert audio.frames == 32000


@pytest.mark.parametrize("source_format", ["WAV", "FLAC"])
def test_sample_manifest_matches_exact_bounded_bytes_and_preserves_source(
    tmp_path: Path, source_format: str
) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "9" * 32 + ".meeting"
    rate = 24000
    buffer = io.BytesIO()
    sf.write(
        buffer,
        [[0.125, 0.375]] * (75 * rate),
        rate,
        format=source_format,
        subtype="PCM_16",
    )
    source = buffer.getvalue()
    storage.path(key).write_bytes(source)
    ranges = [(0, 20 * rate), (0, 20 * rate), (25 * rate, 75 * rate)]
    sample = storage.sample_with_manifest(key, ranges, rate)
    assert sample.manifest.sample_rate == rate
    assert sample.manifest.source_frames == 75 * rate
    assert sample.manifest.source_ranges == ((0, 20 * rate), (25 * rate, 65 * rate))
    assert sample.manifest.frames == 60 * rate and sample.manifest.seconds == 60
    assert sample.sha256 == hashlib.sha256(sample.data).hexdigest()
    assert sample.data == storage.sample(key, ranges, rate)
    audio, observed_rate = sf.read(io.BytesIO(sample.data), always_2d=True)
    assert observed_rate == rate and audio.shape == (60 * rate, 1)
    assert (audio == 0.25).all()
    assert storage.path(key).read_bytes() == source


def test_size_and_format_disagreement_fail(tmp_path: Path) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "d" * 32 + ".meeting"
    source = wav()
    storage.append(key, 0, source, hashlib.sha256(source).hexdigest())
    with pytest.raises(SpeakerError, match="upload_incomplete"):
        storage.validate(key, len(source) + 1, "WAV")
    with pytest.raises(SpeakerError, match="unsupported_audio"):
        storage.validate(key, len(source), "FLAC")


def test_original_float_amplitude_cannot_be_hidden_by_mono_conversion(
    tmp_path: Path,
) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "e" * 32 + ".meeting"
    buffer = io.BytesIO()
    sf.write(buffer, [[2.0, -2.0]] * 16000, 16000, format="WAV", subtype="FLOAT")
    source = buffer.getvalue()
    storage.append(key, 0, source, hashlib.sha256(source).hexdigest())
    with pytest.raises(SpeakerError, match="invalid_audio"):
        storage.validate(key, len(source), "WAV")


def test_original_channel_clipping_cannot_be_hidden_in_profile_sample(
    tmp_path: Path,
) -> None:
    storage = MeetingAudioStorage(tmp_path)
    key = "f" * 32 + ".meeting"
    buffer = io.BytesIO()
    sf.write(buffer, [[1.0, -1.0]] * 16000, 16000, format="WAV")
    source = buffer.getvalue()
    storage.append(key, 0, source, hashlib.sha256(source).hexdigest())
    with pytest.raises(SpeakerError, match="clipped_audio"):
        storage.window(key, 0, 1)
    with pytest.raises(SpeakerError, match="clipped_audio"):
        storage.sample(key, [(0, 16000)], 16000)
