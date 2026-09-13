"""Atomic, append-only public experiment snapshots; never publish private source rows."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

MAX_BYTES = 16 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "results.md"
DATA_MARKER = "<!-- voiceup-data-v1 "
DATA_PATTERN = re.compile(r"<!-- voiceup-data-v1 (\{[^\r\n]+\}) -->")
ASR_PROTOCOLS = {
    "voiceup-mediaspeech-tr-v1",
    "voiceup-mediaspeech-tr-expanded-v1",
    "voiceup-fleurs-tr-test-v1",
}
HEADER = """# Deney sonuçları

Her deney kendi veri, model, protokol ve paydalarıyla okunmalıdır. Kalibrasyon,
tarihsel regresyon ve ayrılmış test birbirinin yerine geçmez. Ölçülemeyen skor
`—` olarak gösterilir; sıfır değildir. Aynı deneyin devamı ayrı sürüm olarak
korunur; sürümler bağımsız deney veya ek kişi/sorgu sayılmaz.

Kimlik precision/recall/F1 ve VoiceUp Score tanımları
[ölçüm protokolündedir](docs/SPEAKER_METRICS.md). cpWER konuşmacı etiketlerini
en uygun biçimde eşler; kalıcı kişi doğruluğu veya konuşmacı zaman hatası değildir.
İngilizce okuma ve birleştirilmiş kayıtlar doğal Türkçe toplantı başarısı kanıtlamaz.

Günlük [kullanım rehberindeki](docs/EXPERIMENTS.md) standart komutlarla güncellenir.
Elle yazılan açıklamalar korunur; makine kanıt blokları elle değiştirilmez.
"""


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def strict_json(payload):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate_json_field")
            value[key] = item
        return value

    def reject(_):
        raise ValueError("invalid_json_constant")

    return json.loads(payload, object_pairs_hook=pairs, parse_constant=reject)


def checked_path(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        require(
            not part.is_symlink() and not getattr(part, "is_junction", lambda: False)(),
            "linked_path_refused",
        )
    return path


def read_document(path):
    with checked_path(path).open("rb") as stream:
        payload = stream.read(MAX_BYTES + 1)
    require(len(payload) <= MAX_BYTES, "input_limit")
    return strict_json(payload)


def public_label(value):
    require(
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,159}", value) is not None
        and ".." not in value
        and not re.search(r"(?i)(gh[pousr]_|github_pat_|hf_|sk-)", value),
        "invalid_public_label",
    )
    return value


def sha256(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "invalid_hash")
    return value


def numeric(value, *, limit=None, nullable=False):
    if value is None and nullable:
        return None
    require(
        type(value) in (int, float)
        and math.isfinite(value)
        and value >= 0
        and (limit is None or value <= limit),
        "invalid_metric",
    )
    return value


def count(value):
    require(type(value) is int and 0 <= value <= 10**12, "invalid_count")
    return value


def counts(value, fields):
    require(isinstance(value, dict), "invalid_counts")
    return {field: count(value[field]) for field in fields}


def scores(value, fields):
    require(isinstance(value, dict), "invalid_scores")
    return {field: numeric(value[field], limit=1, nullable=True) for field in fields}


def validate_metadata(value):
    required = {"date", "dataset", "dataset_revision", "language", "role", "pipeline"}
    optional = {
        "models",
        "protocol_sha256",
        "configuration_sha256",
        "code_commit",
        "elapsed_seconds",
    }
    require(
        isinstance(value, dict) and required <= value.keys() <= required | optional,
        "invalid_metadata",
    )
    require(
        isinstance(value["date"], str)
        and date.fromisoformat(value["date"]).isoformat() == value["date"],
        "invalid_date",
    )
    require(value["language"] in {"tr", "en", "multilingual", "und"}, "invalid_language")
    require(value["role"] in {"calibration", "regression", "frozen-test", "smoke"}, "invalid_role")
    require(
        value["pipeline"]
        in {
            "speaker-pilot",
            "meeting-asr",
            "meeting-memory",
            "controlled-matching",
            "transcript-review",
        },
        "invalid_pipeline",
    )
    result = {key: value[key] for key in required}
    for field in ("dataset", "dataset_revision"):
        public_label(result[field])
    for field in ("protocol_sha256", "configuration_sha256"):
        if field in value:
            result[field] = sha256(value[field])
    if "code_commit" in value:
        require(re.fullmatch(r"[0-9a-f]{40}", value["code_commit"] or ""), "invalid_commit")
        result["code_commit"] = value["code_commit"]
    if "elapsed_seconds" in value:
        result["elapsed_seconds"] = numeric(value["elapsed_seconds"])
    if "models" in value:
        require(isinstance(value["models"], list) and len(value["models"]) <= 8, "invalid_models")
        result["models"] = []
        for model in value["models"]:
            require(isinstance(model, dict) and set(model) == {"id", "revision"}, "invalid_model")
            result["models"].append({key: public_label(model[key]) for key in ("id", "revision")})
    return result


def ratio(top, bottom):
    return top / bottom if bottom else None


def equal_rate(value, expected):
    require(
        value is None
        if expected is None
        else value is not None and math.isclose(value, expected, rel_tol=1e-10, abs_tol=1e-10),
        "metric_arithmetic_mismatch",
    )


def classification_metrics(source):
    result = {}
    for key, fields in (
        ("identity", ("precision", "recall", "micro_f1", "macro_f1")),
        ("unknown", ("precision", "recall", "f1")),
    ):
        values = counts(
            source[key], ("true_positive", "false_positive", "false_negative")
        ) | scores(source[key], fields)
        tp, fp, fn = (
            values[item] for item in ("true_positive", "false_positive", "false_negative")
        )
        equal_rate(values["precision"], ratio(tp, tp + fp))
        equal_rate(values["recall"], ratio(tp, tp + fn))
        equal_rate(
            values["micro_f1" if key == "identity" else "f1"],
            ratio(2 * tp, 2 * tp + fp + fn) if tp + fn else None,
        )
        result[key] = values
    result["voiceup_score"] = numeric(source["voiceup_score"], limit=100, nullable=True)
    macro, unknown = result["identity"]["macro_f1"], result["unknown"]["f1"]
    expected = (
        None
        if macro is None or unknown is None
        else 0.0
        if not macro or not unknown
        else 200 * macro * unknown / (macro + unknown)
    )
    equal_rate(result["voiceup_score"], expected)
    result.update(scores(source, ("enrollment_coverage", "decision_coverage")))
    return result


def identity_metrics(report):
    require(
        report.get("metrics_protocol") in {"voiceup-open-set-v1", "voiceup-real-turnturk-v1"},
        "unsupported_identity_protocol",
    )
    require(
        isinstance(report.get("stages"), list) and 0 < len(report["stages"]) <= 200,
        "invalid_stages",
    )
    result = {
        "protocol": report["metrics_protocol"],
        "manifest_sha256": sha256(report["manifest_sha256"]),
        "stages": [],
    }
    for source in report["stages"]:
        require(source.get("metrics_complete") is True, "incomplete_identity_stage")
        stage = counts(
            source, ("gallery_size_planned", "gallery_size_enrolled", "enrollment_failed")
        )
        stage["support"] = counts(
            source["support"],
            ("known_speakers", "unknown_speakers", "known_probes", "unknown_probes"),
        )
        stage.update(classification_metrics(source))
        stage["rates"] = scores(
            source["rates"],
            (
                "DIR",
                "known_misidentification",
                "FPIR_observed_lower_bound",
                "FPIR_worst_case_upper_bound",
                "unknown_detection_recall",
            ),
        )
        stage["counts"] = counts(
            source["counts"],
            (
                "known_planned",
                "unknown_planned",
                "known_correct",
                "known_wrong",
                "unknown_false_accepted",
                "known_job_failed",
                "unknown_job_failed",
                "known_not_run",
                "unknown_not_run",
            ),
        )
        require(
            stage["identity"]["true_positive"] + stage["identity"]["false_negative"]
            == stage["support"]["known_probes"],
            "known_support_mismatch",
        )
        require(
            stage["unknown"]["true_positive"] + stage["unknown"]["false_negative"]
            == stage["support"]["unknown_probes"],
            "unknown_support_mismatch",
        )
        result["stages"].append(stage)
    return result


def transcript_metrics(report):
    require(
        report.get("normalization") in {"unicode-words-v1", "turkish-words-v1"},
        "unsupported_normalization",
    )
    result = {
        "normalization": report["normalization"],
        "counts": counts(
            report["counts"],
            (
                "reference_words",
                "hypothesis_words",
                "unassigned_words",
            ),
        ),
    }
    for field in ("reference_speakers", "hypothesis_speakers"):
        value = report["counts"].get(field)
        result["counts"][field] = None if value is None else count(value)
    reference, hypothesis = (
        result["counts"][key] for key in ("reference_words", "hypothesis_words")
    )
    for key in ("cpwer", "assigned_only"):
        values = counts(report[key], ("errors", "substitutions", "deletions", "insertions"))
        values["rate"] = numeric(report[key]["rate"], nullable=True)
        require(
            values["errors"]
            == sum(values[item] for item in ("substitutions", "deletions", "insertions")),
            "metric_arithmetic_mismatch",
        )
        require(
            hypothesis == reference - values["deletions"] + values["insertions"],
            "word_support_mismatch",
        )
        equal_rate(values["rate"], ratio(values["errors"], reference))
        result[key] = values
    require(
        result["assigned_only"]["errors"] >= result["cpwer"]["errors"], "invalid_constrained_cost"
    )
    result["unassigned_word_fraction"] = numeric(
        report["unassigned_word_fraction"], limit=1, nullable=True
    )
    equal_rate(
        result["unassigned_word_fraction"], ratio(result["counts"]["unassigned_words"], hypothesis)
    )
    return result


def meeting_identity_metrics(report):
    result = classification_metrics(report)
    # This sequential protocol can enroll a missed person on a later appearance.
    # Its legacy field is cumulative, unlike the isolated-pilot first enrollment rate.
    result["cumulative_enrollment_coverage"] = result.pop("enrollment_coverage")
    result["first_enrollment_coverage"] = numeric(
        report.get("first_enrollment_coverage"), limit=1, nullable=True
    )
    if result["first_enrollment_coverage"] is not None:
        require(
            result["cumulative_enrollment_coverage"] is not None
            and result["first_enrollment_coverage"] <= result["cumulative_enrollment_coverage"],
            "enrollment_coverage_mismatch",
        )
    result["protocol"] = "voiceup-real-turnturk-v1"
    result["protocol_sha256"] = sha256(report["protocol_sha256"])
    result.update(counts(report, ("planned_meetings", "observed_meetings")))
    result["support"] = counts(
        report["support"],
        (
            "known_probes",
            "unknown_probes",
            "known_speakers",
            "unique_speakers",
            "observed_probes",
            "planned_probes",
        ),
    )
    support = result["support"]
    if result["first_enrollment_coverage"] is not None:
        equal_rate(
            result["first_enrollment_coverage"],
            ratio(result["unknown"]["true_positive"], support["unknown_probes"]),
        )
    require(
        result["planned_meetings"] == result["observed_meetings"] == 6
        and support["unique_speakers"] == 6,
        "meeting_plan_mismatch",
    )
    require(
        support["observed_probes"]
        == support["planned_probes"]
        == support["known_probes"] + support["unknown_probes"],
        "meeting_support_mismatch",
    )
    for key, denominator in (("identity", "known_probes"), ("unknown", "unknown_probes")):
        require(
            result[key]["true_positive"] + result[key]["false_negative"] == support[denominator],
            "meeting_support_mismatch",
        )
    require(
        isinstance(report["meetings"], list) and len(report["meetings"]) == 6,
        "meeting_plan_mismatch",
    )
    result["transcripts"] = []
    for index, meeting in enumerate(report["meetings"], 1):
        # Only an ordinal and aggregate text scores survive; case/source identities do not.
        metric = meeting.get("transcript_metrics")
        result["transcripts"].append(
            {
                "meeting": index,
                "source_sha256": sha256(meeting["source_sha256"]),
                "metrics": transcript_metrics(metric) if metric is not None else None,
            }
        )
    return result


def asr_clip_metrics(report):
    require(
        report.get("protocol") in ASR_PROTOCOLS
        and report.get("normalization") == "turkish-words-v1",
        "invalid_asr_protocol",
    )
    result = counts(
        report,
        (
            "planned_clips",
            "observed_clips",
            "reference_words",
            "hypothesis_words",
            "errors",
            "substitutions",
            "deletions",
            "insertions",
        ),
    )
    require(
        result["planned_clips"] == result["observed_clips"] and result["planned_clips"] > 0,
        "incomplete_asr_clips",
    )
    require(
        result["errors"]
        == sum(result[key] for key in ("substitutions", "deletions", "insertions")),
        "metric_arithmetic_mismatch",
    )
    require(
        result["hypothesis_words"]
        == result["reference_words"] - result["deletions"] + result["insertions"],
        "word_support_mismatch",
    )
    result["wer"] = numeric(report["wer"], nullable=True)
    equal_rate(result["wer"], ratio(result["errors"], result["reference_words"]))
    result.update(protocol=report["protocol"], normalization=report["normalization"])
    return result


def meeting_window_scope(report):
    starts = {
        "voiceup-real-turnturk-window300-v1": 300,
        "voiceup-real-turnturk-window600-v1": 600,
    }
    protocol = report["source_protocol_id"]
    require(isinstance(protocol, str) and protocol in starts, "invalid_meeting_window")
    selection = report.get("selection")
    require(
        isinstance(selection, dict)
        and set(selection) == {"start_seconds", "duration_seconds"}
        and all(type(value) is int for value in selection.values())
        and selection == {"start_seconds": starts[protocol], "duration_seconds": 300},
        "invalid_meeting_window",
    )
    durations = {
        field: numeric(report[field])
        for field in ("planned_audio_seconds", "observed_audio_seconds")
    }
    require(
        count(report["source_sessions"]) == count(report["planned_meetings"]) == 6
        and durations["planned_audio_seconds"] == 1800
        and durations["observed_audio_seconds"] == count(report["observed_meetings"]) * 300
        and 0 <= durations["observed_audio_seconds"] <= 1800,
        "invalid_meeting_window",
    )
    return {
        "source_protocol_id": protocol,
        "selection": selection.copy(),
        "source_sessions": 6,
        **durations,
    }


def review_metrics(report):
    source = report["metrics"]
    values = counts(
        source,
        (
            "planned_rows",
            "completed_rows",
            "failed_rows",
            "reference_words",
            "raw_errors",
            "corrected_errors",
            "changed_rows",
            "improved_rows",
            "worsened_rows",
            "clean_rows",
            "damaged_clean_rows",
            "accepted_edits",
            "beneficial_edits",
            "harmful_edits",
            "neutral_edits",
            "rejected_edits",
        ),
    )
    require(values["planned_rows"] > 0 and values["reference_words"] > 0, "empty_review_support")
    require(
        values["completed_rows"] + values["failed_rows"] == values["planned_rows"]
        and values["accepted_edits"]
        == sum(values[key] for key in ("beneficial_edits", "harmful_edits", "neutral_edits")),
        "review_support_mismatch",
    )
    require(
        values["damaged_clean_rows"] <= values["clean_rows"] <= values["planned_rows"]
        and values["damaged_clean_rows"] <= values["worsened_rows"]
        and values["improved_rows"] + values["worsened_rows"]
        <= values["changed_rows"]
        <= values["completed_rows"]
        and values["accepted_edits"] <= 3 * values["completed_rows"]
        and values["rejected_edits"] <= 3 * values["completed_rows"],
        "review_support_mismatch",
    )
    for key, numerator, denominator in (
        ("raw_wer", "raw_errors", "reference_words"),
        ("corrected_wer", "corrected_errors", "reference_words"),
        ("edit_precision", "beneficial_edits", "accepted_edits"),
        ("clean_damage_rate", "damaged_clean_rows", "clean_rows"),
        ("completion_coverage", "completed_rows", "planned_rows"),
        ("change_coverage", "changed_rows", "planned_rows"),
    ):
        values[key] = numeric(source[key], nullable=True)
        equal_rate(values[key], ratio(values[numerator], values[denominator]))
    for key in ("elapsed_seconds", "latency_median_seconds", "latency_max_seconds"):
        values[key] = numeric(source[key])
    require(
        values["latency_median_seconds"]
        <= values["latency_max_seconds"]
        <= values["elapsed_seconds"],
        "review_latency_mismatch",
    )
    return values


def review_visibility(report, metrics):
    fields = {"visible_status_counts", "review_required_edits", "saveable_rows"}
    supplied = fields & report.keys()
    if not supplied:
        # Historical v2 evidence predates the optional aggregate visibility counters.
        return {}
    require(supplied == fields and metrics is not None, "invalid_review_visibility")
    statuses = report["visible_status_counts"]
    names = ("unchanged", "suggested", "unmapped", "invalid_output")
    require(isinstance(statuses, dict) and set(statuses) == set(names), "invalid_review_visibility")
    statuses = counts(statuses, names)
    review_required = count(report["review_required_edits"])
    saveable = count(report["saveable_rows"])
    proposal_count = metrics["accepted_edits"] + metrics["rejected_edits"]
    require(
        sum(statuses.values()) == metrics["completed_rows"]
        and saveable <= statuses["suggested"]
        and saveable <= metrics["accepted_edits"]
        and review_required <= proposal_count <= 3 * metrics["completed_rows"],
        "review_visibility_mismatch",
    )
    return {
        "visible_status_counts": statuses,
        "review_required_edits": review_required,
        "saveable_rows": saveable,
    }


def sanitize_result(report, kind):
    require(isinstance(report, dict), "invalid_report")
    require(
        kind
        in {
            "identity",
            "meeting_identity",
            "transcript",
            "asr_clips",
            "observation",
            "transcript_review",
        },
        "unsupported_experiment_kind",
    )
    status = report.get("status", "complete" if kind == "transcript" else "unscored")
    if kind == "meeting_identity" and status == "running":
        status = "incomplete"
    require(status in {"complete", "incomplete", "failed", "unscored"}, "invalid_status")
    if kind == "identity" and report.get("source_run_complete") is not True:
        status = "incomplete"
    if kind == "identity" and any(
        stage.get("metrics_complete") is not True for stage in report.get("stages", [])
    ):
        status = "incomplete"
    result = {"kind": kind, "status": status, "metrics": None}
    if kind == "transcript_review":
        require(
            (
                report.get("protocol") == "voiceup-context-review-v1"
                or (
                    report.get("protocol") == "voiceup-context-review-visible-v1"
                    and report.get("policy_version") == "tr-context-words-v2"
                )
            )
            and report.get("reference_quality")
            in {
                "synthetic-authored",
                "corpus-provided-not-listened",
                "unverified-meeting-reference",
            },
            "invalid_review_protocol",
        )
        result.update(protocol=report["protocol"], reference_quality=report["reference_quality"])
        if report["protocol"] == "voiceup-context-review-visible-v1":
            result["policy_version"] = report["policy_version"]
    if kind == "meeting_identity":
        require(
            report.get("metrics_protocol") == "voiceup-real-turnturk-v1"
            and report.get("reference_quality") == "automatic-activity-unverified-text-diagnostic"
            and report.get("language") == "tr",
            "unsupported_meeting_reference",
        )
        result["reference_quality"] = "automatic-activity-unverified-text-diagnostic"
        result["coverage"] = counts(report, ("planned_meetings", "observed_meetings"))
        if "use_known_speaker_count" in report:
            require(type(report["use_known_speaker_count"]) is bool, "invalid_speaker_count_hint")
            result["use_known_speaker_count"] = report["use_known_speaker_count"]
        if "source_protocol_id" in report:
            result.update(meeting_window_scope(report))
    if kind == "asr_clips":
        require(
            isinstance(report.get("protocol"), str)
            and report["protocol"] in ASR_PROTOCOLS
            and report.get("normalization") == "turkish-words-v1",
            "invalid_asr_protocol",
        )
        coverage = counts(report, ("planned_clips", "observed_clips"))
        require(
            0 <= coverage["observed_clips"] <= coverage["planned_clips"]
            and coverage["planned_clips"] > 0,
            "invalid_asr_coverage",
        )
        # Preserve the canonical complete v1 snapshots when replaying old evidence.
        if status != "complete" or report["protocol"] != "voiceup-mediaspeech-tr-v1":
            result.update(coverage=coverage, protocol=report["protocol"])
    for field in (
        "source_sha256",
        "input_sha256",
        "private_source_report_sha256",
        "manifest_sha256",
    ):
        if field in report:
            result[field] = sha256(report[field])
    if kind == "observation":
        require(status != "complete", "observation_has_no_accuracy_score")
        permitted = {
            "planned_people",
            "enrolled_people",
            "correct_returns",
            "observed_speakers",
            "transcript_segments",
        }
        supplied = report.get("observations", {})
        require(isinstance(supplied, dict) and supplied.keys() <= permitted, "invalid_observations")
        result["observations"] = counts(supplied, tuple(sorted(supplied)))
    elif status == "complete":
        result["metrics"] = (
            identity_metrics(report)
            if kind == "identity"
            else meeting_identity_metrics(report)
            if kind == "meeting_identity"
            else asr_clip_metrics(report)
            if kind == "asr_clips"
            else review_metrics(report)
            if kind == "transcript_review"
            else transcript_metrics(report)
        )
    if kind == "transcript_review" and result["protocol"] == "voiceup-context-review-visible-v1":
        result.update(review_visibility(report, result["metrics"]))
    return result


def snapshot_digest(value):
    return digest(
        {
            key: value[key]
            for key in ("experiment_id", "metadata", "result", "evidence", "evidence_sha256")
        }
    )


def _parse_snapshots(content):
    matches = DATA_PATTERN.findall(content)
    require(content.count(DATA_MARKER) == len(matches), "invalid_ledger_marker")
    result, revisions, seen = [], {}, set()
    for match in matches:
        value = strict_json(match)
        require(
            isinstance(value, dict)
            and set(value) - {"record_sha256"}
            == {
                "experiment_id",
                "metadata",
                "result",
                "evidence",
                "evidence_sha256",
                "revision",
                "recorded_at_utc",
                "snapshot_sha256",
                "aggregate_sha256",
            },
            "invalid_ledger_snapshot",
        )
        public_label(value["experiment_id"])
        validate_metadata(value["metadata"])
        if "record_sha256" in value:
            require(
                value["record_sha256"]
                == digest({key: item for key, item in value.items() if key != "record_sha256"}),
                "ledger_record_changed",
            )
        require(value["snapshot_sha256"] == snapshot_digest(value), "ledger_snapshot_changed")
        key = value["experiment_id"]
        require(
            value["revision"] == revisions.get(key, 0) + 1 and value["snapshot_sha256"] not in seen,
            "invalid_ledger_revision",
        )
        revisions[key] = value["revision"]
        seen.add(value["snapshot_sha256"])
        result.append(value)
    return result


def read_snapshots(path):
    path = checked_path(path)
    if not path.exists():
        return []
    require(path.stat().st_size <= MAX_BYTES, "ledger_limit")
    return _parse_snapshots(path.read_text(encoding="utf-8"))


def percent(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def render_snapshot(value):
    meta, result = value["metadata"], value["result"]
    lines = [
        "",
        f"## {value['experiment_id']} · sürüm {value['revision']}",
        "",
        f"{meta['date']} · `{meta['dataset']}` / `{meta['dataset_revision']}` · {meta['language']} · **{meta['role']}** · `{meta['pipeline']}` · **{result['status']}**",
        "",
    ]
    if result.get("reference_quality") == "automatic-activity-unverified-text-diagnostic":
        lines.append(
            "**Zayıf otomatik referans:** Konuşma etkinliği otomatik etiketlidir; metin referansı ve zaman damgaları insan doğrulamasıyla teyit edilmemiştir. Bu tanı skorları insan doğrulanmış Türkçe kimlik/metin doğruluğu, bağımsız oturum veya 50 kişi kabulü değildir.\n"
        )
        if "use_known_speaker_count" in result:
            lines.append(
                "Konuşmacı sayısı girdisi: her toplantı için 2 (`expected_speakers=2`, `participant_count=2`).\n"
                if result["use_known_speaker_count"]
                else "Konuşmacı sayısı girdisi: kişi sayısı ipucu verilmedi.\n"
            )
    if value["evidence"]:
        lines.append(
            f"[Toplu kaynak kanıtı]({value['evidence']}) · dosya SHA-256 `{value['evidence_sha256']}`\n"
        )
    if "selection" in result:
        start = result["selection"]["start_seconds"]
        end = start + result["selection"]["duration_seconds"]
        lines.append(
            f"Kaynak aralığı: her görüşmede [{start},{end}) saniye; gözlenen/planlı ses {result['observed_audio_seconds']:g}/{result['planned_audio_seconds']:g} saniye. Aynı altı kişi ve aynı kaynak oturumları; yeni zaman aralığı yeni kişi veya bağımsız oturum değildir.\n"
        )
    metric = result["metrics"]
    if metric is None:
        if result["kind"] == "asr_clips" and "coverage" in result:
            coverage = result["coverage"]
            lines.append(
                f"Klip {coverage['observed_clips']}/{coverage['planned_clips']}; koşum tamamlanmadı.\n"
            )
        lines.append(
            "Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**."
        )
        if result.get("observations"):
            lines.append(
                "\nGözlenen sayılar: "
                + "; ".join(f"`{key}`={number}" for key, number in result["observations"].items())
                + "."
            )
    elif result["kind"] == "transcript_review":
        visible_review = result["protocol"] == "voiceup-context-review-visible-v1"
        if visible_review:
            lines.extend(
                [
                    "Görünür öneri politikası `tr-context-words-v2`: kayda uygun yanıttaki bütün model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Eşlenemeyen veya geçersiz yanıt ham metinle puanlanır. Bu ölçüm kullanıcı kaydı/onayı değildir.",
                    "",
                ]
            )
            if "visible_status_counts" in result:
                statuses = result["visible_status_counts"]
                lines.extend(
                    [
                        f"Ulaşan yanıt {metric['completed_rows']}: değişmedi {statuses['unchanged']}; öneri {statuses['suggested']}; eşlenemedi {statuses['unmapped']}; geçersiz çıktı {statuses['invalid_output']}. Ulaşmayan istek {metric['failed_rows']}; yanıtın ulaşması geçerli veya doğru öneri olduğu anlamına gelmez.",
                        "",
                        f"Kayda uygun satır {result['saveable_rows']}; inceleme işaretli öneri {result['review_required_edits']}. Bunlar kullanıcı onayı veya kayıt sayısı değildir.",
                        "",
                    ]
                )
        lines.extend(
            [
                f"Referans: `{result['reference_quality']}`. İstek {metric['completed_rows']}/{metric['planned_rows']}; başarısız {metric['failed_rows']} istek ham metinle paydada kaldı.",
                "",
                "| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |",
                "|---|---|---|---|---|",
                f"| {percent(metric['raw_wer'])} | {percent(metric['corrected_wer'])} | {metric['improved_rows']} / {metric['worsened_rows']} | {percent(metric['edit_precision'])} ({metric['beneficial_edits']}/{metric['accepted_edits']}) | {percent(metric['clean_damage_rate'])} ({metric['damaged_clean_rows']}/{metric['clean_rows']}) |",
                "",
                f"{metric['reference_words']} referans kelime; değişen satır {metric['changed_rows']}/{metric['planned_rows']}; {'kayda alınamayan öneri' if visible_review else 'reddedilen öneri'} {metric['rejected_edits']}; medyan/en uzun süre {metric['latency_median_seconds']:.2f}/{metric['latency_max_seconds']:.2f} saniye.",
                "",
                "İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.",
            ]
        )
    elif result["kind"] == "asr_clips":
        lines.extend(
            [
                f"Klip {metric['observed_clips']}/{metric['planned_clips']}; {metric['reference_words']} referans kelime / {metric['hypothesis_words']} çıktı kelimesi.",
                "",
                "| Kelime hata oranı (WER) | Hata | Değiştirme | Silme | Ekleme |",
                "|---|---|---|---|---|",
                f"| {percent(metric['wer'])} | {metric['errors']} | {metric['substitutions']} | {metric['deletions']} | {metric['insertions']} |",
                "",
                f"Normalizasyon `{metric['normalization']}`. Her klibin kelime hataları ayrı hesaplanıp bütün referans kelimelerine bölünür; klipler farklı kişiler sayılmaz. Kimlik precision/recall/F1, VoiceUp Score, konuşmacı zaman hatası ve cpWER ölçülmez.",
            ]
        )
    elif result["kind"] == "meeting_identity":
        identity = metric["identity"]
        lines.extend(
            [
                f"Toplantı {metric['observed_meetings']}/{metric['planned_meetings']}; {metric['support']['unique_speakers']} gerçek kişi; bilinen/yeni kişi görünümleri {metric['support']['known_probes']}/{metric['support']['unknown_probes']}.",
                "",
                "| Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |",
                "|---|---|---|---|---|---|",
                f"| {percent(identity['precision'])} | {percent(identity['recall'])} | {percent(identity['micro_f1'])} | {percent(identity['macro_f1'])} | {percent(metric['unknown']['f1'])} | {metric['voiceup_score']:.2f} |",
                "",
                f"Koşu sonunda birikimli kayıt kapsamı: {percent(metric['cumulative_enrollment_coverage'])}; ilk görünümde kayıt kapsamı: {percent(metric['first_enrollment_coverage'])}; karar kapsamı: {percent(metric['decision_coverage'])}.",
                "",
                "| Toplantı | Referans kelime | cpWER | Atanmamış akış cezasıyla |",
                "|---|---|---|---|",
            ]
        )
        for transcript in metric["transcripts"]:
            score = transcript["metrics"]
            lines.append(
                f"| {transcript['meeting']} | {score['counts']['reference_words'] if score else '—'} | {percent(score['cpwer']['rate']) if score else '—'} | {percent(score['assigned_only']['rate']) if score else '—'} |"
            )
    elif result["kind"] == "identity":
        lines.extend(
            [
                "| Galeri kayıt/plan | Bilinen/yeni sorgu | Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |",
                "|---|---|---|---|---|---|---|---|",
            ]
        )
        for stage in metric["stages"]:
            identity = stage["identity"]
            score = "—" if stage["voiceup_score"] is None else f"{stage['voiceup_score']:.2f}"
            lines.append(
                f"| {stage['gallery_size_enrolled']}/{stage['gallery_size_planned']} | {stage['support']['known_probes']}/{stage['support']['unknown_probes']} | {percent(identity['precision'])} | {percent(identity['recall'])} | {percent(identity['micro_f1'])} | {percent(identity['macro_f1'])} | {percent(stage['unknown']['f1'])} | {score} |"
            )
        lines.append(
            "\nBaşarısız ilk kayıt ve sorgular planlı paydada tutulur; iç içe galeriler bağımsız tekrar değildir. Metin ve konuşmacı zaman hatası bu deneyde ölçülmez."
        )
    else:
        lines.extend(
            [
                f"Normalizasyon: `{metric['normalization']}`; {metric['counts']['reference_words']} referans kelime / {metric['counts']['hypothesis_words']} çıktı kelimesi.",
                "",
                "| Ölçü | Hata | Değiştirme | Silme | Ekleme | Oran |",
                "|---|---|---|---|---|---|",
            ]
        )
        for key in ("cpwer", "assigned_only"):
            cost = metric[key]
            lines.append(
                f"| {key} | {cost['errors']} | {cost['substitutions']} | {cost['deletions']} | {cost['insertions']} | {percent(cost['rate'])} |"
            )
        lines.append(
            f"\nAtanmamış kelime oranı: {percent(metric['unassigned_word_fraction'])}. Kalıcı kimlik precision/recall/F1 ve VoiceUp Score bu deneyde ölçülmez."
        )
    if meta.get("models"):
        lines.append(
            "\nModeller: "
            + "; ".join(f"`{item['id']}` @ `{item['revision']}`" for item in meta["models"])
            + "."
        )
    lines.extend(["", DATA_MARKER + canonical(value) + " -->", ""])
    return "\n".join(lines)


def record_experiment(ledger, *, experiment_id, metadata, report, kind, evidence=None):
    """Append one sanitized snapshot; exact semantic replay returns False without writing."""
    public_label(experiment_id)
    require("/" not in experiment_id, "invalid_experiment_id")
    metadata = validate_metadata(metadata)
    result = sanitize_result(report, kind)
    if kind in {"transcript", "asr_clips"} and report.get("normalization") == "turkish-words-v1":
        require(metadata["language"] in {"tr", "multilingual"}, "normalization_language_mismatch")
    if kind == "identity":
        require(
            report.get("metrics_protocol", "voiceup-open-set-v1") == "voiceup-open-set-v1",
            "identity_protocol_mismatch",
        )
    evidence_hash = None
    if evidence is not None:
        require(
            isinstance(evidence, str)
            and re.fullmatch(r"docs/evidence/[A-Za-z0-9._/-]+\.json", evidence)
            and ".." not in PurePosixPath(evidence).parts,
            "invalid_evidence_path",
        )
        evidence_path = checked_path(ROOT / evidence)
        with evidence_path.open("rb") as stream:
            evidence_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    aggregate_hash = digest(report)
    path = checked_path(ledger)
    require(path.suffix == ".md", "invalid_ledger_path")
    value = {
        "experiment_id": experiment_id,
        "metadata": metadata,
        "result": result,
        "evidence": evidence,
        "evidence_sha256": evidence_hash,
    }
    value["snapshot_sha256"] = snapshot_digest(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = checked_path(path.with_name(path.name + ".lock"))
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError("ledger_locked") from None
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with handle:
            handle.write("voiceup-experiment-ledger-v1\n")
        if path.exists():
            require(path.stat().st_size <= MAX_BYTES, "ledger_limit")
            content = path.read_text(encoding="utf-8")
        else:
            content = HEADER
        history = _parse_snapshots(content)
        if any(row["snapshot_sha256"] == value["snapshot_sha256"] for row in history):
            return False
        require(len(history) < 10000, "experiment_limit")
        value.update(
            revision=1 + sum(row["experiment_id"] == experiment_id for row in history),
            recorded_at_utc=datetime.now(UTC).isoformat(),
            aggregate_sha256=aggregate_hash,
        )
        value["record_sha256"] = digest(value)
        output = content + render_snapshot(value)
        require(len(output.encode("utf-8")) <= MAX_BYTES, "ledger_limit")
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(output)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return True
    finally:
        if temporary.exists():
            temporary.unlink()
        lock.unlink()


def record_from_metadata_file(ledger, metadata_path, *, report, kind, evidence=None):
    require(
        Path(ledger).resolve() != Path(metadata_path).resolve(), "ledger_metadata_path_conflict"
    )
    supplied = read_document(metadata_path)
    require(isinstance(supplied, dict) and "experiment_id" in supplied, "missing_experiment_id")
    return record_experiment(
        ledger,
        experiment_id=supplied["experiment_id"],
        metadata={key: item for key, item in supplied.items() if key != "experiment_id"},
        report=report,
        kind=kind,
        evidence=evidence,
    )
