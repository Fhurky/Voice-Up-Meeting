"""Original clean regions, not stitched durations, authorize meeting voice evidence."""

import numpy as np
import pytest

from voiceup.audio import Audio, Turn
from voiceup_inference.meeting_evidence import extract_track_evidence


class AmplitudeEmbedder:
    dimension = 192

    def encode(self, samples, sample_rate=16000):
        vector = np.zeros(self.dimension, dtype=np.float32)
        vector[0 if float(np.mean(samples)) < 0.15 else 1] = 1.0
        return vector


def test_continuous_and_separated_clean_speech_returns_validated_ranges():
    audio = Audio(np.full(16 * 16000, 0.1, dtype=np.float32))
    result = extract_track_evidence(
        audio, [Turn(0, 16, "A")], "A", [(1, 8), (10, 15)], AmplitudeEmbedder()
    )
    assert result["status"] == "usable"
    assert result["validated_ranges"] == [{"start": 1.0, "end": 8.0}, {"start": 10.0, "end": 15.0}]
    assert result["validated_seconds"] == 12
    assert result["dimensions"] == 192
    assert np.linalg.norm(result["embedding"]) == pytest.approx(1.0)


def test_other_speaker_overlap_never_enters_eligible_ranges():
    audio = Audio(np.full(10 * 16000, 0.1, dtype=np.float32))
    turns = [Turn(0, 7, "A"), Turn(4, 10, "B")]
    result = extract_track_evidence(audio, turns, "A", [(0, 10)], AmplitudeEmbedder())
    assert result["validated_ranges"] == [{"start": 0.0, "end": 4.0}]
    assert result["validated_seconds"] == 4


def test_baseline_success_cannot_hide_a_conflicting_short_original_region():
    samples = np.full(10 * 16000, 0.1, dtype=np.float32)
    samples[8 * 16000 :] = 0.2
    result = extract_track_evidence(
        Audio(samples), [Turn(0, 10, "A")], "A", [(0, 6), (8, 10)], AmplitudeEmbedder()
    )
    assert result["status"] == "inconsistent_audio"
    assert result["embedding"] is None
    assert result["validated_ranges"] == []
    assert result["validated_seconds"] == 0


def test_tiny_fragments_do_not_become_profile_evidence_by_joining():
    audio = Audio(np.full(9 * 16000, 0.1, dtype=np.float32))
    spans = [(0, 1), (2, 3), (4, 5), (6, 7)]
    result = extract_track_evidence(audio, [Turn(0, 9, "A")], "A", spans, AmplitudeEmbedder())
    assert result["status"] == "insufficient_speech"
    assert result["embedding"] is None
    assert result["validated_ranges"] == []


def test_quiet_and_gap_regions_never_count_toward_validated_duration():
    samples = np.zeros(10 * 16000, dtype=np.float32)
    samples[: 4 * 16000] = 0.1
    result = extract_track_evidence(
        Audio(samples), [Turn(0, 10, "A")], "A", [(0, 4), (6, 10)], AmplitudeEmbedder()
    )
    assert result["validated_ranges"] == [{"start": 0.0, "end": 4.0}]
    assert result["validated_seconds"] == 4


def test_missing_speech_abstains_without_changing_transcript_turns():
    audio = Audio(np.zeros(5 * 16000, dtype=np.float32))
    turns = [Turn(1, 4, "A")]
    result = extract_track_evidence(audio, turns, "A", [], AmplitudeEmbedder())
    assert result["status"] == "insufficient_speech"
    assert turns == [Turn(1, 4, "A")]


def test_fractional_turn_boundaries_never_round_evidence_outside_the_turn():
    audio = Audio(np.full(10 * 16000, 0.1, dtype=np.float32))
    turn = Turn(3.00003125, 7.00003125, "A")
    result = extract_track_evidence(
        audio, [turn], "A", [(turn.start, turn.end)], AmplitudeEmbedder()
    )
    assert result["status"] == "usable"
    interval = result["validated_ranges"][0]
    assert turn.start <= interval["start"] < interval["end"] <= turn.end
    assert result["validated_seconds"] == pytest.approx(interval["end"] - interval["start"])
