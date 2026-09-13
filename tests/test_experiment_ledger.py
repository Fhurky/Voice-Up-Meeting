"""Experiment history is atomic, idempotent and contains only public aggregates."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ledger():
    spec = importlib.util.spec_from_file_location(
        "experiment_ledger", ROOT / "scripts" / "experiment_ledger.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata():
    return {
        "date": "2026-09-13",
        "dataset": "public-corpus",
        "dataset_revision": "revision-1",
        "language": "tr",
        "role": "regression",
        "pipeline": "meeting-asr",
    }


def transcript():
    cost = {"errors": 1, "substitutions": 0, "deletions": 1, "insertions": 0, "rate": 0.5}
    return {
        "schema_version": 1,
        "normalization": "turkish-words-v1",
        "source_sha256": "a" * 64,
        "input_sha256": "b" * 64,
        "counts": {
            "reference_speakers": 1,
            "hypothesis_speakers": 1,
            "reference_words": 2,
            "hypothesis_words": 1,
            "unassigned_words": 0,
        },
        "cpwer": cost.copy(),
        "assigned_only": cost.copy(),
        "unassigned_word_fraction": 0,
    }


def append(module, path, report=None, **kwargs):
    return module.record_experiment(
        path,
        experiment_id="tr-baseline-001",
        metadata=metadata(),
        report=transcript() if report is None else report,
        kind="transcript",
        **kwargs,
    )


def test_real_file_history_preserves_manual_text_and_exact_replay_is_noop(ledger, tmp_path):
    path = tmp_path / "results.md"
    manual = "# Deneyler\n\nElle yazılan açıklama.\n"
    path.write_text(manual, encoding="utf-8")
    assert append(ledger, path)
    before = path.read_bytes()
    assert not append(ledger, path)
    assert path.read_bytes() == before
    assert path.read_text(encoding="utf-8").startswith(manual)
    assert len(ledger.read_snapshots(path)) == 1
    assert "50.00%" in path.read_text(encoding="utf-8")


def test_incomplete_then_complete_are_same_experiment_with_separate_revisions(ledger, tmp_path):
    path = tmp_path / "results.md"
    assert append(ledger, path, {"status": "incomplete", "error_code": "private error"})
    assert append(ledger, path)
    values = ledger.read_snapshots(path)
    assert [row["revision"] for row in values] == [1, 2]
    assert {row["experiment_id"] for row in values} == {"tr-baseline-001"}
    assert values[0]["result"]["metrics"] is None
    assert "private error" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("state", ["failed", "incomplete", "unscored"])
def test_noncomplete_report_never_publishes_supplied_scores(ledger, tmp_path, state):
    path = tmp_path / "results.md"
    append(ledger, path, transcript() | {"status": state})
    row = ledger.read_snapshots(path)[0]
    assert row["result"]["metrics"] is None
    assert row["result"]["status"] == state


def test_raw_report_fields_and_assignments_are_never_published(ledger, tmp_path):
    path = tmp_path / "results.md"
    report = transcript() | {
        "password": "PRIVATE_PASSWORD",
        "tenant_id": "PRIVATE_TENANT",
        "text": "PRIVATE_TRANSCRIPT",
        "token": "PRIVATE_TOKEN",
    }
    report["cpwer"]["assignment"] = [{"reference_speaker": "PRIVATE_PERSON"}]
    append(ledger, path, report)
    assert "PRIVATE_" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "change",
    [
        {"tenant_id": "private"},
        {"date": "2026-02-30"},
        {"role": "blind-success"},
        {"dataset": "https://host/?token=private"},
        {"dataset": "<script>bad</script>"},
        {"dataset_revision": "ghp_" + "x" * 40},
        {"elapsed_seconds": float("nan")},
        {"models": [{"id": "model", "revision": "one", "token": "private"}]},
    ],
)
def test_unsafe_metadata_is_rejected_before_any_write(ledger, tmp_path, change):
    path = tmp_path / "results.md"
    with pytest.raises(ValueError):
        ledger.record_experiment(
            path,
            experiment_id="run-1",
            metadata=metadata() | change,
            report=transcript(),
            kind="transcript",
        )
    assert not path.exists()


@pytest.mark.parametrize("field,value", [("errors", -1), ("rate", float("nan")), ("rate", 0.75)])
def test_inconsistent_or_invalid_metric_is_not_published(ledger, tmp_path, field, value):
    report = transcript()
    report["cpwer"][field] = value
    with pytest.raises(ValueError):
        append(ledger, tmp_path / "results.md", report)


def test_held_lock_fails_closed_without_modification(ledger, tmp_path):
    path = tmp_path / "results.md"
    path.write_text("preserved")
    lock = path.with_name(path.name + ".lock")
    lock.write_text("another writer")
    with pytest.raises(ValueError, match="ledger_locked"):
        append(ledger, path)
    assert path.read_text() == "preserved"
    assert lock.read_text() == "another writer"


def test_replace_failure_preserves_history_and_releases_only_own_lock(
    ledger, tmp_path, monkeypatch
):
    path = tmp_path / "results.md"
    path.write_text("preserved")

    def fail(*args):
        raise OSError("disk write failed")

    monkeypatch.setattr(ledger.os, "replace", fail)
    with pytest.raises(OSError):
        append(ledger, path)
    assert path.read_text() == "preserved"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["results.md"]


def test_tampered_machine_block_is_not_silently_rewritten(ledger, tmp_path):
    path = tmp_path / "results.md"
    append(ledger, path)
    content = path.read_text(encoding="utf-8").replace('"reference_words":2', '"reference_words":3')
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        append(ledger, path, {"status": "incomplete"})
    assert path.read_text(encoding="utf-8") == content


def test_metadata_file_helper_uses_only_validated_public_contract(ledger, tmp_path):
    path, meta = tmp_path / "results.md", tmp_path / "metadata.json"
    meta.write_text(json.dumps(metadata() | {"experiment_id": "tr-001"}))
    assert ledger.record_from_metadata_file(path, meta, report=transcript(), kind="transcript")
    assert ledger.read_snapshots(path)[0]["experiment_id"] == "tr-001"


def test_earlier_v1_snapshot_without_optional_full_record_seal_still_accepts_append(
    ledger, tmp_path
):
    path = tmp_path / "results.md"
    append(ledger, path)
    content = path.read_text(encoding="utf-8")
    row = ledger.read_snapshots(path)[0]
    unsealed = {key: value for key, value in row.items() if key != "record_sha256"}
    path.write_text(
        content.replace(ledger.canonical(row), ledger.canonical(unsealed)), encoding="utf-8"
    )
    before = path.read_bytes()
    assert not append(ledger, path)
    assert path.read_bytes() == before
    assert append(ledger, path, {"status": "incomplete"})
    assert len(ledger.read_snapshots(path)) == 2


def test_historical_identity_all_planned_denominators_are_preserved(ledger, tmp_path):
    report = json.loads(
        (ROOT / "docs/evidence/2026-09-09-speaker-metrics/fresh-summary.json").read_text()
    )
    path = tmp_path / "results.md"
    ledger.record_experiment(
        path,
        experiment_id="historical-identity-1",
        metadata=metadata() | {"language": "en", "pipeline": "speaker-pilot"},
        report=report,
        kind="identity",
    )
    stage = ledger.read_snapshots(path)[0]["result"]["metrics"]["stages"][0]
    assert stage["support"]["known_probes"] == 150
    assert stage["gallery_size_planned"] == 50
    assert stage["gallery_size_enrolled"] == 40
    assert stage["identity"]["recall"] == 116 / 150
    assert stage["voiceup_score"] == pytest.approx(82.49305990865945)
    changed = copy.deepcopy(report)
    changed["source_run_complete"] = False
    ledger.record_experiment(
        path,
        experiment_id="historical-identity-2",
        metadata=metadata() | {"language": "en", "pipeline": "speaker-pilot"},
        report=changed,
        kind="identity",
    )
    assert ledger.read_snapshots(path)[1]["result"]["metrics"] is None


def test_meeting_coverage_distinguishes_first_appearance_from_later_enrollment(ledger):
    source = {
        "identity": {
            "true_positive": 3,
            "false_positive": 0,
            "false_negative": 3,
            "precision": 1,
            "recall": 0.5,
            "micro_f1": 2 / 3,
            "macro_f1": 0.5,
        },
        "unknown": {
            "true_positive": 4,
            "false_positive": 2,
            "false_negative": 2,
            "precision": 2 / 3,
            "recall": 2 / 3,
            "f1": 2 / 3,
        },
        "voiceup_score": 400 / 7,
        "enrollment_coverage": 1,
        "first_enrollment_coverage": 2 / 3,
        "decision_coverage": 0.75,
        "protocol_sha256": "a" * 64,
        "planned_meetings": 6,
        "observed_meetings": 6,
        "support": {
            "known_probes": 6,
            "unknown_probes": 6,
            "known_speakers": 4,
            "unique_speakers": 6,
            "observed_probes": 12,
            "planned_probes": 12,
        },
        "meetings": [{"source_sha256": "a" * 64, "transcript_metrics": None} for _ in range(6)],
    }
    result = ledger.meeting_identity_metrics(source)
    assert result["cumulative_enrollment_coverage"] == 1
    assert result["first_enrollment_coverage"] == 2 / 3
    assert "enrollment_coverage" not in result
    source["first_enrollment_coverage"] = 1
    with pytest.raises(ValueError, match="metric_arithmetic_mismatch"):
        ledger.meeting_identity_metrics(source)


@pytest.mark.parametrize("hint", [True, False, 1, "true", None])
def test_meeting_hint_setting_is_explicit_and_strictly_boolean(ledger, tmp_path, hint):
    report = {
        "metrics_protocol": "voiceup-real-turnturk-v1",
        "reference_quality": "automatic-activity-unverified-text-diagnostic",
        "language": "tr",
        "status": "running",
        "planned_meetings": 6,
        "observed_meetings": 0,
        "use_known_speaker_count": hint,
    }
    path = tmp_path / "results.md"
    if type(hint) is not bool:
        with pytest.raises(ValueError, match="invalid_speaker_count_hint"):
            ledger.record_experiment(
                path,
                experiment_id="hint-1",
                metadata=metadata() | {"pipeline": "meeting-memory"},
                report=report,
                kind="meeting_identity",
            )
        assert not path.exists()
        return
    ledger.record_experiment(
        path,
        experiment_id="hint-1",
        metadata=metadata() | {"pipeline": "meeting-memory"},
        report=report,
        kind="meeting_identity",
    )
    assert ledger.read_snapshots(path)[0]["result"]["use_known_speaker_count"] is hint
    visible = path.read_text(encoding="utf-8")
    assert ("expected_speakers=2" if hint else "kişi sayısı ipucu verilmedi") in visible


def test_turkish_normalization_cannot_be_labeled_english(ledger, tmp_path):
    with pytest.raises(ValueError, match="normalization_language_mismatch"):
        ledger.record_experiment(
            tmp_path / "results.md",
            experiment_id="run-1",
            metadata=metadata() | {"language": "en"},
            report=transcript(),
            kind="transcript",
        )


def test_asr_clips_report_word_error_without_invented_speaker_counts(ledger, tmp_path):
    report = {
        "protocol": "voiceup-mediaspeech-tr-v1",
        "status": "complete",
        "normalization": "turkish-words-v1",
        "planned_clips": 2,
        "observed_clips": 2,
        "reference_words": 2,
        "hypothesis_words": 5,
        "errors": 3,
        "substitutions": 0,
        "deletions": 0,
        "insertions": 3,
        "wer": 1.5,
    }
    path = tmp_path / "results.md"
    ledger.record_experiment(
        path, experiment_id="asr-1", metadata=metadata(), report=report, kind="asr_clips"
    )
    row = ledger.read_snapshots(path)[0]
    assert row["result"]["metrics"]["wer"] == 1.5
    assert "150.00%" in path.read_text(encoding="utf-8")
    assert "reference_speakers" not in path.read_text(encoding="utf-8")
    report["observed_clips"] = 1
    with pytest.raises(ValueError, match="incomplete_asr_clips"):
        ledger.record_experiment(
            path, experiment_id="asr-1", metadata=metadata(), report=report, kind="asr_clips"
        )


@pytest.mark.parametrize(
    "protocol", ["voiceup-mediaspeech-tr-expanded-v1", "voiceup-fleurs-tr-test-v1"]
)
def test_expanded_asr_protocols_retain_coverage_without_private_rows(ledger, tmp_path, protocol):
    report = {
        "protocol": protocol,
        "status": "incomplete",
        "normalization": "turkish-words-v1",
        "planned_clips": 743,
        "observed_clips": 1,
        "reference_words": 10,
        "hypothesis_words": 9,
        "errors": 1,
        "substitutions": 0,
        "deletions": 1,
        "insertions": 0,
        "wer": None,
        "clips": [{"reference": "PRIVATE_REFERENCE", "hypothesis": "PRIVATE_TEXT"}],
    }
    path = tmp_path / "results.md"
    ledger.record_experiment(
        path, experiment_id="expanded-1", metadata=metadata(), report=report, kind="asr_clips"
    )
    snapshot = ledger.read_snapshots(path)[0]
    assert snapshot["result"]["coverage"] == {"planned_clips": 743, "observed_clips": 1}
    assert snapshot["result"]["metrics"] is None
    assert snapshot["result"]["protocol"] == protocol
    visible = path.read_text(encoding="utf-8")
    assert "Klip 1/743" in visible
    assert "PRIVATE_" not in visible
    report.update(status="complete", observed_clips=743, wer=0.1)
    ledger.record_experiment(
        path, experiment_id="expanded-1", metadata=metadata(), report=report, kind="asr_clips"
    )
    latest = ledger.read_snapshots(path)[1]
    assert latest["result"]["metrics"]["wer"] == 0.1
    assert latest["revision"] == 2


@pytest.mark.parametrize("observed", [-1, 744, True])
def test_asr_incomplete_coverage_must_fit_plan(ledger, observed):
    with pytest.raises(ValueError):
        ledger.sanitize_result(
            {
                "status": "incomplete",
                "protocol": "voiceup-fleurs-tr-test-v1",
                "normalization": "turkish-words-v1",
                "planned_clips": 743,
                "observed_clips": observed,
            },
            "asr_clips",
        )


def test_unadmitted_asr_protocol_is_rejected_even_when_incomplete(ledger):
    with pytest.raises(ValueError, match="invalid_asr_protocol"):
        ledger.sanitize_result(
            {
                "status": "incomplete",
                "protocol": "arbitrary-corpus",
                "normalization": "turkish-words-v1",
                "planned_clips": 1,
                "observed_clips": 0,
            },
            "asr_clips",
        )


@pytest.mark.parametrize("start", [300, 600])
def test_new_meeting_windows_are_visible_and_bound_to_fixed_scope(ledger, tmp_path, start):
    report = {
        "status": "incomplete",
        "metrics_protocol": "voiceup-real-turnturk-v1",
        "reference_quality": "automatic-activity-unverified-text-diagnostic",
        "language": "tr",
        "planned_meetings": 6,
        "observed_meetings": 2,
        "source_protocol_id": f"voiceup-real-turnturk-window{start}-v1",
        "selection": {"start_seconds": start, "duration_seconds": 300},
        "planned_audio_seconds": 1800,
        "observed_audio_seconds": 600,
        "source_sessions": 6,
    }
    path = tmp_path / "results.md"
    ledger.record_experiment(
        path, experiment_id="window-1", metadata=metadata(), report=report, kind="meeting_identity"
    )
    result = ledger.read_snapshots(path)[0]["result"]
    assert result["selection"] == report["selection"]
    assert result["observed_audio_seconds"] == 600
    assert f"[{start},{start + 300})" in path.read_text(encoding="utf-8")
    report["selection"]["start_seconds"] = 0
    with pytest.raises(ValueError, match="invalid_meeting_window"):
        ledger.sanitize_result(report, "meeting_identity")


def test_new_meeting_window_cannot_claim_more_audio_than_observed(ledger):
    with pytest.raises(ValueError, match="invalid_meeting_window"):
        ledger.sanitize_result(
            {
                "status": "incomplete",
                "metrics_protocol": "voiceup-real-turnturk-v1",
                "reference_quality": "automatic-activity-unverified-text-diagnostic",
                "language": "tr",
                "planned_meetings": 6,
                "observed_meetings": 2,
                "source_protocol_id": "voiceup-real-turnturk-window300-v1",
                "selection": {"start_seconds": 300, "duration_seconds": 300},
                "planned_audio_seconds": 1800,
                "observed_audio_seconds": 1800,
                "source_sessions": 6,
            },
            "meeting_identity",
        )


def test_meeting_identity_retains_weak_reference_scope_and_private_names_are_removed(
    ledger, tmp_path
):
    report = {
        "metrics_protocol": "voiceup-real-turnturk-v1",
        "reference_quality": "automatic-activity-unverified-text-diagnostic",
        "language": "tr",
        "status": "complete",
        "protocol_sha256": "c" * 64,
        "planned_meetings": 6,
        "observed_meetings": 6,
        "support": {
            "known_probes": 6,
            "unknown_probes": 6,
            "known_speakers": 4,
            "unique_speakers": 6,
            "observed_probes": 12,
            "planned_probes": 12,
        },
        "identity": {
            "true_positive": 6,
            "false_positive": 0,
            "false_negative": 0,
            "precision": 1,
            "recall": 1,
            "micro_f1": 1,
            "macro_f1": 1,
        },
        "unknown": {
            "true_positive": 6,
            "false_positive": 0,
            "false_negative": 0,
            "precision": 1,
            "recall": 1,
            "f1": 1,
        },
        "voiceup_score": 100,
        "enrollment_coverage": 1,
        "decision_coverage": 1,
        "meetings": [
            {
                "case": "PRIVATE_PERSON",
                "source_sha256": "a" * 64,
                "transcript_metrics": transcript(),
            }
            for _ in range(6)
        ],
    }
    path = tmp_path / "results.md"
    ledger.record_experiment(
        path,
        experiment_id="meeting-1",
        metadata=metadata() | {"pipeline": "meeting-memory"},
        report=report,
        kind="meeting_identity",
    )
    assert "Zayıf otomatik referans" in path.read_text(encoding="utf-8")
    visible = path.read_text(encoding="utf-8")
    assert visible.index("Zayıf otomatik referans") < visible.index("| Precision |")
    assert "metin referansı ve zaman damgaları insan doğrulamasıyla" in visible
    assert "cumulative_enrollment_coverage" in visible
    assert "İlk kayıt kapsamı: 100.00%" not in visible
    assert "PRIVATE_PERSON" not in path.read_text(encoding="utf-8")
    report["status"] = "running"
    report["observed_meetings"] = 3
    ledger.record_experiment(
        path,
        experiment_id="meeting-1",
        metadata=metadata() | {"pipeline": "meeting-memory"},
        report=report,
        kind="meeting_identity",
    )
    assert ledger.read_snapshots(path)[1]["result"]["metrics"] is None


def test_historical_backfill_cli_includes_rejected_candidates_and_is_idempotent(ledger, tmp_path):
    path = tmp_path / "results.md"
    command = [
        sys.executable,
        str(ROOT / "scripts/record-experiment.py"),
        "--backfill-reviewed-history",
        "--results-md",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert len(ledger.read_snapshots(path)) == 13
    assert "rejected-fullcoverage-clips-v1" in path.read_text(encoding="utf-8")
    assert "rejected-targeted-native-anomaly-v2" in path.read_text(encoding="utf-8")
    assert "turkish-single-speaker-smoke" in path.read_text(encoding="utf-8")
    before = path.read_bytes()
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "added: 0" in result.stdout
    assert path.read_bytes() == before


def test_standalone_cli_records_aggregate_and_existing_source_remains_unchanged(ledger, tmp_path):
    source, meta, path = (
        tmp_path / "report.json",
        tmp_path / "metadata.json",
        tmp_path / "results.md",
    )
    source.write_text(json.dumps(transcript()))
    meta.write_text(json.dumps(metadata() | {"experiment_id": "cli-1"}))
    before = source.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/record-experiment.py"),
            "--input",
            str(source),
            "--experiment-metadata",
            str(meta),
            "--kind",
            "transcript",
            "--results-md",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert len(ledger.read_snapshots(path)) == 1
    assert source.read_bytes() == before


def test_canonical_identity_report_cli_logs_validated_aggregate(ledger, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "metric_fixtures", ROOT / "tests/test_public_speaker_metrics.py"
    )
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    source, manifest = fixtures.fixture()
    # The scorer fixture returns a manifest-bound source with complete known/unknown support.
    source_path, manifest_path = tmp_path / "private.json", tmp_path / "manifest.json"
    source_path.write_text(json.dumps(source))
    manifest_path.write_text(json.dumps(manifest))
    meta = tmp_path / "metadata.json"
    meta.write_text(
        json.dumps(
            metadata()
            | {"experiment_id": "identity-cli", "pipeline": "speaker-pilot", "language": "en"}
        )
    )
    output, path = tmp_path / "summary.json", tmp_path / "results.md"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/report-public-speakers.py"),
            "--input",
            str(source_path),
            "--manifest",
            str(manifest_path),
            "--metrics-protocol",
            "voiceup-open-set-v1",
            "--output",
            str(output),
            "--experiment-metadata",
            str(meta),
            "--results-md",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert len(ledger.read_snapshots(path)) == 1
    assert "private-A" not in path.read_text(encoding="utf-8")
