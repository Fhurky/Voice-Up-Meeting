"""All bounded model suggestions remain visible while source mapping stays deterministic."""

import json

import pytest

from app.domain.transcript_suggestions import project_model_output


def output(*pairs):
    return json.dumps(
        {"edits": [{"original": old, "replacement": new} for old, new in pairs]}, ensure_ascii=False
    )


def test_semantic_rejection_remains_visible_and_saveable():
    text = "Ali 15 kişi için ödeme yapmadı."
    result = project_model_output(text, output(("15", "16"), ("yapmadı", "yaptı")))
    assert result.status == "suggested" and result.saveable
    assert result.suggested_text == "Ali 16 kişi için ödeme yaptı."
    assert len(result.proposals) == 2
    assert all(proposal.assessment == "review_required" for proposal in result.proposals)


def test_checked_change_has_unicode_codepoint_coordinates():
    result = project_model_output("🎧 Yeni sürüyü yükledik.", output(("sürüyü", "sürümü")))
    assert result.proposals[0].start_char == 7
    assert result.proposals[0].end_char == 13
    assert result.proposals[0].assessment == "checked"
    assert result.proposals[0].reason is None


@pytest.mark.parametrize(
    "text,pairs,reason",
    [
        ("ses ses", [("ses", "söz")], "ambiguous_source"),
        ("ses geldi", [("yok", "var")], "source_not_found"),
        ("ses geldi", [("ses", "söz"), ("ses geldi", "söz geldi")], "overlapping_edits"),
        ("ses geldi", [("ses", "söz\u200b")], "unsupported_characters"),
    ],
)
def test_unmapped_changes_are_visible_without_invented_offsets_or_save(text, pairs, reason):
    result = project_model_output(text, output(*pairs))
    assert result.status == "unmapped" and not result.saveable
    assert len(result.proposals) == len(pairs)
    assert all(proposal.reason == reason for proposal in result.proposals)
    assert all(
        proposal.start_char is None and proposal.end_char is None for proposal in result.proposals
    )


def test_one_unmapped_proposal_does_not_hide_other_inline_change():
    result = project_model_output(
        "Yeni sürüyü yükledik.", output(("sürüyü", "sürümü"), ("yok", "var"))
    )
    assert result.suggested_text == "Yeni sürümü yükledik."
    assert result.status == "unmapped" and not result.saveable
    assert len(result.proposals) == 2


@pytest.mark.parametrize(
    "raw",
    [
        "Plain model response",
        "{}",
        '{"edits":[],"edits":[]}',
        '{"edits":[],"bad":NaN}',
        '{"edits":[{"original":"x","replacement":""}]}',
    ],
)
def test_invalid_json_shape_is_distinct_from_no_changes(raw):
    result = project_model_output("Some text", raw)
    assert result.status == "invalid_output" and not result.saveable
    assert result.suggested_text == "Some text" and result.proposals == ()


def test_empty_or_identity_proposals_never_create_a_save_receipt():
    assert project_model_output("ses", output()).status == "unchanged"
    result = project_model_output("ses", output(("ses", "ses")))
    assert result.status == "unchanged" and not result.saveable
    assert len(result.proposals) == 1


def test_truncated_but_parseable_output_cannot_be_saved():
    result = project_model_output("ses", output(("ses", "söz")), truncated=True)
    assert result.status == "invalid_output" and not result.saveable
    assert len(result.proposals) == 1


def test_html_is_plain_bounded_model_text_and_never_executed_by_domain():
    result = project_model_output("ses geldi", output(("ses", "<b>ses</b>")))
    assert result.suggested_text == "<b>ses</b> geldi"
    assert result.proposals[0].assessment == "review_required"


def test_long_input_and_excessive_proposals_fail_without_hidden_partial_save():
    assert project_model_output("x" * 1025, output()).status == "invalid_output"
    assert (
        project_model_output(
            "a b c d", output(("a", "aa"), ("b", "bb"), ("c", "cc"), ("d", "dd"))
        ).status
        == "invalid_output"
    )
