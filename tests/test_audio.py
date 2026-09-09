import numpy as np
import pytest
import soundfile as sf

from voiceup.audio import (
    Turn,
    clean_spans,
    load_audio,
    merge_spans,
    speakers_overlap,
    speech_windows,
    validate_turns,
)


def test_clean_spans_subtracts_nested_and_all_other_speakers():
    turns = [
        Turn(0, 20, "A"),
        Turn(2, 4, "B"),
        Turn(3, 5, "C"),
        Turn(8, 12, "B"),
        Turn(9, 10, "D"),
        Turn(18, 24, "C"),
    ]
    assert clean_spans(turns, "A") == [(0, 2), (5, 8), (12, 18)]
    assert clean_spans(turns, "B") == []
    assert clean_spans(turns, "C") == [(20, 24)]
    assert clean_spans(turns, "missing") == []


def test_same_speaker_spans_merge_and_touching_speakers_do_not_overlap():
    turns = [Turn(0, 5, "A"), Turn(3, 8, "A"), Turn(8, 10, "B")]
    assert clean_spans(turns, "A") == [(0, 8)]
    assert not speakers_overlap(turns, "A", "B")
    assert speakers_overlap(turns + [Turn(7.9, 9, "B")], "A", "B")
    assert merge_spans([(2, 4), (0, 3), (4, 5), (7, 7)]) == [(0, 5)]


def test_complete_overlap_produces_no_clean_speech():
    turns = [Turn(0, 10, "A"), Turn(0, 10, "B")]
    assert clean_spans(turns, "A") == []
    assert clean_spans(turns, "B") == []


def test_windows_keep_utterances_independent_and_within_bounds():
    assert speech_windows([(0, 2), (3, 5)]) == []
    assert speech_windows([(0, 12)]) == [(0, 6), (6, 12)]
    windows = speech_windows([(0, 25), (30, 34)])
    assert all(3 <= end - start <= 8 for start, end in windows)
    assert windows[0][0] == 0
    assert windows[-1] == (30, 34)
    with pytest.raises(ValueError):
        speech_windows([(0, 10)], minimum=4, maximum=3)


def test_turn_validation_sorts_and_clamps_only_small_end_rounding():
    turns = validate_turns([Turn(4, 10.01, "B"), Turn(0, 4, "A")], 10)
    assert turns == [Turn(0, 4, "A"), Turn(4, 10, "B")]


@pytest.mark.parametrize(
    "turn",
    [
        Turn(-0.1, 1, "A"),
        Turn(1, 1, "A"),
        Turn(2, 1, "A"),
        Turn(0, float("nan"), "A"),
        Turn(float("inf"), 1, "A"),
        Turn(0, 10.1, "A"),
        Turn(0, 1, ""),
        Turn(0, 1, "  "),
        Turn(10, 10.01, "A"),
        Turn(10.01, 10.015, "A"),
    ],
)
def test_invalid_turns_rejected(turn):
    with pytest.raises(ValueError):
        validate_turns([turn], 10)


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf")])
def test_invalid_recording_duration_rejected(duration):
    with pytest.raises(ValueError):
        validate_turns([], duration)


def test_load_stereo_downmix_and_select_channel(tmp_path):
    path = tmp_path / "stereo.wav"
    samples = np.column_stack((np.full(1600, 0.2), np.full(1600, -0.1)))
    sf.write(path, samples, 16000, subtype="FLOAT")
    mixed = load_audio(path)
    assert mixed.sample_rate == 16000
    assert mixed.duration == pytest.approx(0.1)
    assert mixed.samples.ndim == 1
    assert mixed.samples.dtype == np.float32
    assert mixed.samples.flags.c_contiguous
    np.testing.assert_allclose(mixed.samples, 0.05, atol=1e-7)
    np.testing.assert_allclose(load_audio(path, channel=0).samples, 0.2, atol=1e-7)
    np.testing.assert_allclose(load_audio(path, channel=1).samples, -0.1, atol=1e-7)


@pytest.mark.parametrize("channel", [-1, 2, 0.5, True, "0"])
def test_invalid_channel_rejected_cleanly(tmp_path, channel):
    path = tmp_path / "stereo.wav"
    sf.write(path, np.zeros((200, 2)), 16000)
    with pytest.raises(ValueError):
        load_audio(path, channel=channel)


@pytest.mark.parametrize("sample_rate", [8000, 44100, 48000])
def test_audio_resampled_to_sixteen_khz(tmp_path, sample_rate):
    path = tmp_path / f"tone-{sample_rate}.wav"
    t = np.arange(sample_rate) / sample_rate
    sf.write(path, 0.2 * np.sin(2 * np.pi * 400 * t), sample_rate, subtype="FLOAT")
    audio = load_audio(path)
    assert audio.sample_rate == 16000
    assert audio.samples.shape == (16000,)
    assert audio.duration == pytest.approx(1)
    assert np.isfinite(audio.samples).all()
    assert np.sqrt(np.mean(audio.samples[100:-100] ** 2)) == pytest.approx(
        0.2 / np.sqrt(2), rel=0.01
    )


def test_missing_corrupt_empty_and_nonfinite_audio_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_audio(tmp_path / "missing.wav")
    invalid = tmp_path / "invalid.wav"
    invalid.write_bytes(b"not a wave file")
    with pytest.raises(ValueError):
        load_audio(invalid)
    empty = tmp_path / "empty.wav"
    sf.write(empty, np.array([], dtype=np.float32), 16000, subtype="FLOAT")
    with pytest.raises(ValueError):
        load_audio(empty)
    nonfinite = tmp_path / "nonfinite.wav"
    sf.write(nonfinite, np.array([0, np.nan, 0]), 16000, subtype="FLOAT")
    with pytest.raises(ValueError):
        load_audio(nonfinite)
