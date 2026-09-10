"""Speaker decisions and producer-contract validation."""

import math

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.domain.speaker_identity import MatchPolicy, decide, normalize, normalize_name
from app.schemas.speaker_identity import SpeakerJobCreate, SpeakerProfilePage

pytestmark = pytest.mark.unit


def test_decision_requires_threshold_and_margin() -> None:
    policy = MatchPolicy()
    assert decide([], policy).reason == "no_profiles"
    assert decide([0.3], policy).decision == "unknown"
    assert decide([0.50, 0.2], policy).decision == "ambiguous"
    assert decide([0.7, 0.2], policy).decision == "recognized"
    assert decide([0.9, 0.85], policy).reason == "insufficient_margin"
    assert decide([0.9, 0.5], policy).decision == "recognized"


@pytest.mark.parametrize(
    ("scores", "decision", "reason"),
    [
        ([0.5499, 0.2], "ambiguous", "below_match_threshold"),
        ([0.55, 0.2], "recognized", "matched"),
        ([0.58304, 0.2], "recognized", "matched"),
        ([0.51501, 0.2], "ambiguous", "below_match_threshold"),
        ([0.58304, 0.51501], "ambiguous", "insufficient_margin"),
        ([0.55, 0.451], "ambiguous", "insufficient_margin"),
        ([0.4499, 0.2], "unknown", "below_new_threshold"),
        ([0.45, 0.2], "ambiguous", "below_match_threshold"),
    ],
)
def test_calibrated_policy_preserves_rejection_boundaries(
    scores: list[float], decision: str, reason: str
) -> None:
    result = decide(scores, MatchPolicy())
    assert result.decision == decision
    assert result.reason == reason


def test_explicit_historical_policy_remains_available() -> None:
    result = decide([0.58304, 0.2], MatchPolicy(match_threshold=0.75))
    assert result.decision == "ambiguous"
    assert result.reason == "below_match_threshold"


def test_typed_settings_and_domain_share_calibrated_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "VOICEUP_SPEAKER_MATCH_THRESHOLD",
        "VOICEUP_SPEAKER_NEW_THRESHOLD",
        "VOICEUP_SPEAKER_MATCH_MARGIN",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        _env_file=None,
        environment="test",
        jwt_secret=SecretStr("calibration-test-only-secret-at-least-32-bytes"),
    )
    actual = MatchPolicy(
        match_threshold=settings.speaker_match_threshold,
        new_threshold=settings.speaker_new_threshold,
        margin=settings.speaker_match_margin,
    )
    assert actual == MatchPolicy(match_threshold=0.55, new_threshold=0.45, margin=0.10)
    assert actual == MatchPolicy()


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


@pytest.mark.parametrize("total", [0, 50, 200])
def test_profile_listing_contract_exposes_total_without_quota(total: int) -> None:
    payload = {"items": [], "total": total, "offset": 0, "limit": 20}
    assert SpeakerProfilePage.model_validate(payload).model_dump() == payload
