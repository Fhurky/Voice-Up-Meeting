"""The private memory contract fails closed at native source-frame boundaries."""

import pytest
from pydantic import ValidationError

from app.services.meeting_memory_ports import MeetingMemoryResult, MemoryFrameRange
from app.services.meeting_ports import DiarizationIdentity, MeetingChunkResult


def test_native_ranges_reject_coercion_and_reversal() -> None:
    for values in ({"start": True, "end": 3}, {"start": 1, "end": 1}):
        with pytest.raises(ValidationError):
            MemoryFrameRange.model_validate(values)


def test_diarization_recipe_is_optional_only_for_historical_checkpoints() -> None:
    identity = {
        "model_id": "pyannote/speaker-diarization-community-1",
        "revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
    }
    assert DiarizationIdentity.model_validate(identity).recipe is None
    assert (
        DiarizationIdentity.model_validate({**identity, "recipe": "community-vbx-fa015-v1"}).recipe
        == "community-vbx-fa015-v1"
    )
    with pytest.raises(ValidationError):
        DiarizationIdentity.model_validate({**identity, "recipe": "unrecognized-recipe"})


def test_rejected_quality_cannot_carry_enrollment_evidence() -> None:
    payload = {
        "ecapa_model_id": "speechbrain/spkrec-ecapa-voxceleb",
        "ecapa_model_revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
        "input_sha256": "a" * 64,
        "retained_sha256": None,
        "input_frames": 48000,
        "sample_rate": 16000,
        "quality_version": "meeting-natural-context-v1",
        "status": "inconsistent_audio",
        "accepted_context_indices": [],
        "validated_ranges": [],
        "validated_seconds": 0.0,
        "windows_count": 0,
        "device": "cpu",
        "embedding192": None,
        "memory_embedding": None,
    }
    assert MeetingMemoryResult.model_validate(payload).status == "inconsistent_audio"
    payload["accepted_context_indices"] = [0]
    with pytest.raises(ValidationError):
        MeetingMemoryResult.model_validate(payload)


@pytest.mark.parametrize(
    "fault",
    ["model", "version", "hash", "overlap", "order", "bounds", "recipe"],
)
def test_candidate_vad_requires_exact_identity_order_source_and_recipe(fault: str) -> None:
    payload = {
        "input_seconds": 4.0,
        "sample_rate": 16000,
        "turns": [],
        "exclusive_turns": [],
        "segments": [],
        "words": [],
        "tracks": [],
        "language": None,
        "language_probability": 0.0,
        "device": "cuda:0",
        "model_identity": {
            "diarization": {
                "model_id": "pyannote/speaker-diarization-community-1",
                "revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
                "recipe": "community-vbx-fa015-v1",
            },
            "asr": {
                "model_id": "Systran/faster-whisper-large-v3",
                "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
            },
            "embedding": {
                "model_id": "speechbrain/spkrec-ecapa-voxceleb",
                "revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
                "dimensions": 192,
            },
        },
        "vad": {
            "model_id": "silero-vad",
            "model_version": "6.2.1",
            "model_sha256": "e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720",
            "ranges": [{"start": 0.0, "end": 2.0}, {"start": 2.5, "end": 4.0}],
        },
    }
    assert MeetingChunkResult.model_validate(payload).vad is not None
    if fault in {"model", "version", "hash"}:
        key = {"model": "model_id", "version": "model_version", "hash": "model_sha256"}[fault]
        payload["vad"][key] = "unrecognized"
    elif fault == "overlap":
        payload["vad"]["ranges"][1]["start"] = 1.5
    elif fault == "order":
        payload["vad"]["ranges"].reverse()
    elif fault == "bounds":
        payload["vad"]["ranges"][1]["end"] = 4.01
    else:
        payload["model_identity"]["diarization"].pop("recipe")
    with pytest.raises(ValidationError):
        MeetingChunkResult.model_validate(payload)
