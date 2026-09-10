"""Real PCM boundaries for conservative fragmented-speech recovery."""

import numpy as np
import pytest

from voiceup.audio import Audio, Turn
from voiceup.pipeline import extract_evidence
from voiceup_inference.evidence import extract_pilot_evidence

RATE = 16000


class RecordingEmbedder:
    model_id = "deterministic-boundary-fixture"
    dimension = 3

    def __init__(self, vectors=None):
        self.chunks = []
        self.vectors = vectors

    def encode(self, samples, sample_rate=RATE):
        assert sample_rate == RATE
        self.chunks.append(samples.copy())
        if self.vectors is not None:
            return np.array(self.vectors[len(self.chunks) - 1], dtype=np.float32)
        return np.array([1.0, 0.0, 0.0], dtype=np.float32)


def fragments(durations, values=None, gap=0.4):
    values = values or [0.1] * len(durations)
    pieces, turns = [], []
    offset = 0
    for duration, value in zip(durations, values, strict=True):
        count = round(duration * RATE)
        pieces.append(np.full(count, value, dtype=np.float32))
        turns.append(Turn(offset / RATE, (offset + count) / RATE, "probe"))
        offset += count
        # An obvious sentinel proves packing never includes unvoiced gaps.
        pieces.append(np.full(round(gap * RATE), -0.75, dtype=np.float32))
        offset += len(pieces[-1])
    return Audio(np.concatenate(pieces)), turns


@pytest.mark.parametrize(
    "purpose,durations,expected_windows",
    [
        ("enroll", [2.0] * 5, 2),
        ("enroll", [2.0] * 10, 3),
        ("identify", [1.5, 1.5], 1),
    ],
)
def test_fragmented_real_samples_recover_without_silence_or_repetition(
    purpose, durations, expected_windows
):
    values = [0.01 * (index + 1) for index in range(len(durations))]
    audio, turns = fragments(durations, values)
    embedder = RecordingEmbedder()
    result, version = extract_pilot_evidence(audio, turns, embedder, purpose)
    assert result.reason == "usable"
    assert result.used_seconds == pytest.approx(sum(durations))
    assert result.clean_seconds == pytest.approx(sum(durations))
    assert result.windows == expected_windows
    assert version == "vad-packed-fallback-v1"
    evidence_chunks = embedder.chunks[-expected_windows:]
    actual = np.concatenate(evidence_chunks)
    expected = np.concatenate(
        [
            np.full(round(duration * RATE), value, dtype=np.float32)
            for duration, value in zip(durations, values, strict=True)
        ]
    )
    np.testing.assert_array_equal(actual, expected)
    assert all(3 * RATE <= len(chunk) <= 8 * RATE for chunk in evidence_chunks)
    assert np.linalg.norm(result.embedding) == pytest.approx(1)


@pytest.mark.parametrize("purpose,seconds", [("enroll", 12), ("identify", 4)])
def test_sufficient_continuous_evidence_is_preserved_exactly(purpose, seconds):
    audio, turns = fragments([seconds, 1, 1, 1])
    expected = extract_evidence(audio, turns, "probe", RecordingEmbedder())
    embedder = RecordingEmbedder()
    actual, version = extract_pilot_evidence(audio, turns, embedder, purpose)
    np.testing.assert_array_equal(actual.embedding, expected.embedding)
    assert (actual.clean_seconds, actual.used_seconds, actual.windows, actual.consistency) == (
        expected.clean_seconds,
        expected.used_seconds,
        expected.windows,
        expected.consistency,
    )
    assert sum(len(chunk) for chunk in embedder.chunks) == seconds * RATE
    assert version == "vad-windows-v1"


def test_existing_inconsistency_is_never_retried_by_packing():
    audio, turns = fragments([4, 4, 2, 2])
    embedder = RecordingEmbedder([[1, 0, 0], [0, 1, 0]])
    result, version = extract_pilot_evidence(audio, turns, embedder, "enroll")
    assert result.embedding is None
    assert result.reason == "inconsistent_voice_windows"
    assert len(embedder.chunks) == 2
    assert version == "vad-windows-v1"


def test_recovered_windows_must_agree_with_partial_original_voice():
    audio, turns = fragments([4, 2, 2, 2])
    embedder = RecordingEmbedder([[1, 0, 0]] + [[0, 1, 0]] * 6)
    result, version = extract_pilot_evidence(audio, turns, embedder, "enroll")
    assert result.embedding is None
    assert result.reason == "inconsistent_voice_windows"
    assert result.consistency == pytest.approx(0)
    assert version == "vad-packed-fallback-v1"


def test_inconsistent_recovered_windows_are_rejected():
    audio, turns = fragments([2] * 5)
    result, _ = extract_pilot_evidence(
        audio, turns, RecordingEmbedder([[1, 0, 0]] * 6 + [[0, 1, 0]]), "enroll"
    )
    assert result.embedding is None
    assert result.reason == "inconsistent_voice_windows"


@pytest.mark.parametrize(
    "purpose,durations",
    [
        ("identify", [1.0, 1.0, 1.0 - 1 / RATE]),
        ("enroll", [2.0, 2.0, 2.0, 2.0, 2.0 - 1 / RATE]),
        ("enroll", [9.0]),
    ],
)
def test_insufficient_total_samples_are_not_manufactured(purpose, durations):
    audio, turns = fragments(durations, gap=2)
    result, _ = extract_pilot_evidence(audio, turns, RecordingEmbedder(), purpose)
    minimum = 10 if purpose == "enroll" else 3
    assert result.embedding is None or result.used_seconds < minimum


@pytest.mark.parametrize("invalid_value", [0.0, 1e-5, 1.0, float("nan")])
def test_unusable_fragments_cannot_inflate_usable_speech(invalid_value):
    audio, turns = fragments([2] * 6, [invalid_value] * 5 + [0.1])
    embedder = RecordingEmbedder()
    result, _ = extract_pilot_evidence(audio, turns, embedder, "enroll")
    assert result.embedding is None
    assert result.used_seconds < 10
    assert not embedder.chunks


def test_quiet_long_window_cannot_be_diluted_by_short_valid_fragments():
    audio, turns = fragments([8, 2, 2], [0.0, 0.1, 0.1])
    result, _ = extract_pilot_evidence(audio, turns, RecordingEmbedder(), "enroll")
    assert result.embedding is None


def test_overlapping_spans_do_not_duplicate_samples_or_other_speaker_regions():
    audio, turns = fragments([2] * 6, gap=1)
    turns += [turns[0], Turn(turns[1].start, turns[1].end, "other")]
    embedder = RecordingEmbedder()
    result, _ = extract_pilot_evidence(audio, turns, embedder, "enroll")
    assert result.used_seconds == pytest.approx(10)
    assert sum(len(chunk) for chunk in embedder.chunks[-result.windows :]) == 10 * RATE


def test_no_speech_stays_unusable():
    audio = Audio(np.zeros(12 * RATE, dtype=np.float32))
    embedder = RecordingEmbedder()
    result, _ = extract_pilot_evidence(audio, [], embedder, "enroll")
    assert result.embedding is None and result.used_seconds == 0
    assert not embedder.chunks


class VoiceMixEmbedder(RecordingEmbedder):
    def encode(self, samples, sample_rate=RATE):
        self.chunks.append(samples.copy())
        # Two different original voices become a similar blend in every packed
        # window; checking packed windows alone misses the mixed enrollment.
        voice_a = float(np.mean(samples < 0.15))
        return np.array([voice_a, 1 - voice_a, 0], dtype=np.float32)


def test_alternating_short_voices_cannot_become_a_consistent_blended_profile():
    audio, turns = fragments([2] * 8, [0.1, 0.2] * 4)
    result, _ = extract_pilot_evidence(audio, turns, VoiceMixEmbedder(), "enroll")
    assert result.embedding is None
    assert result.reason == "inconsistent_voice_windows"


@pytest.mark.parametrize(
    "purpose,durations",
    [
        ("identify", [1.4] * 3),
        ("enroll", [1.4] * 8),
        ("enroll", [2] * 4 + [1.4] * 2),
    ],
)
def test_blocks_too_short_for_identity_guard_cannot_inflate_recovery(purpose, durations):
    audio, turns = fragments(durations)
    result, version = extract_pilot_evidence(audio, turns, RecordingEmbedder(), purpose)
    assert result.embedding is None
    assert version == "vad-windows-v1"


def test_consistent_guard_vectors_must_agree_with_packed_evidence():
    audio, turns = fragments([2] * 5)
    embedder = RecordingEmbedder([[1, 0, 0]] * 5 + [[0, 1, 0]] * 2)
    result, _ = extract_pilot_evidence(audio, turns, embedder, "enroll")
    assert result.embedding is None
    assert result.reason == "inconsistent_voice_windows"
    assert result.consistency == pytest.approx(0)


@pytest.mark.parametrize("invalid", [[0, 0, 0], [float("nan"), 0, 0], [1, 0]])
def test_invalid_original_guard_vectors_fail_closed(invalid):
    audio, turns = fragments([2] * 5)
    with pytest.raises(ValueError):
        extract_pilot_evidence(audio, turns, RecordingEmbedder([invalid]), "enroll")


def test_maximum_pilot_duration_remains_bounded():
    audio, turns = fragments([2.7] * 40, gap=0.3)
    embedder = RecordingEmbedder()
    result, _ = extract_pilot_evidence(audio, turns, embedder, "enroll")
    assert audio.duration == 120
    assert result.used_seconds == pytest.approx(108)
    assert result.windows <= 20
    assert len(embedder.chunks) <= 100
    assert all(1.5 * RATE <= len(chunk) <= 8 * RATE for chunk in embedder.chunks)
    assert all(3 * RATE <= len(chunk) <= 8 * RATE for chunk in embedder.chunks[-result.windows :])
