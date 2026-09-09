"""Speaker decisions and producer-contract validation."""

import math

import pytest
from pydantic import ValidationError

from app.domain.speaker_identity import MatchPolicy, decide, normalize, normalize_name
from app.schemas.speaker_identity import SpeakerJobCreate

pytestmark = pytest.mark.unit


def test_decision_requires_threshold_and_margin() -> None:
    policy = MatchPolicy()
    assert decide([], policy).reason == "no_profiles"
    assert decide([0.3], policy).decision == "unknown"
    assert decide([0.7, 0.2], policy).decision == "ambiguous"
    assert decide([0.9, 0.85], policy).reason == "insufficient_margin"
    assert decide([0.9, 0.5], policy).decision == "recognized"


@pytest.mark.parametrize("value", [[0.0] * 192, [math.nan] * 192, [1.0] * 191])
def test_vector_contract_rejects_invalid_data(value: list[float]) -> None:
    with pytest.raises(ValueError):
        normalize(value)


def test_normalized_names_and_vectors() -> None:
    assert normalize_name("  Test   Person  ") == "Test Person"
    vector = normalize([2.0] + [0.0] * 191)
    assert vector == [1.0] + [0.0] * 191


@pytest.mark.parametrize(
    "payload",
    [
        {"purpose": "enroll"},
        {"purpose": "identify", "name": "Person"},
        {"purpose": "enroll", "name": "   "},
        {"purpose": "enroll", "name": "Person", "profile_public_id": "x"},
    ],
)
def test_job_target_contract(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        SpeakerJobCreate(recording_public_id="e090c75f-14a9-47d4-adbb-dfba411aef71", **payload)
