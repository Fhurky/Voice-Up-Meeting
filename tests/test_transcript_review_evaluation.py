"""Post-edit scores retain every planned row and reveal damage to correct text."""

import copy
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def evaluation():
    path = Path(__file__).resolve().parents[1] / "scripts/transcript_review_evaluation.py"
    spec = importlib.util.spec_from_file_location("review_evaluation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rows():
    return [
        dict(
            reference="yeni sürümü kurduk",
            original="yeni sürüyü kurduk",
            suggested="yeni sürümü kurduk",
            completed=True,
            elapsed_seconds=2,
            edits=[dict(start_char=5, end_char=11, original="sürüyü", replacement="sürümü")],
            rejected_count=0,
        ),
        dict(
            reference="yarın görüşürüz",
            original="yarın görüşürüz",
            suggested="bugün görüşürüz",
            completed=True,
            elapsed_seconds=3,
            edits=[dict(start_char=0, end_char=5, original="yarın", replacement="bugün")],
            rejected_count=0,
        ),
        dict(
            reference="güzel hava",
            original="güzel lava",
            suggested="güzel lava",
            completed=False,
            elapsed_seconds=100,
            edits=[],
            rejected_count=0,
        ),
    ]


def test_all_rows_and_failed_requests_remain_in_paired_scores(evaluation):
    score = evaluation.summarize(rows())
    assert score["planned_rows"] == 3
    assert score["completed_rows"] == 2
    assert score["failed_rows"] == 1
    assert score["reference_words"] == 7
    assert score["raw_errors"] == score["corrected_errors"] == 2
    assert score["beneficial_edits"] == score["harmful_edits"] == 1
    assert score["edit_precision"] == 0.5
    assert score["clean_rows"] == score["damaged_clean_rows"] == 1
    assert score["clean_damage_rate"] == 1
    assert score["elapsed_seconds"] == 105


def test_punctuation_is_not_lexical_success_or_clean_damage(evaluation):
    row = dict(
        reference="İyi günler",
        original="İyi günler",
        suggested="İyi günler!",
        completed=True,
        elapsed_seconds=1,
        edits=[dict(start_char=4, end_char=10, original="günler", replacement="günler!")],
        rejected_count=0,
    )
    score = evaluation.summarize([row])
    assert score["changed_rows"] == score["damaged_clean_rows"] == 0
    assert score["edit_precision"] == 0
    assert score["neutral_edits"] == 1
    assert score["raw_wer"] == score["corrected_wer"] == 0


def test_even_latency_uses_the_two_middle_observations(evaluation):
    assert evaluation.summarize(rows()[:2])["latency_median_seconds"] == 2.5


@pytest.mark.parametrize(
    "change",
    [
        {"edits": []},
        {"suggested": "unrelated rewrite"},
        {"edits": [dict(start_char=5, end_char=11, original="sürüyü", replacement="sürümü")] * 2},
        {
            "edits": [
                dict(
                    start_char=5,
                    end_char=11,
                    original="sürüyü",
                    replacement="sürümü",
                    private="untrusted",
                )
            ]
        },
    ],
)
def test_edits_must_exactly_reconstruct_the_suggestion_without_overlap(evaluation, change):
    sample = rows()
    sample[0].update(change)
    with pytest.raises(ValueError):
        evaluation.summarize(sample)


def test_codepoint_offsets_handle_non_bmp_source(evaluation):
    sample = rows()[:1]
    row = sample[0]
    for field in ("reference", "original", "suggested"):
        row[field] = "😀 " + row[field]
    row["edits"][0].update(start_char=7, end_char=13)
    assert evaluation.summarize(sample)["beneficial_edits"] == 1


def test_total_proposed_edit_budget_and_failed_row_rejections_are_checked(evaluation):
    sample = rows()
    sample[0]["rejected_count"] = 3
    with pytest.raises(ValueError):
        evaluation.summarize(sample)
    sample = rows()
    sample[2]["rejected_count"] = 1
    with pytest.raises(ValueError):
        evaluation.summarize(sample)


def test_empty_references_and_tampered_or_nonfinite_rows_are_refused(evaluation):
    for change in (
        {"reference": ""},
        {"elapsed_seconds": float("nan")},
        {"completed": False, "suggested": "different"},
    ):
        sample = rows()
        sample[0].update(change)
        with pytest.raises(ValueError):
            evaluation.summarize(sample)


def test_summary_excludes_raw_private_content(evaluation):
    sample = rows()
    sample[0]["private_prompt"] = "PRIVATE_SECRET"
    score = evaluation.summarize(sample)
    assert "PRIVATE" not in str(score)
    assert "sürümü" not in str(score)


def test_ledger_accepts_arithmetic_checked_review_aggregates(evaluation, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "experiment_ledger", Path(__file__).resolve().parents[1] / "scripts/experiment_ledger.py"
    )
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    report = dict(
        status="complete",
        protocol="voiceup-context-review-v1",
        reference_quality="synthetic-authored",
        metrics=evaluation.summarize(rows()),
    )
    result = ledger.sanitize_result(report, "transcript_review")
    assert result["metrics"]["edit_precision"] == 0.5
    bad = copy.deepcopy(report)
    bad["metrics"]["edit_precision"] = 1
    with pytest.raises(ValueError):
        ledger.sanitize_result(bad, "transcript_review")
