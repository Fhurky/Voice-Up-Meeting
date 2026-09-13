"""Prepare MediaSpeech Turkish explicitly, then evaluate the local pinned ASR offline.

Clip-disjoint subsets do not imply speaker/session-disjoint sources: the archive
does not supply those labels. Outputs contain private text; publish aggregates only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import tarfile
import time
import urllib.request
from datetime import UTC, datetime
from contextlib import ExitStack, contextmanager
from pathlib import Path

URL = "https://www.openslr.org/resources/108/TR.tgz"
ARCHIVE_BYTES = 618578461
# Observed official HTTPS archive bytes, not a publisher-supplied checksum.
ARCHIVE_SHA256 = "c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c"
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
SEED = "voiceup-mediaspeech-tr-v1"
MODEL_REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"


def _existing_file_helpers():
    spec = importlib.util.spec_from_file_location(
        "turkish_asr_file_helpers", Path(__file__).with_name("evaluate-public-speakers.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


file_helpers = _existing_file_helpers()


def safe_path(path):
    path = Path(path).absolute()
    if any(
        p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)
    ):
        raise ValueError("linked_path_refused")
    return path


def digest(path):
    with safe_path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def immutable_write(path, content):
    path = safe_path(path)
    if path.exists():
        if path.stat().st_size != len(content) or path.read_bytes() != content:
            raise ValueError("existing_file_conflict")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def load_manifest(root):
    def unique_fields(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate_manifest_field")
            value[key] = item
        return value

    def reject_constant(_value):
        raise ValueError("invalid_manifest_number")

    with safe_path(Path(root) / "manifest.json").open("rb") as stream:
        payload = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(payload) > MAX_MANIFEST_BYTES:
        raise ValueError("manifest_limit")
    value = json.loads(payload, object_pairs_hook=unique_fields, parse_constant=reject_constant)
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema_version",
            "protocol",
            "language",
            "source_url",
            "archive_sha256",
            "archive_bytes",
            "reference_quality",
            "selection",
            "speaker_session_labels_available",
            "clips",
        }
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["protocol"] != SEED
        or value["language"] != "tr"
        or value["source_url"] != URL
        or value["archive_sha256"] != ARCHIVE_SHA256
        or value["archive_bytes"] != ARCHIVE_BYTES
        or value["reference_quality"] != "source-human-transcribed"
        or value["selection"] != "sha256-seed-order-clip-disjoint"
        or value["speaker_session_labels_available"] is not False
        or not isinstance(value["clips"], list)
        or not 2 <= len(value["clips"]) <= 2000
        or len(value["clips"]) % 2
    ):
        raise ValueError("invalid_manifest")
    identities, hashes = [], set()
    for row in value["clips"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"clip_id", "role", "flac_sha256", "txt_sha256", "reference"}
            or not isinstance(row["clip_id"], str)
            or re.fullmatch(r"[a-f0-9-]{36}", row["clip_id"]) is None
            or row["role"] not in {"calibration", "frozen-test"}
            or not isinstance(row["reference"], str)
            or not row["reference"].strip()
            or len(row["reference"]) > 500_000
            or any(
                not isinstance(row[key], str) or re.fullmatch(r"[a-f0-9]{64}", row[key]) is None
                for key in ("flac_sha256", "txt_sha256")
            )
        ):
            raise ValueError("invalid_manifest_clip")
        if row["clip_id"] in identities or row["flac_sha256"] in hashes:
            raise ValueError("duplicate_manifest_audio")
        identities.append(row["clip_id"])
        hashes.add(row["flac_sha256"])
    count = len(identities) // 2
    development, held_out = select_clips(identities, count)
    if (
        identities != development + held_out
        or [row["role"] for row in value["clips"]]
        != ["calibration"] * count + ["frozen-test"] * count
    ):
        raise ValueError("manifest_selection_changed")
    return value, hashlib.sha256(payload).hexdigest()


def evaluation_paths(args, rows):
    root, models = safe_path(args.root), safe_path(args.model_dir)
    output = safe_path(args.output)
    public = safe_path(output.with_name(output.stem + ".aggregate.json"))
    ledger = safe_path(args.results_md)
    protected = {
        safe_path(root / "manifest.json"),
        safe_path(args.model_manifest),
        safe_path(Path(__file__)),
        safe_path(root / "TR.tgz"),
    }
    protected.update(
        safe_path(root / "clips" / (row["clip_id"] + "." + kind))
        for row in rows
        for kind in ("flac", "txt")
    )
    if output.suffix.lower() != ".json" or ledger.suffix.lower() != ".md":
        raise ValueError("invalid_evidence_path")
    destinations = (output, public, ledger)
    for path in destinations:
        if (
            path.resolve().is_relative_to(root.resolve())
            or path.resolve().is_relative_to(models.resolve())
            or any(
                path.resolve() == source.resolve()
                or (path.exists() and source.exists() and path.samefile(source))
                for source in protected
            )
            or (path.exists() and (not path.is_file() or path.stat().st_nlink > 1))
        ):
            raise ValueError("evidence_source_conflict")
    for index, path in enumerate(destinations):
        if any(
            path.resolve() == other.resolve()
            or (path.exists() and other.exists() and path.samefile(other))
            for other in destinations[index + 1 :]
        ):
            raise ValueError("aliased_evidence_paths")
    for path in (output, public):
        lock = safe_path(path.with_suffix(path.suffix + ".lock"))
        if lock.exists() and (not lock.is_file() or lock.stat().st_nlink > 1):
            raise ValueError("linked_evaluation_lock")
    return output, public


@contextmanager
def evaluation_lock(output, public):
    with ExitStack() as locks:
        for path in sorted((output, public), key=lambda path: str(path.resolve())):
            locks.enter_context(file_helpers.state_lock(path))
        if output.exists() or public.exists():
            raise ValueError("output_exists")
        yield


def save_checkpoint(output, report):
    output = safe_path(output)
    if output.exists() and (not output.is_file() or output.stat().st_nlink > 1):
        raise ValueError("linked_checkpoint")
    file_helpers.atomic_json(output, report)


def read_audio(path):
    import numpy as np
    import soundfile as sf

    with sf.SoundFile(safe_path(path)) as audio:
        rate, frames = audio.samplerate, audio.frames
        if rate != 16000 or audio.channels != 1 or not 0 < frames <= 60 * rate:
            raise ValueError("invalid_audio")
        samples = audio.read(frames=frames + 1, dtype="float32")
    if samples.ndim != 1 or len(samples) != frames or not np.isfinite(samples).all():
        raise ValueError("invalid_audio")
    return samples, rate


def member_identity(member):
    match = re.fullmatch(r"TR/([a-f0-9-]{36})\.(flac|txt)", member.name)
    if not match or not member.isfile() or not 0 < member.size <= 2 * 1024 * 1024:
        raise ValueError("unsafe_archive_member")
    return match.group(1), match.group(2)


def index_archive(path):
    found = {}
    with tarfile.open(safe_path(path), "r:gz") as archive:
        for member in archive:
            if member.isdir() and member.name.rstrip("/") == "TR":
                continue
            identity, kind = member_identity(member)
            if (identity, kind) in found:
                raise ValueError("duplicate_archive_member")
            found[(identity, kind)] = member.name
            if len(found) > 20000:
                raise ValueError("archive_member_limit")
    if {i for i, k in found if k == "flac"} != {i for i, k in found if k == "txt"}:
        raise ValueError("missing_paired_reference")
    return found


def select_clips(identities, count):
    if not 1 <= count <= 1000 or len(set(identities)) < 2 * count:
        raise ValueError("insufficient_selection")
    ordered = sorted(
        set(identities), key=lambda x: hashlib.sha256((SEED + ":" + x).encode()).hexdigest()
    )
    return ordered[:count], ordered[count : 2 * count]


def prepare(root, *, download, count):
    root = safe_path(root)
    archive = root / "TR.tgz"
    if not archive.exists():
        if not download:
            raise ValueError("explicit_download_required")
        partial = safe_path(root / "TR.tgz.part")
        root.mkdir(parents=True, exist_ok=True)
        with partial.open("xb") as target, urllib.request.urlopen(URL, timeout=60) as response:
            if int(response.headers.get("Content-Length", 0)) != ARCHIVE_BYTES:
                raise ValueError("source_size_changed")
            received = 0
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > ARCHIVE_BYTES:
                    raise ValueError("download_limit")
                target.write(chunk)
        if received != ARCHIVE_BYTES:
            raise ValueError("incomplete_download")
        os.replace(partial, archive)
    if archive.stat().st_size != ARCHIVE_BYTES:
        raise ValueError("archive_size_mismatch")
    archive_hash = digest(archive)
    if archive_hash != ARCHIVE_SHA256:
        raise ValueError("archive_revision_changed")
    members = index_archive(archive)
    dev, test = select_clips([i for i, kind in members if kind == "flac"], count)
    selected = set(dev + test)
    rows = {}
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            if member.isdir():
                continue
            identity, kind = member_identity(member)
            if identity not in selected:
                continue
            content = source.extractfile(member).read(member.size + 1)
            if len(content) != member.size:
                raise ValueError("member_size_mismatch")
            path = root / "clips" / (identity + "." + kind)
            immutable_write(path, content)
            row = rows.setdefault(
                identity,
                {"clip_id": identity, "role": "calibration" if identity in dev else "frozen-test"},
            )
            row[kind + "_sha256"] = hashlib.sha256(content).hexdigest()
            if kind == "txt":
                row["reference"] = content.decode("utf-8-sig").strip()
    manifest = {
        "schema_version": 1,
        "protocol": SEED,
        "language": "tr",
        "source_url": URL,
        "archive_sha256": archive_hash,
        "archive_bytes": ARCHIVE_BYTES,
        "reference_quality": "source-human-transcribed",
        "selection": "sha256-seed-order-clip-disjoint",
        "speaker_session_labels_available": False,
        "clips": [rows[i] for i in dev + test],
    }
    immutable_write(
        root / "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    )
    print(
        f"Prepared {count} development and {count} held-out clips; archive SHA256 {archive_hash}",
        flush=True,
    )


def evaluate(args):
    source_hash = digest(Path(__file__))
    root = safe_path(args.root)
    manifest, manifest_hash = load_manifest(root)
    output, public_path = evaluation_paths(args, manifest["clips"])
    if args.role not in {"calibration", "frozen-test"} or args.language not in {"tr", "auto"}:
        raise ValueError("invalid_evaluation_mode")
    with evaluation_lock(output, public_path):
        evaluation_paths(args, manifest["clips"])
        return _evaluate(args, root, manifest, manifest_hash, output, public_path, source_hash)


def _evaluate(args, root, manifest, manifest_hash, output, public_path, source_hash):
    # Imports stay after preparation: download needs only the standard library.
    from faster_whisper import WhisperModel
    from voiceup.meeting_metrics import score_transcript
    from voiceup_inference.meeting_models import (
        ASR_FILES,
        ASR_ID,
        ASR_REVISION,
        verify_meeting_bundle,
    )

    rows = [r for r in manifest["clips"] if r["role"] == args.role]
    report = {
        "schema_version": 1,
        "protocol": SEED,
        "status": "incomplete",
        "language": "tr",
        "language_mode": args.language,
        "role": args.role,
        "model_id": ASR_ID,
        "model_revision": ASR_REVISION,
        "manifest_sha256": manifest_hash,
        "evaluation_source_sha256": source_hash,
        "planned_clips": len(rows),
        "archive_sha256": manifest["archive_sha256"],
        "clips": [],
    }
    start = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        save_checkpoint(output, report)

    try:
        verify_meeting_bundle(args.model_dir, args.model_manifest, ASR_ID, ASR_REVISION, ASR_FILES)
        model = WhisperModel(
            str(args.model_dir),
            device="cuda",
            device_index=0,
            compute_type="int8_float16",
            cpu_threads=4,
            num_workers=1,
            local_files_only=True,
        )
        for row in rows:
            if re.fullmatch(r"[a-f0-9-]{36}", row["clip_id"]) is None:
                raise ValueError("invalid_clip")
            path = root / "clips" / (row["clip_id"] + ".flac")
            if digest(path) != row["flac_sha256"]:
                raise ValueError("audio_changed")
            reference_path = root / "clips" / (row["clip_id"] + ".txt")
            if (
                digest(reference_path) != row["txt_sha256"]
                or reference_path.read_text(encoding="utf-8-sig").strip() != row["reference"]
            ):
                raise ValueError("reference_changed")
            samples, rate = read_audio(path)
            segments, info = model.transcribe(
                samples,
                language="tr" if args.language == "tr" else None,
                beam_size=5,
                word_timestamps=True,
                condition_on_previous_text=False,
                vad_filter=False,
            )
            hypothesis = " ".join(segment.text for segment in segments)
            metric = score_transcript(
                {"reference": row["reference"]},
                {"hypothesis": hypothesis},
                normalization="turkish-words-v1",
            )
            for key in ("cpwer", "assigned_only"):
                metric[key].pop("assignment", None)
            report["clips"].append(
                {
                    "source_sha256": row["flac_sha256"],
                    "duration_seconds": len(samples) / rate,
                    "detected_language": info.language,
                    "metrics": metric,
                    "reference": row["reference"],
                    "hypothesis": hypothesis,
                }
            )
            save()
            print(f"ASR {len(report['clips'])}/{len(rows)}", flush=True)
        report["status"] = "complete"
    finally:
        report["elapsed_seconds"] = time.monotonic() - start
        save()
        from experiment_ledger import record_experiment

        public = aggregate(report)
        immutable_write(public_path, (json.dumps(public, indent=2) + "\n").encode())
        configuration = {
            "language": args.language,
            "beam_size": 5,
            "word_timestamps": True,
            "condition_on_previous_text": False,
            "vad_filter": False,
            "compute_type": "int8_float16",
            "evaluation_source_sha256": source_hash,
        }
        metadata = {
            "date": datetime.now(UTC).date().isoformat(),
            "dataset": "MediaSpeech-TR",
            "dataset_revision": manifest["archive_sha256"],
            "language": "tr",
            "role": args.role,
            "pipeline": "meeting-asr",
            "protocol_sha256": manifest_hash,
            "configuration_sha256": hashlib.sha256(
                json.dumps(configuration, sort_keys=True).encode()
            ).hexdigest(),
            "elapsed_seconds": report["elapsed_seconds"],
            "models": [{"id": ASR_ID, "revision": ASR_REVISION}],
        }
        record_experiment(
            args.results_md,
            experiment_id=args.experiment_id,
            metadata=metadata,
            report=public,
            kind="asr_clips",
        )


def aggregate(report):
    rows = report["clips"]
    complete = report["status"] == "complete" and len(rows) == report["planned_clips"]
    result = {
        "protocol": SEED,
        "status": "complete" if complete else "incomplete",
        "normalization": "turkish-words-v1",
        "input_sha256": report["manifest_sha256"],
        "source_sha256": report["archive_sha256"],
        "planned_clips": report["planned_clips"],
        "observed_clips": len(rows),
    }
    for key in ("reference_words", "hypothesis_words"):
        result[key] = sum(row["metrics"]["counts"][key] for row in rows)
    for key in ("errors", "substitutions", "deletions", "insertions"):
        result[key] = sum(row["metrics"]["cpwer"][key] for row in rows)
    result["wer"] = (
        result["errors"] / result["reference_words"]
        if complete and result["reference_words"]
        else None
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "evaluate"])
    parser.add_argument("--root", type=Path, default=Path("data/turkish/mediaspeech-v1"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--role", choices=["calibration", "frozen-test"], default="calibration")
    parser.add_argument("--language", choices=["tr", "auto"], default="tr")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--model-manifest", type=Path)
    parser.add_argument("--experiment-id")
    parser.add_argument("--results-md", type=Path, default=Path("results.md"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.root, download=args.download, count=args.count)
    else:
        if not all([args.output, args.model_dir, args.model_manifest, args.experiment_id]):
            parser.error("evaluate requires output, model-dir, model-manifest and experiment-id")
        evaluate(args)


if __name__ == "__main__":
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
        tarfile.TarError,
        file_helpers.EvaluationError,
    ):
        raise SystemExit(
            "Turkish ASR preparation/evaluation incomplete; private evidence retained when available."
        ) from None
