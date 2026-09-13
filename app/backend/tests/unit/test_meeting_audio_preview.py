"""Source review reads bounded real audio without weakening inference quality."""

import io
import os
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.speaker_ports import SpeakerError


def write_source(tmp_path, *, rate=16000, channels=1, seconds=3, format="WAV", value=0.25):
    storage = MeetingAudioStorage(tmp_path)
    key = "7" * 32 + ".meeting"
    data = np.full((round(seconds * rate), channels), value, dtype=np.float32)
    sf.write(storage.path(key), data, rate, format=format, subtype="PCM_16")
    metadata = {
        "expected_bytes": storage.path(key).stat().st_size,
        "expected_format": format,
        "sample_rate": rate,
        "channels": channels,
        "duration_seconds": seconds,
    }
    return storage, key, metadata


@pytest.mark.parametrize("rate", [8000, 16000, 48000, 192000])
@pytest.mark.parametrize("format,channels", [("WAV", 1), ("WAV", 8), ("FLAC", 2)])
def test_preview_preserves_rate_range_mono_and_source(tmp_path, rate, format, channels):
    storage, key, metadata = write_source(tmp_path, rate=rate, channels=channels, format=format)
    path = storage.path(key)
    before = path.read_bytes()
    preview = storage.preview(key, 0.5, 3, **metadata)
    with sf.SoundFile(io.BytesIO(preview)) as audio:
        assert (audio.format, audio.subtype, audio.channels, audio.samplerate) == (
            "WAV",
            "PCM_16",
            1,
            rate,
        )
        assert audio.frames == round(2.5 * rate)
        assert np.all(audio.read() == 0.25)
    assert preview == storage.preview(key, 0.5, 3, **metadata)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_preview_downmixes_channels_and_allows_clipping_only_for_review(tmp_path):
    storage, key, metadata = write_source(tmp_path, channels=2, value=1)
    data = np.tile(np.array([1.0, -0.5], dtype=np.float32), (3 * 16000, 1))
    sf.write(storage.path(key), data, 16000, format="WAV", subtype="PCM_16")
    preview = storage.preview(key, 0, 3, **metadata)
    samples, rate = sf.read(io.BytesIO(preview))
    assert rate == 16000 and np.allclose(samples, 0.25, atol=1 / 32768)
    with pytest.raises(SpeakerError, match="clipped_audio"):
        storage.window(key, 0, 3)
    with pytest.raises(SpeakerError, match="clipped_audio"):
        storage.sample(key, [(0, 48000)], 16000)


def test_thirty_seconds_at_maximum_rate_is_bounded_and_seeks_exact_source(tmp_path, monkeypatch):
    storage, key, metadata = write_source(tmp_path, rate=192000, seconds=65)
    original_read = sf.SoundFile.read
    observations = []

    def bounded_read(source, frames=-1, *args, **kwargs):
        observations.append((source.tell(), frames))
        assert 0 < frames <= 65536
        return original_read(source, frames, *args, **kwargs)

    monkeypatch.setattr(sf.SoundFile, "read", bounded_read)
    preview = storage.preview(key, 35, 65, **metadata)
    assert observations[0][0] == 35 * 192000
    assert sum(frames for _, frames in observations) == 30 * 192000
    assert len(preview) <= 11520128
    with sf.SoundFile(io.BytesIO(preview)) as audio:
        assert audio.frames == 30 * 192000


@pytest.mark.parametrize(
    "start,end",
    [
        (-1, 1),
        (0, 0),
        (2, 1),
        (0, 31),
        (0, 3.1),
        (float("nan"), 1),
        (0, float("inf")),
        (0, 0.000001),
    ],
)
def test_invalid_preview_range_is_a_safe_422(tmp_path, start, end):
    storage, key, metadata = write_source(tmp_path)
    with pytest.raises(SpeakerError, match="invalid_audio_range") as caught:
        storage.preview(key, start, end, **metadata)
    assert caught.value.status_code == 422


@pytest.mark.parametrize("change", ["missing", "size", "rate", "channels", "format", "duration"])
def test_changed_or_missing_source_is_unavailable(tmp_path, change):
    storage, key, metadata = write_source(tmp_path)
    if change == "missing":
        storage.path(key).unlink()
    elif change == "size":
        with storage.path(key).open("ab") as target:
            target.write(b"extra")
    else:
        field = {
            "rate": "sample_rate",
            "format": "expected_format",
            "duration": "duration_seconds",
        }.get(change, change)
        metadata[field] = {"rate": 48000, "channels": 2, "format": "FLAC", "duration": 2}[change]
    with pytest.raises(SpeakerError, match="recording_unavailable") as caught:
        storage.preview(key, 0, 1, **metadata)
    assert caught.value.status_code == 410


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 2.0])
def test_nonfinite_or_out_of_range_samples_fail_closed(tmp_path, value):
    storage, key, metadata = write_source(tmp_path)
    sf.write(storage.path(key), np.full(48000, value), 16000, format="WAV", subtype="FLOAT")
    metadata["expected_bytes"] = storage.path(key).stat().st_size
    with pytest.raises(SpeakerError, match="recording_unavailable"):
        storage.preview(key, 0, 1, **metadata)


@pytest.mark.parametrize("link", ["file", "parent", "hardlink"])
def test_preview_refuses_linked_source_paths(tmp_path, link):
    owned = tmp_path / "owned"
    owned.mkdir()
    storage, key, metadata = write_source(owned)
    path = storage.path(key)
    try:
        if link == "parent":
            moved = tmp_path / "moved"
            owned.rename(moved)
            owned.symlink_to(moved, target_is_directory=True)
        elif link == "file":
            target = tmp_path / "target.wav"
            path.rename(target)
            path.symlink_to(target)
        else:
            os.link(path, tmp_path / "alias.wav")
    except OSError as exc:
        pytest.skip(f"filesystem cannot create the required link: {exc}")
    with pytest.raises(SpeakerError, match="recording_unavailable"):
        storage.preview(key, 0, 1, **metadata)


def test_preview_refuses_path_replaced_while_reading(tmp_path, monkeypatch):
    storage, key, metadata = write_source(tmp_path)
    original_read = sf.SoundFile.read
    changed = False

    def replace_while_reading(source, *args, **kwargs):
        nonlocal changed
        data = original_read(source, *args, **kwargs)
        if not changed:
            changed = True
            path = storage.path(key)
            replacement = tmp_path / "replacement.wav"
            replacement.write_bytes(path.read_bytes())
            replacement.replace(path)
        return data

    monkeypatch.setattr(sf.SoundFile, "read", replace_while_reading)
    with pytest.raises(SpeakerError, match="recording_unavailable"):
        storage.preview(key, 0, 1, **metadata)


def test_preview_refuses_parent_link_existing_when_storage_is_constructed(tmp_path):
    owned = tmp_path / "owned"
    owned.mkdir()
    _, key, metadata = write_source(owned)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(owned, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"filesystem cannot create the required link: {exc}")
    storage = MeetingAudioStorage(alias)
    with pytest.raises(SpeakerError, match="recording_unavailable"):
        storage.preview(key, 0, 1, **metadata)


def test_source_removed_before_open_is_unavailable(tmp_path, monkeypatch):
    storage, key, metadata = write_source(tmp_path)
    original_open = os.open

    def delete_then_open(path, flags, *args, **kwargs):
        Path(path).unlink()
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", delete_then_open)
    with pytest.raises(SpeakerError, match="recording_unavailable"):
        storage.preview(key, 0, 1, **metadata)
