"""Minimal lexical corrections preserve original source and bounded protected tokens."""

import pytest

from app.domain.transcript_correction import ProposedEdit, validate_edits


def test_small_contextual_word_replacement_preserves_source_offsets():
    original = "Yeni sürüyü sunucuya yükledik."
    result = validate_edits(original, [ProposedEdit("sürüyü", "sürümü")])
    assert result.status == "suggested"
    assert result.suggested_text == "Yeni sürümü sunucuya yükledik."
    assert result.rejected_count == 0
    edit = result.edits[0]
    assert (edit.start_char, edit.end_char) == (5, 11)
    assert original[edit.start_char : edit.end_char] == edit.original
    assert original == "Yeni sürüyü sunucuya yükledik."


def test_empty_proposals_leave_clean_text_unchanged():
    result = validate_edits("Toplantıya katılacağım.", [])
    assert result.status == "unchanged"
    assert result.edits == () and result.rejected_count == 0


@pytest.mark.parametrize(
    ("text", "original", "replacement"),
    [
        ("Bu sürüyü ve sürüyü yükledik.", "sürüyü", "sürümü"),
        ("Bu sürüyü yükledik.", "sürü", "sürüm"),
        ("Bu sürüyü yükledik.", "olmayan", "sürümü"),
        ("Yarın 15 kişi gelecek.", "15", "16"),
        ("Yarın beş kişi gelecek.", "beş", "bir"),
        ("Ali bugün geldi.", "Ali", "Veli"),
        ("Bugün Ayşe geldi.", "Ayşe", "Ayça"),
        ("Ödemeyi yapmadı.", "yapmadı", "yaptı"),
        ("O ödemedi.", "ödemedi", "ödedi"),
        ("O ödedi.", "ödedi", "ödemedi"),
        ("Bunu yapma.", "yapma", "yap"),
        ("Bunu yap.", "yap", "yapma"),
        ("O katılacak.", "katılacak", "katılmayacak"),
        ("Güzel değil.", "değil", "güzel"),
        ("Yeni sürüyü yükledik.", "sürüyü", "sürümü\u200b"),
        ("Yeni sürüyü yükledik.", "sürüyü", "sürümü\n"),
        ("Yeni sürüyü yükledik.", "sürüyü", "<script>"),
        ("Yeni sürüyü yükledik.", "sürüyü", "sunucuya başarılı biçimde"),
        ("Yeni sürüyü yükledik.", "sürüyü", "tamamen"),
        ("Yeni sürüyü yükledik.", "sürüyü", ""),
        ("Yeni sürüyü yükledik.", "sürüyü", " sürümü"),
        ("Yeni sürüyü yükledik.", "sürüyü", "sürüyü!"),
        ("Yeni sürüyü yükledik.", "sürüyü", "SÜRÜYÜ"),
    ],
)
def test_unsafe_or_ambiguous_changes_are_not_returned(text, original, replacement):
    result = validate_edits(text, [ProposedEdit(original, replacement)])
    assert result.status == "rejected"
    assert result.suggested_text == text
    assert result.edits == () and result.rejected_count == 1


def test_valid_edits_survive_separate_rejection_and_are_source_ordered():
    text = "Yeni sürüyü yükledik, 15 kişi katıldı."
    result = validate_edits(text, [ProposedEdit("15", "16"), ProposedEdit("sürüyü", "sürümü")])
    assert result.suggested_text == "Yeni sürümü yükledik, 15 kişi katıldı."
    assert len(result.edits) == 1 and result.rejected_count == 1
    assert result.status == "suggested"


def test_overlapping_proposals_are_rejected_without_double_application():
    text = "Yeni sürüyü sunucuya yükledik."
    result = validate_edits(
        text, [ProposedEdit("sürüyü", "sürümü"), ProposedEdit("sürüyü", "sürüye")]
    )
    assert result.suggested_text == text
    assert result.status == "rejected" and result.rejected_count == 2


def test_unicode_offsets_are_codepoints_not_utf16_or_normalized_coordinates():
    text = "🎧 Yeni sürüyü yükledik."
    result = validate_edits(text, [ProposedEdit("sürüyü", "sürümü")])
    assert result.edits[0].start_char == 7
    assert text[7:13] == "sürüyü"


def test_long_targets_and_excessive_proposals_fail_closed():
    assert validate_edits("x" * 1025, []).status == "rejected"
    result = validate_edits("Yeni sürüyü yükledik.", [ProposedEdit("sürüyü", "sürümü")] * 4)
    assert result.status == "rejected" and result.rejected_count == 4
