"""Validate local pilot dataset readiness without running a model or changing audio."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import numpy as np
import soundfile as sf

MAX_BYTES = 50 * 1024 * 1024
MAX_SECONDS = 120
MAX_DECODED_SAMPLES = 24_000_000
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_RECORDINGS = 500
MAX_ERRORS = 1000
INITIAL_ROLES = {"enrollment", "known_query", "unknown_query"}
LATER_ROLES = {"new_enrollment", "return_query"}
ROLES = INITIAL_ROLES | LATER_ROLES
ENROLLMENT_ROLES = {"enrollment", "new_enrollment"}


class DatasetError(Exception):
    """Stable diagnostic code without a private filesystem path."""


def _phase(*roles: str) -> str:
    return "return" if any(role in LATER_ROLES for role in roles) else "initial"


def _error(report: dict[str, Any], code: str, phase: str, *ids: str) -> None:
    report["errors_total"] += 1
    if phase not in report["invalid_phases"]:
        report["invalid_phases"].append(phase)
    if len(report["errors"]) < MAX_ERRORS:
        report["errors"].append({"code": code, "phase": phase, "recording_ids": list(ids)})
    else:
        report["errors_truncated"] = True


def _report() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dataset_id": None,
        "status": "not_ready",
        "initial_baseline_ready": False,
        "return_phase_ready": False,
        "accuracy_evidence": False,
        "model_executed": False,
        "counts": {},
        "files": [],
        "errors": [],
        "errors_total": 0,
        "errors_truncated": False,
        "invalid_phases": [],
        "limitations": [
            "Duration is total decoded audio, not VAD-confirmed usable speech.",
            "The human single-speaker assertion is not machine verification of speech purity.",
            "Metadata and exact duplicate hashes cannot prove session independence or detect every transformed copy.",
            "Ready means the declared data passes bookkeeping and file checks, not recognition accuracy.",
        ],
    }


def _audio_path(root: Path, value: str) -> Path:
    posix, windows = PurePosixPath(value), PureWindowsPath(value)
    if (
        not value
        or "\\" in value
        or posix.is_absolute()
        or windows.drive
        or ".." in posix.parts
        or "\x00" in value
    ):
        raise DatasetError("unsafe_path")
    try:
        path = (root / value).resolve()
        if not path.is_relative_to(root):
            raise DatasetError("unsafe_path")
        if not path.is_file():
            raise DatasetError("missing_file")
        return path
    except (OSError, ValueError, RuntimeError) as exc:
        raise DatasetError("unsafe_path") from exc


def _inspect_audio(path: Path, role: str) -> dict[str, Any]:
    """Bound both raw byte hashing and decoded blocks; preserve the original file."""
    try:
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > MAX_BYTES:
                raise DatasetError("audio_limit")
            byte_hash = hashlib.sha256()
            size = 0
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise DatasetError("audio_limit")
                byte_hash.update(chunk)
            stream.seek(0)
            with sf.SoundFile(stream) as audio:
                if audio.format not in {"WAV", "FLAC"}:
                    raise DatasetError("unsupported_audio")
                if (
                    not 8000 <= audio.samplerate <= 192000
                    or not 1 <= audio.channels <= 8
                    or audio.frames <= 0
                ):
                    raise DatasetError("invalid_audio")
                duration = audio.frames / audio.samplerate
                if duration > MAX_SECONDS or audio.frames * audio.channels > MAX_DECODED_SAMPLES:
                    raise DatasetError("audio_limit")
                minimum = 10 if role in ENROLLMENT_ROLES else 3
                if duration < minimum - 1e-6:
                    raise DatasetError("duration_too_short")
                pcm_hash = hashlib.sha256(
                    f"pcm-f64le:{audio.samplerate}:{audio.channels}:{audio.frames}:".encode()
                )
                frames = 0
                clipped_samples = 0
                while True:
                    block = audio.read(
                        frames=max(1, 65536 // audio.channels), dtype="float64", always_2d=True
                    )
                    if not len(block):
                        break
                    frames += len(block)
                    if (
                        frames / audio.samplerate > MAX_SECONDS
                        or frames * audio.channels > MAX_DECODED_SAMPLES
                    ):
                        raise DatasetError("audio_limit")
                    if not np.isfinite(block).all():
                        raise DatasetError("invalid_audio")
                    production_pcm = block.astype("float32")
                    if np.max(np.abs(production_pcm)) > 1:
                        raise DatasetError("invalid_audio")
                    clipped_samples += int(np.count_nonzero(np.abs(production_pcm) >= 0.999))
                    block[block == 0] = 0  # Canonicalize negative zero without editing the file.
                    pcm_hash.update(block.astype("<f8", copy=False).tobytes(order="C"))
                if frames != audio.frames:
                    raise DatasetError("invalid_audio")
                clipped_fraction = clipped_samples / (frames * audio.channels)
                if clipped_fraction > 0.05:
                    raise DatasetError("clipped_audio")
                result = {
                    "sha256": byte_hash.hexdigest(),
                    "decoded_pcm_sha256": pcm_hash.hexdigest(),
                    "size_bytes": size,
                    "format": audio.format,
                    "duration_seconds": duration,
                    "sample_rate": audio.samplerate,
                    "channels": audio.channels,
                    "frames": frames,
                    "clipped_fraction": clipped_fraction,
                }
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise DatasetError("file_changed_during_validation")
            return result
    except DatasetError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise DatasetError("invalid_audio") from exc


def validate_dataset(manifest: object, audio_root: Path) -> dict[str, Any]:
    report = _report()
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("schema_version")) is not int
        or manifest.get("schema_version") != 1
        or manifest.get("language") != "tr"
        or not isinstance(manifest.get("dataset_id"), str)
        or not manifest["dataset_id"].strip()
        or not isinstance(manifest.get("recordings"), list)
    ):
        _error(report, "invalid_manifest", "all")
        return report
    report["dataset_id"] = manifest["dataset_id"]
    if len(manifest["recordings"]) > MAX_RECORDINGS:
        _error(report, "manifest_recording_limit", "all")
        return report
    root = audio_root.resolve()
    if not root.is_dir():
        _error(report, "missing_audio_root", "all")
    rows = []
    identifiers = set()
    for row in manifest["recordings"]:
        if (
            not isinstance(row, dict)
            or any(
                not isinstance(row.get(key), str) or not row[key].strip()
                for key in ("id", "speaker_id", "role", "session_id", "source_recording_id", "path")
            )
            or row["role"] not in ROLES
        ):
            _error(report, "invalid_recording", "all")
            continue
        if row["id"] in identifiers:
            _error(report, "duplicate_recording_id", _phase(row["role"]), row["id"])
        identifiers.add(row["id"])
        if row.get("natural_single_speaker") is not True:
            _error(report, "single_speaker_assertion_required", _phase(row["role"]), row["id"])
        rows.append(row)

    enrolled = {row["speaker_id"] for row in rows if row["role"] == "enrollment"}
    unknown = {row["speaker_id"] for row in rows if row["role"] == "unknown_query"}
    known_counts = Counter(row["speaker_id"] for row in rows if row["role"] == "known_query")
    later = {row["speaker_id"] for row in rows if row["role"] == "new_enrollment"}
    returning = {row["speaker_id"] for row in rows if row["role"] == "return_query"}
    if len(enrolled) < 5:
        _error(report, "insufficient_enrolled_speakers", "initial")
    if any(known_counts[speaker] < 3 for speaker in enrolled):
        _error(report, "insufficient_known_queries", "initial")
    if set(known_counts) - enrolled:
        _error(report, "known_query_without_enrollment", "initial")
    if len(unknown) < 2 or sum(row["role"] == "unknown_query" for row in rows) < 10:
        _error(report, "insufficient_unknown_queries", "initial")
    if unknown & enrolled:
        _error(report, "unknown_is_enrolled", "initial")
    if not later or later - unknown:
        _error(report, "new_enrollment_requires_initial_unknown", "return")
    if not returning or later - returning or returning - later:
        _error(report, "return_query_requires_new_enrollment", "return")

    for index, first in enumerate(rows):
        for second in rows[index + 1 :]:
            if first["role"] == second["role"]:
                continue
            if (
                first["speaker_id"] == second["speaker_id"]
                and first["session_id"] == second["session_id"]
            ) or first["source_recording_id"] == second["source_recording_id"]:
                _error(
                    report,
                    "split_leakage",
                    _phase(first["role"], second["role"]),
                    first["id"],
                    second["id"],
                )

    seen_paths: dict[Path, dict[str, str]] = {}
    seen_bytes: dict[str, dict[str, str]] = {}
    seen_pcm: dict[str, dict[str, str]] = {}
    checked = 0
    for row in rows:
        phase = _phase(row["role"])
        try:
            path = _audio_path(root, row["path"])
            checked += 1
            prior = seen_paths.get(path)
            if prior:
                _error(
                    report,
                    "duplicate_path",
                    _phase(prior["role"], row["role"]),
                    prior["id"],
                    row["id"],
                )
            if prior is None or row["role"] in INITIAL_ROLES:
                seen_paths[path] = row
            evidence = _inspect_audio(path, row["role"])
            for key, seen, code in (
                ("sha256", seen_bytes, "duplicate_bytes"),
                ("decoded_pcm_sha256", seen_pcm, "duplicate_pcm"),
            ):
                prior = seen.get(evidence[key])
                if prior:
                    _error(report, code, _phase(prior["role"], row["role"]), prior["id"], row["id"])
                if prior is None or row["role"] in INITIAL_ROLES:
                    seen[evidence[key]] = row
            report["files"].append({"recording_id": row["id"], **evidence})
        except DatasetError as exc:
            _error(report, str(exc), phase, row["id"])
    report["counts"] = {
        "recordings_declared": len(manifest["recordings"]),
        "enrolled_speakers": len(enrolled),
        "known_queries": sum(known_counts.values()),
        "unknown_speakers": len(unknown),
        "unknown_queries": sum(row["role"] == "unknown_query" for row in rows),
        "new_enrolled_speakers": len(later),
        "return_queries": sum(row["role"] == "return_query" for row in rows),
        "files_checked": checked,
    }
    report["initial_baseline_ready"] = not ({"initial", "all"} & set(report["invalid_phases"]))
    report["return_phase_ready"] = not ({"return", "all"} & set(report["invalid_phases"]))
    if report["initial_baseline_ready"] and report["return_phase_ready"]:
        report["status"] = "ready"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="Use a private ignored outputs/ path"
    )
    args = parser.parse_args(argv)
    manifest = None
    try:
        with args.manifest.open("rb") as source:
            manifest_bytes = source.read(MAX_MANIFEST_BYTES + 1)
        if len(manifest_bytes) > MAX_MANIFEST_BYTES:
            raise DatasetError("manifest_size_limit")
        manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
        report = validate_dataset(manifest, args.audio_root)
    except DatasetError as exc:
        report = _report()
        _error(report, str(exc), "all")
    except (OSError, ValueError, RuntimeError):
        report = _report()
        _error(report, "unreadable_manifest_or_audio_root", "all")
    # Never overwrite the manifest or any source recording, including through a symlink.
    output = args.output.resolve()
    protected = {args.manifest.resolve()}
    if isinstance(manifest, dict) and isinstance(manifest.get("recordings"), list):
        for row in manifest["recordings"]:
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                try:
                    protected.add((args.audio_root / row["path"]).resolve())
                except (OSError, ValueError, RuntimeError):
                    pass
    try:
        if output in protected or (
            output.exists()
            and any(source.exists() and output.samefile(source) for source in protected)
        ):
            print("not_ready: output_would_overwrite_input")
            return 1
        if output.suffix.lower() != ".json":
            print("not_ready: json_output_required")
            return 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    except OSError:
        print("not_ready: output_unavailable")
        return 1
    print(report["status"])
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
