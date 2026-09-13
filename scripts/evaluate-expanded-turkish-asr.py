"""Prepare an untouched MediaSpeech remainder and resume frozen Turkish ASR cohorts.

Raw references and hypotheses stay in private files. Inference is offline and uses
the production model contract and unchanged inference/normalization parameters.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import stat
import tarfile
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path


def load_base():
    spec = importlib.util.spec_from_file_location(
        "expanded_existing_asr", Path(__file__).with_name("evaluate-turkish-asr.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base()
PROTOCOLS = {
    "voiceup-mediaspeech-tr-expanded-v1": "MediaSpeech-TR",
    "voiceup-fleurs-tr-test-v1": "FLEURS-TR",
}
MANIFEST_SHA256 = {
    "voiceup-mediaspeech-tr-expanded-v1": "e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef",
    "voiceup-fleurs-tr-test-v1": "77fa49973ee399d0378842ef9697697a54a29fb9a5f71a04ea55f6bf818624f8",
}
MODEL_ID = "Systran/faster-whisper-large-v3"
PREVIOUS_MANIFEST_SHA256 = "b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e"
EXPECTED_MEDIASPEECH_CLIPS = 2513
SETTINGS = dict(
    language="tr",
    beam_size=5,
    word_timestamps=True,
    condition_on_previous_text=False,
    vad_filter=False,
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path, limit=16 * 1024 * 1024):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_field")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("nonfinite_json")

    with base.safe_path(path).open("rb") as stream:
        content = stream.read(limit + 1)
    require(len(content) <= limit, "json_limit")
    return json.loads(content, object_pairs_hook=pairs, parse_constant=constant)


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def is_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def load_manifest(root):
    path = base.safe_path(root) / "manifest.json"
    value = read_json(path)
    require(
        isinstance(value, dict)
        and set(value)
        == {
            "schema_version",
            "protocol",
            "language",
            "role",
            "dataset",
            "dataset_revision",
            "source_sha256",
            "reference_quality",
            "speaker_session_labels_available",
            "selection",
            "exclusion_manifest_sha256",
            "clips",
        },
        "invalid_manifest_fields",
    )
    require(
        type(value["schema_version"]) is int
        and value["schema_version"] == 1
        and value["protocol"] in PROTOCOLS
        and value["dataset"] == PROTOCOLS[value["protocol"]]
        and value["language"] == "tr"
        and value["role"] == "frozen-test"
        and value["reference_quality"] == "source-human-transcribed"
        and value["speaker_session_labels_available"] is False
        and isinstance(value["dataset_revision"], str)
        and re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", value["dataset_revision"]) is not None
        and is_hash(value["source_sha256"])
        and (
            value["exclusion_manifest_sha256"] is None
            or is_hash(value["exclusion_manifest_sha256"])
        )
        and isinstance(value["selection"], str)
        and 1 <= len(value["selection"]) <= 200
        and isinstance(value["clips"], list)
        and 1 <= len(value["clips"]) <= 5000,
        "invalid_manifest",
    )
    seen_ids, seen_hashes = set(), set()
    for row in value["clips"]:
        require(
            isinstance(row, dict)
            and set(row)
            == {
                "clip_id",
                "audio",
                "reference_file",
                "audio_sha256",
                "reference_sha256",
                "reference",
            },
            "invalid_clip_fields",
        )
        identity = row["clip_id"]
        require(
            isinstance(identity, str)
            and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identity) is not None
            and row["audio"] in {f"clips/{identity}.wav", f"clips/{identity}.flac"}
            and row["reference_file"] == f"clips/{identity}.txt"
            and is_hash(row["audio_sha256"])
            and is_hash(row["reference_sha256"])
            and isinstance(row["reference"], str)
            and 0 < len(row["reference"]) <= 500_000
            and row["reference"].strip() == row["reference"]
            and identity not in seen_ids
            and row["audio_sha256"] not in seen_hashes,
            "invalid_or_duplicate_clip",
        )
        seen_ids.add(identity)
        seen_hashes.add(row["audio_sha256"])
    manifest_hash = base.digest(path)
    require(manifest_hash == MANIFEST_SHA256[value["protocol"]], "manifest_source_binding_mismatch")
    return value, manifest_hash


def validate_sources(root, manifest):
    durations = {}
    total = len(manifest["clips"])
    print(f"ASR preflight: source integrity 0/{total}", flush=True)
    for index, row in enumerate(manifest["clips"], 1):
        audio, reference = (base.safe_path(root / row[key]) for key in ("audio", "reference_file"))
        require(
            audio.is_file()
            and 0 < audio.stat().st_size <= 4 * 1024 * 1024
            and reference.is_file()
            and 0 < reference.stat().st_size <= 2 * 1024 * 1024
            and base.digest(audio) == row["audio_sha256"]
            and base.digest(reference) == row["reference_sha256"]
            and reference.read_text(encoding="utf-8-sig").strip() == row["reference"],
            "source_changed",
        )
        # Decode each bounded file before starting inference, including already cached clips.
        samples, rate = base.read_audio(audio)
        durations[row["audio_sha256"]] = len(samples) / rate
        if index % 100 == 0 or index == total:
            print(f"ASR preflight: source integrity {index}/{total}", flush=True)
    return durations


def paths(args):
    output = base.safe_path(args.output)
    public = base.safe_path(output.with_name(output.stem + ".aggregate.json"))
    cache = base.safe_path(output.with_name(output.stem + ".clips"))
    return output, public, cache


def validate_paths(args, manifest):
    output, public, cache = paths(args)
    ledger = base.safe_path(args.results_md)
    root = base.safe_path(args.root).resolve()
    models = base.safe_path(args.model_dir).resolve()
    require(output.suffix == ".json" and ledger.suffix == ".md", "invalid_output_suffix")
    # Manifest paths have exactly one fixed parent. Check its ancestry once per pass,
    # then lstat each regular file once, avoiding repeated bind-mount path resolution.
    base.safe_path(root / "clips")
    protected = [
        root / row[key] for row in manifest["clips"] for key in ("audio", "reference_file")
    ] + [
        base.safe_path(root / "manifest.json"),
        base.safe_path(args.model_manifest).resolve(),
        base.safe_path(__file__).resolve(),
    ]
    protected_paths, protected_identities = set(), set()
    for source in protected:
        info = source.lstat()
        require(stat.S_ISREG(info.st_mode), "linked_or_nonregular_source")
        protected_paths.add(source)
        protected_identities.add((info.st_dev, info.st_ino))
    destinations = (output, public, cache, ledger)
    resolved = {target: target.resolve() for target in destinations}
    snapshots = {}
    for target in destinations:
        try:
            snapshots[target] = target.stat()
        except FileNotFoundError:
            snapshots[target] = None
        info = snapshots[target]
        require(
            not resolved[target].is_relative_to(root)
            and not resolved[target].is_relative_to(models)
            and resolved[target] not in protected_paths
            and (info is None or (info.st_dev, info.st_ino) not in protected_identities),
            "evidence_source_conflict",
        )
        if info is not None:
            require(
                stat.S_ISDIR(info.st_mode)
                if target == cache
                else stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                "linked_destination",
            )
    for index, target in enumerate(destinations):
        for other in destinations[index + 1 :]:
            require(
                resolved[target] != resolved[other]
                and not resolved[target].is_relative_to(resolved[other])
                and not resolved[other].is_relative_to(resolved[target])
                and not (
                    snapshots[target] is not None
                    and snapshots[other] is not None
                    and (snapshots[target].st_dev, snapshots[target].st_ino)
                    == (snapshots[other].st_dev, snapshots[other].st_ino)
                ),
                "aliased_destinations",
            )
    for target in (output, public):
        lock = base.safe_path(target.with_suffix(target.suffix + ".lock"))
        require(not lock.exists() or (lock.is_file() and lock.stat().st_nlink == 1), "linked_lock")
    return output, public, cache


def configuration():
    from voiceup import meeting_metrics

    return {
        **SETTINGS,
        "compute_type": "int8_float16",
        "normalization": "turkish-words-v1",
        "evaluation_source_sha256": base.digest(Path(__file__)),
        "base_source_sha256": base.digest(Path(base.__file__)),
        "metric_source_sha256": base.digest(Path(meeting_metrics.__file__)),
    }


def binding(args, manifest_hash, config):
    return dict(
        schema_version=1,
        manifest_sha256=manifest_hash,
        configuration=config,
        model_id=MODEL_ID,
        model_revision=base.MODEL_REVISION,
        model_manifest_sha256=base.digest(args.model_manifest),
        model_directory=str(base.safe_path(args.model_dir)),
        experiment_id=args.experiment_id,
        results_md=str(base.safe_path(args.results_md)),
    )


def metric(reference, hypothesis):
    from voiceup.meeting_metrics import score_transcript

    result = score_transcript(
        {"reference": reference}, {"hypothesis": hypothesis}, normalization="turkish-words-v1"
    )
    for key in ("cpwer", "assigned_only"):
        result[key].pop("assignment", None)
    return result


def load_model(args):
    from faster_whisper import WhisperModel
    from voiceup_inference.meeting_models import (
        ASR_FILES,
        ASR_ID,
        ASR_REVISION,
        verify_meeting_bundle,
    )

    require(ASR_ID == MODEL_ID and ASR_REVISION == base.MODEL_REVISION, "model_contract_changed")
    verify_meeting_bundle(args.model_dir, args.model_manifest, ASR_ID, ASR_REVISION, ASR_FILES)
    return WhisperModel(
        str(args.model_dir),
        device="cuda",
        device_index=0,
        compute_type="int8_float16",
        cpu_threads=4,
        num_workers=1,
        local_files_only=True,
    )


def transcribe(model, samples):
    segments, info = model.transcribe(samples, **SETTINGS)
    return " ".join(segment.text for segment in segments), info.language


def read_cached(cache, manifest, durations):
    expected_names = {"binding.json"} | {
        f"{index:06d}.json" for index in range(len(manifest["clips"]))
    }
    require(
        all(
            path.name in expected_names
            or (
                re.fullmatch(r"[0-9]{6}\.json\.[a-f0-9]{32}\.tmp", path.name) is not None
                and base.safe_path(path).is_file()
                and path.stat().st_nlink == 1
            )
            for path in cache.iterdir()
        ),
        "unexpected_checkpoint_file",
    )
    rows = []
    gap = False
    for index, source in enumerate(manifest["clips"]):
        path = base.safe_path(cache / f"{index:06d}.json")
        if not path.exists():
            gap = True
            continue
        require(not gap and path.is_file() and path.stat().st_nlink == 1, "checkpoint_gap_or_link")
        row = read_json(path, 4 * 1024 * 1024)
        require(
            isinstance(row, dict)
            and set(row)
            == {
                "source_sha256",
                "duration_seconds",
                "detected_language",
                "metrics",
                "reference",
                "hypothesis",
                "inference_seconds",
            },
            "checkpoint_shape",
        )
        require(
            row["source_sha256"] == source["audio_sha256"]
            and row["reference"] == source["reference"]
            and isinstance(row["hypothesis"], str)
            and len(row["hypothesis"]) <= 500_000
            and isinstance(row["detected_language"], str)
            and len(row["detected_language"]) <= 20
            and all(
                type(row[key]) in (int, float) and math.isfinite(row[key]) and row[key] >= 0
                for key in ("duration_seconds", "inference_seconds")
            )
            and 0 < row["duration_seconds"] <= 60
            and row["duration_seconds"] == durations[source["audio_sha256"]]
            and row["metrics"] == metric(source["reference"], row["hypothesis"]),
            "checkpoint_content_changed",
        )
        rows.append(row)
    return rows


def aggregate(report):
    result = base.aggregate({**report, "archive_sha256": report["source_sha256"]})
    result["protocol"] = report["protocol"]
    return result


def publish(args, manifest, report, config, public):
    from experiment_ledger import record_experiment

    summary = aggregate(report)
    content = (json.dumps(summary, indent=2, allow_nan=False) + "\n").encode()
    if public.exists():
        existing = read_json(public)
        if existing.get("status") == "complete":
            require(public.read_bytes() == content, "completed_aggregate_changed")
        else:
            base.save_checkpoint(public, summary)
    else:
        base.immutable_write(public, content)
    record_experiment(
        args.results_md,
        experiment_id=args.experiment_id,
        metadata={
            "date": report["started_date"],
            "dataset": manifest["dataset"],
            "dataset_revision": manifest["dataset_revision"],
            "language": "tr",
            "role": "frozen-test",
            "pipeline": "meeting-asr",
            "protocol_sha256": report["manifest_sha256"],
            "configuration_sha256": canonical_hash(config),
            "elapsed_seconds": report["elapsed_seconds"],
            "models": [{"id": MODEL_ID, "revision": base.MODEL_REVISION}],
        },
        report=summary,
        kind="asr_clips",
    )


def evaluate(args):
    root = base.safe_path(args.root)
    manifest, manifest_hash = load_manifest(root)
    require(base.safe_path(args.model_dir).is_dir(), "model_directory_missing")
    require(base.safe_path(args.model_manifest).is_file(), "model_manifest_missing")
    print("ASR preflight: path safety before lock", flush=True)
    output, public, cache = validate_paths(args, manifest)
    require(
        isinstance(args.experiment_id, str)
        and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", args.experiment_id) is not None,
        "invalid_experiment_id",
    )
    config = configuration()
    expected_binding = binding(args, manifest_hash, config)
    with ExitStack() as locks:
        for destination in sorted((output, public), key=str):
            locks.enter_context(base.file_helpers.state_lock(destination))
        print("ASR preflight: path safety under lock", flush=True)
        validate_paths(args, manifest)
        exists = output.exists() or public.exists() or cache.exists()
        require(not exists or args.resume, "existing_run_requires_resume")
        require(exists or not args.resume, "resume_state_missing")
        if exists:
            require(
                cache.is_dir() and read_json(cache / "binding.json") == expected_binding,
                "resume_binding_mismatch",
            )
        durations = validate_sources(root, manifest)
        if not exists:
            cache.mkdir(parents=True)
            base.immutable_write(
                cache / "binding.json", (json.dumps(expected_binding, indent=2) + "\n").encode()
            )
        cached = read_cached(cache, manifest, durations)
        previous = read_json(output, 64 * 1024 * 1024) if output.exists() else None
        if previous is not None:
            expected_core = dict(
                schema_version=1,
                protocol=manifest["protocol"],
                language="tr",
                language_mode="tr",
                role="frozen-test",
                model_id=MODEL_ID,
                model_revision=base.MODEL_REVISION,
                manifest_sha256=manifest_hash,
                source_sha256=manifest["source_sha256"],
                evaluation_source_sha256=config["evaluation_source_sha256"],
                planned_clips=len(manifest["clips"]),
            )
            require(
                isinstance(previous, dict)
                and set(previous)
                == set(expected_core)
                | {"binding_sha256", "status", "clips", "started_date", "elapsed_seconds"}
                and all(previous.get(key) == value for key, value in expected_core.items())
                and type(previous["schema_version"]) is int
                and type(previous["planned_clips"]) is int,
                "checkpoint_provenance_changed",
            )
            require(
                previous.get("binding_sha256") == canonical_hash(expected_binding),
                "report_binding_mismatch",
            )
            require(
                previous.get("status") in {"complete", "incomplete"}
                and previous.get("planned_clips") == len(manifest["clips"])
                and isinstance(previous.get("clips"), list)
                and previous["clips"] == cached[: len(previous["clips"])]
                and type(previous.get("elapsed_seconds")) in (int, float)
                and math.isfinite(previous["elapsed_seconds"])
                and previous["elapsed_seconds"] >= 0
                and isinstance(previous.get("started_date"), str)
                and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", previous["started_date"])
                is not None,
                "invalid_previous_checkpoint",
            )
            datetime.strptime(previous["started_date"], "%Y-%m-%d")
        if public.exists():
            previous_public = read_json(public)
            require(
                previous_public.get("input_sha256") == manifest_hash
                and previous_public.get("source_sha256") == manifest["source_sha256"]
                and previous_public.get("protocol") == manifest["protocol"],
                "aggregate_binding_mismatch",
            )
        if previous is not None and previous.get("status") == "complete":
            require(
                previous.get("clips") == cached and len(cached) == len(manifest["clips"]),
                "completed_checkpoint_changed",
            )
            publish(args, manifest, previous, config, public)
            return previous
        report = {
            "schema_version": 1,
            "protocol": manifest["protocol"],
            "status": "incomplete",
            "language": "tr",
            "language_mode": "tr",
            "role": "frozen-test",
            "model_id": MODEL_ID,
            "model_revision": base.MODEL_REVISION,
            "manifest_sha256": manifest_hash,
            "evaluation_source_sha256": config["evaluation_source_sha256"],
            "source_sha256": manifest["source_sha256"],
            "binding_sha256": canonical_hash(expected_binding),
            "planned_clips": len(manifest["clips"]),
            "clips": cached,
            "started_date": previous["started_date"]
            if previous
            else datetime.now(UTC).date().isoformat(),
            "elapsed_seconds": previous["elapsed_seconds"] if previous else 0.0,
        }
        elapsed_before = max(
            report["elapsed_seconds"], sum(row["inference_seconds"] for row in cached)
        )
        base.save_checkpoint(output, report)
        started = time.monotonic()
        try:
            model = load_model(args) if len(cached) < report["planned_clips"] else None
            for index in range(len(cached), report["planned_clips"]):
                source = manifest["clips"][index]
                path = root / source["audio"]
                require(base.digest(path) == source["audio_sha256"], "source_changed")
                samples, rate = base.read_audio(path)
                clip_started = time.monotonic()
                hypothesis, language = transcribe(model, samples)
                row = dict(
                    source_sha256=source["audio_sha256"],
                    duration_seconds=len(samples) / rate,
                    detected_language=language,
                    metrics=metric(source["reference"], hypothesis),
                    reference=source["reference"],
                    hypothesis=hypothesis,
                    inference_seconds=time.monotonic() - clip_started,
                )
                base.save_checkpoint(cache / f"{index:06d}.json", row)
                report["clips"].append(row)
                # Per-clip files are durable; the consolidated private report is bounded-cadence.
                if len(report["clips"]) % 100 == 0:
                    report["elapsed_seconds"] = elapsed_before + time.monotonic() - started
                    base.save_checkpoint(output, report)
                print(f"ASR inference {len(report['clips'])}/{report['planned_clips']}", flush=True)
            report["status"] = "complete"
        finally:
            report["elapsed_seconds"] = elapsed_before + time.monotonic() - started
            base.save_checkpoint(output, report)
            publish(args, manifest, report, config, public)
        return report


def exclude_previous(rows, previous):
    identities = {row["clip_id"] for row in previous}
    hashes = {row["flac_sha256"] for row in previous}
    return [
        row
        for row in rows
        if row["clip_id"] not in identities and row["audio_sha256"] not in hashes
    ]


def prepare_mediaspeech(root, original):
    root, original = base.safe_path(root), base.safe_path(original)
    require(
        not root.resolve().is_relative_to(original.resolve())
        and not original.resolve().is_relative_to(root.resolve()),
        "preparation_roots_overlap",
    )
    old, old_hash = base.load_manifest(original)
    require(
        old_hash == PREVIOUS_MANIFEST_SHA256 and len(old["clips"]) == 80, "previous_cohort_changed"
    )
    archive = original / "TR.tgz"
    require(
        archive.stat().st_size == base.ARCHIVE_BYTES
        and base.digest(archive) == base.ARCHIVE_SHA256,
        "archive_changed",
    )
    base.index_archive(archive)
    rows, payloads = {}, {}
    # A single read-only streaming archive pass; only text is retained across members.
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            if member.isdir():
                continue
            identity, kind = base.member_identity(member)
            content = source.extractfile(member).read(member.size + 1)
            require(len(content) == member.size, "member_size_mismatch")
            row = rows.setdefault(identity, {"clip_id": identity})
            if kind == "flac":
                row["audio_sha256"] = hashlib.sha256(content).hexdigest()
            else:
                row["reference_sha256"] = hashlib.sha256(content).hexdigest()
                row["reference"] = content.decode("utf-8-sig").strip()
                payloads[identity] = content
    require(len(rows) == EXPECTED_MEDIASPEECH_CLIPS, "archive_cohort_changed")
    selected = exclude_previous(list(rows.values()), old["clips"])
    require(len(selected) == EXPECTED_MEDIASPEECH_CLIPS - 80, "exclusion_cohort_changed")
    selected.sort(
        key=lambda row: hashlib.sha256(
            ("voiceup-mediaspeech-tr-expanded-v1:" + row["clip_id"]).encode()
        ).hexdigest()
    )
    selected_ids = {row["clip_id"] for row in selected}
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            if not member.isfile() or not member.name.endswith(".flac"):
                continue
            identity, _ = base.member_identity(member)
            if identity in selected_ids:
                base.immutable_write(
                    root / "clips" / (identity + ".flac"), source.extractfile(member).read()
                )
    for row in selected:
        identity = row["clip_id"]
        row["audio"] = f"clips/{identity}.flac"
        row["reference_file"] = f"clips/{identity}.txt"
        base.immutable_write(root / row["reference_file"], payloads[identity])
    manifest = dict(
        schema_version=1,
        protocol="voiceup-mediaspeech-tr-expanded-v1",
        language="tr",
        role="frozen-test",
        dataset="MediaSpeech-TR",
        dataset_revision=base.ARCHIVE_SHA256,
        source_sha256=base.ARCHIVE_SHA256,
        reference_quality="source-human-transcribed",
        speaker_session_labels_available=False,
        selection="all-unseen-clips-exclude-prior-ids-and-audio-hashes-sha256-protocol-order",
        exclusion_manifest_sha256=old_hash,
        clips=selected,
    )
    base.immutable_write(
        root / "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    )
    loaded, manifest_hash = load_manifest(root)
    validate_sources(root, loaded)
    duration = sum(len(base.read_audio(root / row["audio"])[0]) / 16000 for row in selected)
    audit = dict(
        schema_version=1,
        protocol=manifest["protocol"],
        source_sha256=base.ARCHIVE_SHA256,
        exclusion_manifest_sha256=old_hash,
        manifest_sha256=manifest_hash,
        archive_clips=len(rows),
        previous_clips=len(old["clips"]),
        prepared_clips=len(selected),
        excluded_clips=len(rows) - len(selected),
        duration_seconds=duration,
        shared_old_ids=0,
        shared_old_audio_hashes=0,
    )
    base.immutable_write(
        root / "preparation-audit.json", (json.dumps(audit, indent=2) + "\n").encode()
    )
    print(json.dumps(audit, indent=2), flush=True)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare-mediaspeech", "evaluate"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, default=Path("data/turkish/mediaspeech-v1"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--model-manifest", type=Path)
    parser.add_argument("--experiment-id")
    parser.add_argument("--results-md", type=Path, default=Path("results.md"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare-mediaspeech":
        prepare_mediaspeech(args.root, args.original_root)
    else:
        if not all((args.output, args.model_dir, args.model_manifest, args.experiment_id)):
            parser.error("evaluate requires output, model-dir, model-manifest and experiment-id")
        evaluate(args)


def cli():
    try:
        main()
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        AttributeError,
        OverflowError,
        RecursionError,
        RuntimeError,
        tarfile.TarError,
        base.file_helpers.EvaluationError,
    ):
        raise SystemExit(
            "Expanded Turkish ASR incomplete; private evidence retained when available."
        ) from None


if __name__ == "__main__":
    cli()
