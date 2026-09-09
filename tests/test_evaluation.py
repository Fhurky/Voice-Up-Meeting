"""Open-set metric definitions and malformed decision inputs."""

from copy import deepcopy

import pytest

from voiceup.evaluation import evaluate_decisions


def decision(actual, predicted=None, status="unknown", **metadata):
    return {
        "ground_truth": actual,
        "predicted_id": predicted,
        "status": status,
        **metadata,
    }


def test_open_set_metrics_count_rejections_in_known_denominator():
    records = [
        decision("a", "a", "recognized"),
        decision("b", "b", "recognized"),
        decision("a", "b", "recognized"),
        decision("b"),
        decision("c", status="ambiguous"),
        decision("c", status="new"),
        decision(None, "a", "recognized"),
        decision(None),
        decision(None, status="ambiguous"),
        decision(None, status="new"),
    ]

    report = evaluate_decisions(records)

    assert report["counts"] == {
        "total": 10,
        "known": 6,
        "unknown": 4,
        "recognized": 4,
        "correct_known": 2,
        "wrong_known": 1,
        "rejected_known": 3,
        "false_accepted_unknown": 1,
    }
    assert report["status_counts"] == {"recognized": 4, "unknown": 2, "ambiguous": 2, "new": 2}
    assert report["rates"] == {
        "DIR": 2 / 6,
        "known_misidentification": 1 / 6,
        "known_rejection": 3 / 6,
        "FPIR": 1 / 4,
    }


def test_empty_input_has_counts_and_undefined_rates():
    report = evaluate_decisions([])
    assert all(count == 0 for count in report["counts"].values())
    assert all(rate is None for rate in report["rates"].values())


def test_only_known_probes_leave_fpir_undefined():
    report = evaluate_decisions([decision("a", "a", "recognized")])
    assert report["rates"] == {
        "DIR": 1.0,
        "known_misidentification": 0.0,
        "known_rejection": 0.0,
        "FPIR": None,
    }


def test_only_unknown_probes_leave_known_rates_undefined():
    report = evaluate_decisions([decision(None), decision(None, status="new")])
    assert report["rates"] == {
        "DIR": None,
        "known_misidentification": None,
        "known_rejection": None,
        "FPIR": 0.0,
    }
    assert report["counts"]["recognized"] == 0


def test_persistent_identity_errors_are_not_remapped():
    report = evaluate_decisions(
        [decision("a", "b", "recognized"), decision("b", "a", "recognized")]
    )
    assert report["rates"]["DIR"] == 0.0
    assert report["rates"]["known_misidentification"] == 1.0


def test_duration_is_metadata_and_input_is_unchanged():
    records = [
        decision("a", "a", "recognized", duration_seconds=100, session_id="meeting-1"),
        decision("a", status="ambiguous", duration_seconds=0.1),
    ]
    before = deepcopy(records)
    report = evaluate_decisions(records)
    assert report["rates"]["DIR"] == 0.5
    assert records == before
    assert "not pairwise FAR or EER" in report["note"]


@pytest.mark.parametrize("records", [None, {}, "[]", (), 7, [None], [[]], ["record"]])
def test_invalid_container_or_record_raises_value_error(records):
    with pytest.raises(ValueError):
        evaluate_decisions(records)


@pytest.mark.parametrize("missing", ["ground_truth", "predicted_id", "status"])
def test_required_keys_cannot_be_omitted(missing):
    record = decision(None)
    del record[missing]
    with pytest.raises(ValueError, match="missing required keys"):
        evaluate_decisions([record])


@pytest.mark.parametrize("actual", ["", "  ", 0, False, [], {}])
def test_ground_truth_requires_nonempty_id_or_none(actual):
    with pytest.raises(ValueError, match="ground_truth"):
        evaluate_decisions([decision(actual)])


@pytest.mark.parametrize("status", [None, 1, True, [], {}, "", "rejected", "RECOGNIZED"])
def test_invalid_status_raises_value_error(status):
    with pytest.raises(ValueError, match="status"):
        evaluate_decisions([decision(None, status=status)])


@pytest.mark.parametrize("predicted", [None, "", "  ", 1, True, [], {}])
def test_recognized_requires_nonempty_id(predicted):
    with pytest.raises(ValueError, match="predicted_id"):
        evaluate_decisions([decision("a", predicted, "recognized")])


@pytest.mark.parametrize("status", ["unknown", "ambiguous", "new"])
@pytest.mark.parametrize("predicted", ["a", "", False, 0, []])
def test_nonrecognized_status_requires_none_prediction(status, predicted):
    with pytest.raises(ValueError, match="predicted_id must be None"):
        evaluate_decisions([decision(None, predicted, status)])


@pytest.mark.parametrize(
    "duration", [None, 0, -1, True, "3", [], float("nan"), float("inf"), -(10**400), 10**400]
)
def test_invalid_optional_duration_raises_value_error(duration):
    with pytest.raises(ValueError, match="duration_seconds"):
        evaluate_decisions([decision(None, duration_seconds=duration)])
