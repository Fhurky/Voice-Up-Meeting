"""Evaluate frozen speaker decisions through the public API in an isolated tenant."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from uuid import UUID, uuid4


def _benchmark_module():
    path = Path(__file__).with_name("benchmark-local-pilot.py")
    spec = importlib.util.spec_from_file_location("voiceup_public_benchmark", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark = _benchmark_module()
MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
MODEL_REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"
POLICY = {"match_threshold": 0.75, "new_threshold": 0.45, "margin": 0.10}
ROLES = {"enrollment", "known_query", "unknown_query", "new_enrollment", "return_query"}
TERMINAL = {"succeeded", "failed"}
MAX_AUDIO_BYTES = 50 * 1024 * 1024
# Offline evaluation resource bounds, not product capacity or accuracy guarantees.
MAX_MANIFEST_PEOPLE_PER_ROLE = 200
MAX_RECORDINGS = 1500
MAX_OPERATIONS = 20000
PREPROCESSING_VERSIONS = ("vad-windows-v1", "vad-packed-fallback-v1")


class EvaluationError(Exception):
    """A stable code, never a credential, private path, or downstream payload."""


class ProfileLimitRejected(EvaluationError):
    """The API rejected a new profile before allocating a job."""


class CapacityConflictHandler(urllib.request.BaseHandler):
    """Read only a bounded, exact capacity code; never expose an HTTP error body."""

    def http_error_409(self, request, response, _code, _message, _headers):
        def unique_fields(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate_field")
                result[key] = value
            return result

        def invalid_constant(_value):
            raise ValueError("invalid_json_constant")

        try:
            body = json.loads(request.data or b"null")
            payload = response.read(16385)
            if (
                request.get_method() == "POST"
                and request.selector == "/api/voiceup/v1/speaker-jobs"
                and isinstance(body, dict)
                and set(body) == {"recording_public_id", "purpose", "name"}
                and body["purpose"] == "enroll"
                and len(payload) <= 16384
            ):
                error = json.loads(
                    payload, object_pairs_hook=unique_fields, parse_constant=invalid_constant
                )
                detail = error.get("detail") if isinstance(error, dict) else None
                if isinstance(detail, dict) and detail.get("code") == "profile_limit":
                    raise ProfileLimitRejected("profile_limit")
        except (ValueError, TypeError, RecursionError):
            pass
        finally:
            response.close()
        raise benchmark.BenchmarkFailure("http_409")


class EvaluationApi(benchmark.Api):
    def __init__(self, origin: str, prefix: str):
        super().__init__(origin, prefix)
        self.opener.add_handler(CapacityConflictHandler())


def now() -> str:
    return datetime.now(UTC).isoformat()


def operation_key(run_id: str, operation: str) -> str:
    return "public-eval-" + hashlib.sha256(f"{run_id}:{operation}".encode()).hexdigest()


def validate_policy(value: Any) -> dict[str, float]:
    if (
        not isinstance(value, dict)
        or set(value) != {"match_threshold", "new_threshold", "margin"}
        or any(type(number) not in (float, int) for number in value.values())
    ):
        raise EvaluationError("invalid_frozen_policy")
    try:
        policy = {key: float(number) for key, number in value.items()}
    except (OverflowError, ValueError):
        raise EvaluationError("invalid_frozen_policy") from None
    if (
        not all(math.isfinite(number) for number in policy.values())
        or not -1 <= policy["new_threshold"] < policy["match_threshold"] <= 1
        or not 0 <= policy["margin"] <= 2
    ):
        raise EvaluationError("invalid_frozen_policy")
    return policy


def read_json(path: Path, maximum: int = 16 * 1024 * 1024) -> Any:
    with path.open("rb") as source:
        payload = source.read(maximum + 1)
    if len(payload) > maximum:
        raise EvaluationError("json_input_limit")
    return json.loads(payload.decode("utf-8-sig"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as target:
            json.dump(value, target, ensure_ascii=False, indent=2, allow_nan=False)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def check_output_paths(output: Path, state: Path, protected: set[Path]) -> None:
    destinations = [output.resolve(), state.resolve()]
    protected = {path.resolve() for path in protected}
    if destinations[0] == destinations[1]:
        raise EvaluationError("output_and_state_must_differ")
    for original, path in zip((output, state), destinations):
        if original.is_symlink() or path.suffix.lower() != ".json":
            raise EvaluationError("invalid_output_path")
        if path in protected or (
            path.exists() and any(source.exists() and path.samefile(source) for source in protected)
        ):
            raise EvaluationError("output_would_overwrite_input")


@contextmanager
def state_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise EvaluationError("evaluation_already_running") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 250


def audio_path(root: Path, value: Any) -> Path:
    if (
        not _text(value)
        or "\\" in value
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).drive
        or ".." in PurePosixPath(value).parts
        or "\x00" in value
    ):
        raise EvaluationError("unsafe_audio_path")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise EvaluationError("unsafe_audio_path")
    return path


def validate_manifest(manifest: Any, audio_root: Path, gallery_sizes: list[int]) -> None:
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
        or not _text(manifest.get("dataset_id"))
        or manifest.get("language") != "en"
        or manifest.get("split") not in {"calibration", "test"}
        or not isinstance(manifest.get("recordings"), list)
        or not 1 <= len(manifest["recordings"]) <= MAX_RECORDINGS
    ):
        raise EvaluationError("invalid_manifest")
    gallery = manifest.get("gallery_order")
    if (
        not isinstance(gallery, list)
        or not 1 <= len(gallery) <= MAX_MANIFEST_PEOPLE_PER_ROLE
        or not all(_text(item) for item in gallery)
        or len(set(gallery)) != len(gallery)
    ):
        raise EvaluationError("invalid_gallery_order")
    declared_unknown = manifest.get("unknown_order")
    if (
        not isinstance(declared_unknown, list)
        or not 1 <= len(declared_unknown) <= MAX_MANIFEST_PEOPLE_PER_ROLE
        or not all(_text(item) for item in declared_unknown)
        or len(set(declared_unknown)) != len(declared_unknown)
    ):
        raise EvaluationError("invalid_unknown_order")
    if (
        not gallery_sizes
        or any(type(size) is not int or not 1 <= size <= len(gallery) for size in gallery_sizes)
        or gallery_sizes != sorted(set(gallery_sizes))
    ):
        raise EvaluationError("invalid_gallery_sizes")
    identifiers: set[str] = set()
    paths: set[Path] = set()
    hashes: set[str] = set()
    utterances: set[str] = set()
    chapter_roles: dict[tuple[str, str, str], set[str]] = {}
    counts: Counter = Counter()
    speakers: dict[str, set[str]] = {role: set() for role in ROLES}
    for row in manifest["recordings"]:
        if (
            not isinstance(row, dict)
            or any(
                not _text(row.get(key))
                for key in ("id", "speaker_id", "source_split", "chapter_id", "path")
            )
            or row.get("role") not in ROLES
            or not isinstance(row.get("source_utterance_ids"), list)
            or not row["source_utterance_ids"]
            or not all(_text(item) for item in row["source_utterance_ids"])
            or not isinstance(row.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
            or type(row.get("duration_seconds")) not in (int, float)
            or not math.isfinite(row["duration_seconds"])
            or not 0 < row["duration_seconds"] <= 120
        ):
            raise EvaluationError("invalid_recording")
        if row["id"] in identifiers:
            raise EvaluationError("duplicate_recording_id")
        identifiers.add(row["id"])
        for identifier in row["source_utterance_ids"]:
            if identifier in utterances:
                raise EvaluationError("duplicate_source_utterance")
            utterances.add(identifier)
        chapter_key = (row["speaker_id"], row["source_split"], row["chapter_id"])
        chapter_roles.setdefault(chapter_key, set()).add(row["role"])
        if len(chapter_roles[chapter_key]) > 1:
            raise EvaluationError("source_role_leakage")
        path = audio_path(audio_root, row["path"])
        if path in paths or row["sha256"] in hashes:
            raise EvaluationError("duplicate_audio")
        paths.add(path)
        hashes.add(row["sha256"])
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            if not 0 < before.st_size <= MAX_AUDIO_BYTES:
                raise EvaluationError("audio_size_limit")
            hasher = hashlib.sha256()
            size = 0
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_AUDIO_BYTES:
                    raise EvaluationError("audio_size_limit")
                hasher.update(chunk)
            digest = hasher.hexdigest()
            after = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise EvaluationError("audio_changed_during_preflight")
        if digest != row["sha256"]:
            raise EvaluationError("audio_hash_mismatch")
        speakers[row["role"]].add(row["speaker_id"])
        counts[row["speaker_id"], row["role"]] += 1
    if speakers["enrollment"] != set(gallery) or speakers["known_query"] != set(gallery):
        raise EvaluationError("gallery_recordings_mismatch")
    if any(
        counts[speaker, "enrollment"] != 1 or counts[speaker, "known_query"] < 3
        for speaker in gallery
    ):
        raise EvaluationError("insufficient_gallery_recordings")
    unknown = speakers["unknown_query"]
    if unknown != set(declared_unknown):
        raise EvaluationError("unknown_recordings_mismatch")
    if not unknown or unknown & set(gallery):
        raise EvaluationError("unknown_gallery_overlap")
    later = speakers["new_enrollment"]
    if not later or later - unknown or later != speakers["return_query"]:
        raise EvaluationError("invalid_return_phase")
    if any(counts[speaker, "new_enrollment"] != 1 for speaker in later):
        raise EvaluationError("duplicate_new_enrollment")
    unknown_queries = sum(counts[speaker, "unknown_query"] for speaker in unknown)
    planned_operations = (
        max(gallery_sizes)
        + sum(
            count
            for (_speaker, role), count in counts.items()
            if role in {"new_enrollment", "return_query"}
        )
        + sum(
            unknown_queries + sum(counts[speaker, "known_query"] for speaker in gallery[:size])
            for size in gallery_sizes
        )
    )
    if planned_operations > MAX_OPERATIONS:
        raise EvaluationError("operation_limit")


def validate_preprocessing_result(result: Any, versions: list[str]) -> None:
    version = result.get("preprocessing_version") if isinstance(result, dict) else None
    if not isinstance(version, str) or version not in versions:
        raise EvaluationError("frozen_inference_contract_changed")


def validate_state(state: Any, binding: dict) -> None:
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != 1
        or state.get("binding") != binding
        or not _text(state.get("run_id"))
        or not isinstance(state.get("operations"), dict)
        or not isinstance(state.get("uploads"), dict)
        or not isinstance(state.get("expected_profiles"), list)
    ):
        raise EvaluationError("resume_binding_mismatch")
    if "required_preprocessing_versions" in binding:
        for operation in state["operations"].values():
            if operation.get("status") == "succeeded":
                validate_preprocessing_result(
                    operation.get("result"), binding["required_preprocessing_versions"]
                )


def wilson_interval(successes: int, total: int) -> dict[str, float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    ratio = successes / total
    denominator = 1 + z * z / total
    center = (ratio + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(ratio * (1 - ratio) / total + z * z / (4 * total * total)) / denominator
    return {
        "lower": 0.0 if successes == 0 else max(0.0, center - radius),
        "upper": 1.0 if successes == total else min(1.0, center + radius),
    }


def summarize_probes(records: list[dict], *, known_planned: int, unknown_planned: int) -> dict:
    counts = {
        f"{kind}_{suffix}": 0
        for kind in ("known", "unknown")
        for suffix in ("completed", "job_failed", "recognized", "unknown", "ambiguous")
    }
    counts.update(
        known_planned=known_planned,
        unknown_planned=unknown_planned,
        known_correct=0,
        known_wrong=0,
        known_rejected=0,
        unknown_false_accepted=0,
    )
    errors: Counter = Counter()
    for record in records:
        kind = record["kind"]
        counts[f"{kind}_completed"] += 1
        if record["status"] == "failed":
            counts[f"{kind}_job_failed"] += 1
            errors[record.get("error_code", "unknown")] += 1
            continue
        decision = record["decision"]
        counts[f"{kind}_{decision}"] += 1
        if kind == "unknown":
            counts["unknown_false_accepted"] += int(decision == "recognized")
        elif decision == "recognized":
            field = (
                "known_correct"
                if record["predicted_speaker_id"] == record["speaker_id"]
                else "known_wrong"
            )
            counts[field] += 1
        else:
            counts["known_rejected"] += 1
    for kind, planned in (("known", known_planned), ("unknown", unknown_planned)):
        counts[f"{kind}_not_run"] = planned - counts[f"{kind}_completed"]
        if counts[f"{kind}_not_run"] < 0:
            raise EvaluationError("duplicate_probe_accounting")
    missing_unknown = counts["unknown_job_failed"] + counts["unknown_not_run"]

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    return {
        "counts": counts,
        "error_counts": dict(errors),
        "complete_decisions": not any(
            counts[f"{kind}_{suffix}"]
            for kind in ("known", "unknown")
            for suffix in ("job_failed", "not_run")
        ),
        "rates": {
            "DIR": ratio(counts["known_correct"], known_planned),
            "known_misidentification": ratio(counts["known_wrong"], known_planned),
            "FPIR_observed_lower_bound": ratio(counts["unknown_false_accepted"], unknown_planned),
            "FPIR_worst_case_upper_bound": ratio(
                counts["unknown_false_accepted"] + missing_unknown, unknown_planned
            ),
            "unknown_detection_recall": ratio(counts["unknown_unknown"], unknown_planned),
        },
        "wilson_95_probe_intervals": {
            "DIR": wilson_interval(counts["known_correct"], known_planned),
            "FPIR_observed_lower_bound": wilson_interval(
                counts["unknown_false_accepted"], unknown_planned
            ),
        },
        "limitations": [
            "Wilson intervals assume independent probes; shared speakers and chapters make these descriptive, not population guarantees.",
            "Known quality errors and unrun probes remain in the planned DIR denominator.",
            "Unknown errors and unrun probes are not successful rejections; FPIR reports observed and worst-case bounds.",
            "English read speech and assembled clips do not establish Turkish meeting or recording-session generalization.",
        ],
    }


class Evaluator:
    def __init__(
        self,
        *,
        manifest: dict,
        audio_root: Path,
        credentials: dict,
        state: dict,
        state_path: Path,
        output: Path,
        job_timeout: float = 660,
        poll_seconds: float = 0.5,
        api=None,
    ):
        self.manifest, self.audio_root, self.credentials = manifest, audio_root, credentials
        self.state, self.state_path, self.output = state, state_path, output
        self.policy = validate_policy(state["binding"]["policy"])
        self.job_timeout, self.poll_seconds = job_timeout, poll_seconds
        self.api = api or EvaluationApi(credentials["url"], "/api/voiceup/v1")
        self.rows = {row["id"]: row for row in manifest["recordings"]}

    def login(self) -> None:
        authenticated = self.api.json(
            "/auth/login",
            {"username": self.credentials["username"], "password": self.credentials["password"]},
        )
        if str(authenticated.get("user", {}).get("tenant_id")) != self.credentials["tenant_id"]:
            raise EvaluationError("authenticated_tenant_mismatch")
        token = authenticated.get("access_token")
        if not _text(token) and not (isinstance(token, str) and 1 <= len(token) <= 16000):
            raise EvaluationError("invalid_authentication_response")
        self.api.headers = {
            "Authorization": "Bearer " + token,
            "x-tenant-id": self.credentials["tenant_id"],
        }

    def request(self, method: str, path: str, **kwargs) -> dict:
        try:
            return self.api.request(method, path, **kwargs)
        except benchmark.BenchmarkFailure as exc:
            if str(exc) != "http_401":
                raise EvaluationError(str(exc)) from None
            self.login()
            try:
                return self.api.request(method, path, **kwargs)
            except benchmark.BenchmarkFailure as retry:
                raise EvaluationError(str(retry)) from None

    def post(self, path: str, body: dict, key: str) -> dict:
        return self.request(
            "POST",
            path,
            payload=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Idempotency-Key": key},
        )

    def profiles(self) -> list[dict]:
        result = []
        offset = 0
        planned_profiles = max(self.state["binding"]["gallery_sizes"]) + sum(
            row["role"] == "new_enrollment" for row in self.rows.values()
        )
        while True:
            page = self.request("GET", f"/speaker-profiles?offset={offset}&limit=100")
            if not isinstance(page.get("items"), list) or type(page.get("total")) is not int:
                raise EvaluationError("invalid_profile_page")
            if not 0 <= page["total"] <= planned_profiles:
                raise EvaluationError("unexpected_gallery_size")
            result.extend(page["items"])
            offset += len(page["items"])
            if offset >= page["total"]:
                break
            if not page["items"]:
                raise EvaluationError("incomplete_profile_page")
        if len({item["public_id"] for item in result}) != len(result):
            raise EvaluationError("duplicate_profile_response")
        return sorted(result, key=lambda item: item["public_id"])

    def assert_gallery(self) -> None:
        if self.profiles() != self.state["expected_profiles"]:
            raise EvaluationError("evaluation_gallery_changed")

    def profile_map(self) -> dict[str, str]:
        return {
            operation["result"]["profile_public_id"]: operation["speaker_id"]
            for operation in self.state["operations"].values()
            if operation.get("purpose") == "enroll" and operation.get("status") == "succeeded"
        }

    def report(self) -> dict:
        stages = []
        operations = list(self.state["operations"].values())
        for size in self.state["binding"]["gallery_sizes"]:
            gallery = set(self.manifest["gallery_order"][:size])
            probes = [
                item
                for item in operations
                if item.get("stage") == size
                and item.get("purpose") == "identify"
                and item.get("status") in TERMINAL
            ]
            known_count = sum(
                row["role"] == "known_query" and row["speaker_id"] in gallery
                for row in self.rows.values()
            )
            unknown_count = sum(row["role"] == "unknown_query" for row in self.rows.values())
            enrollment = [
                item
                for item in operations
                if item.get("purpose") == "enroll"
                and item["role"] == "enrollment"
                and item["speaker_id"] in gallery
            ]
            stages.append(
                {
                    "gallery_size_planned": size,
                    "gallery_size_enrolled": sum(
                        item.get("status") == "succeeded" for item in enrollment
                    ),
                    "enrollment_failed": sum(item.get("status") == "failed" for item in enrollment),
                    **summarize_probes(
                        probes, known_planned=known_count, unknown_planned=unknown_count
                    ),
                }
            )
        return {
            "schema_version": 1,
            "run_id": self.state["run_id"],
            "binding": self.state["binding"],
            "dataset_id": self.manifest["dataset_id"],
            "split": self.manifest["split"],
            "status": self.state.get("status", "incomplete"),
            "error_code": self.state.get("error_code"),
            "started_at": self.state["started_at"],
            "updated_at": now(),
            "frozen_policy": self.policy,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "stages": stages,
            "operations": operations,
            "return_phase": [item for item in operations if item.get("stage") == "return"],
            "return_phase_planned": {
                "enrollments": sum(row["role"] == "new_enrollment" for row in self.rows.values()),
                "queries": sum(row["role"] == "return_query" for row in self.rows.values()),
            },
            "accuracy_scope": "Public English read-speech baseline; no Turkish, meeting, diarization, or production guarantee.",
        }

    def save(self) -> None:
        atomic_json(self.state_path, self.state)
        atomic_json(self.output, self.report())

    def upload(self, row: dict) -> str:
        existing = self.state["uploads"].get(row["id"])
        if existing is not None:
            return existing["recording_public_id"]
        path = audio_path(self.audio_root, row["path"])
        with path.open("rb") as source:
            audio = source.read(MAX_AUDIO_BYTES + 1)
        if len(audio) > MAX_AUDIO_BYTES or hashlib.sha256(audio).hexdigest() != row["sha256"]:
            raise EvaluationError("audio_changed_since_preflight")
        boundary = "voiceupeval" + uuid4().hex
        payload = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="probe.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
            + audio
            + f"\r\n--{boundary}--\r\n".encode()
        )
        response = self.request(
            "POST",
            "/recordings",
            payload=payload,
            headers={
                "Content-Type": "multipart/form-data; boundary=" + boundary,
                "Idempotency-Key": operation_key(self.state["run_id"], "upload:" + row["id"]),
            },
        )
        if response.get("sha256") != row["sha256"] or not _text(response.get("public_id")):
            raise EvaluationError("invalid_upload_response")
        self.state["uploads"][row["id"]] = {
            "recording_public_id": response["public_id"],
            "sha256": row["sha256"],
        }
        self.save()
        return response["public_id"]

    def prepare(self, row: dict, purpose: str, stage: int | str) -> tuple[str, dict]:
        identifier = f"{stage}:{purpose}:{row['id']}"
        operation = self.state["operations"].get(identifier)
        if operation is not None and operation.get("status") in TERMINAL:
            return identifier, operation
        if operation is None:
            self.assert_gallery()
            operation = {
                "operation_id": identifier,
                "recording_id": row["id"],
                "speaker_id": row["speaker_id"],
                "role": row["role"],
                "source_split": row["source_split"],
                "chapter_id": row["chapter_id"],
                "source_utterance_ids": row["source_utterance_ids"],
                "source_sha256": row["sha256"],
                "duration_seconds": row["duration_seconds"],
                "purpose": purpose,
                "stage": stage,
                "kind": "unknown" if row["role"] == "unknown_query" else "known",
                "status": "pending",
                "submitted_at": now(),
            }
            self.state["operations"][identifier] = operation
            self.save()
        recording_id = self.upload(row)
        body = {"recording_public_id": recording_id, "purpose": purpose}
        if purpose == "enroll":
            body["name"] = "eval-" + self.state["run_id"][:8] + "-" + row["speaker_id"]
        if operation.get("job_public_id"):
            response = self.request("GET", "/speaker-jobs/" + operation["job_public_id"])
        else:
            try:
                response = self.post(
                    "/speaker-jobs", body, operation_key(self.state["run_id"], identifier)
                )
            except ProfileLimitRejected:
                if purpose != "enroll":
                    raise EvaluationError("http_409") from None
                self.assert_gallery()
                operation.update(
                    status="failed",
                    error_code="profile_limit",
                    result=None,
                    attempt_count=0,
                    finished_at=now(),
                    timing=None,
                    profiles_unchanged=True,
                )
                self.save()
                return identifier, operation
        if not _text(response.get("public_id")):
            raise EvaluationError("invalid_job_response")
        if operation.get("job_public_id", response["public_id"]) != response["public_id"]:
            raise EvaluationError("job_identity_changed")
        operation["job_public_id"] = response["public_id"]
        self.save()
        return identifier, response

    def finish(self, identifier: str, response: dict) -> dict:
        operation = dict(self.state["operations"][identifier])
        next_profiles = self.state["expected_profiles"]
        if operation.get("status") in TERMINAL:
            return operation
        deadline = time.monotonic() + self.job_timeout
        while response.get("status") in {"queued", "running"}:
            if time.monotonic() >= deadline:
                raise EvaluationError("job_poll_deadline_exceeded")
            time.sleep(self.poll_seconds)
            response = self.request("GET", "/speaker-jobs/" + operation["job_public_id"])
        if (
            response.get("public_id") != operation["job_public_id"]
            or response.get("purpose") != operation["purpose"]
            or response.get("status") not in TERMINAL
        ):
            raise EvaluationError("invalid_terminal_job_response")
        operation["status"] = response["status"]
        operation["attempt_count"] = response.get("attempt_count")
        operation["result"] = response.get("result")
        operation["finished_at"] = response.get("finished_at")
        operation["error_code"] = (response.get("error") or {}).get("code")
        if operation["error_code"] is not None and (
            not isinstance(operation["error_code"], str)
            or re.fullmatch(r"[a-z0-9_]{1,80}", operation["error_code"]) is None
        ):
            raise EvaluationError("invalid_job_error_code")
        if operation["status"] == "succeeded":
            result = operation["result"]
            if (
                not isinstance(result, dict)
                or result.get("policy") != self.policy
                or result.get("model_id") != MODEL_ID
                or result.get("model_revision") != MODEL_REVISION
                or not str(result.get("device", "")).startswith("cuda")
            ):
                raise EvaluationError("frozen_inference_contract_changed")
            if "required_preprocessing_versions" in self.state["binding"]:
                validate_preprocessing_result(
                    result, self.state["binding"]["required_preprocessing_versions"]
                )
            if operation["purpose"] == "enroll":
                if result.get("decision") != "enrolled" or not _text(
                    result.get("profile_public_id")
                ):
                    raise EvaluationError("invalid_enrollment_result")
                expected = self.state["expected_profiles"]
                current = self.profiles()
                additions = [
                    item for item in current if item["public_id"] == result["profile_public_id"]
                ]
                remaining = [
                    item for item in current if item["public_id"] != result["profile_public_id"]
                ]
                if (
                    remaining != expected
                    or len(additions) != 1
                    or additions[0].get("sample_count") != 1
                ):
                    raise EvaluationError("evaluation_gallery_changed")
                next_profiles = current
            else:
                decision = result.get("decision")
                profile_id = result.get("profile_public_id")
                if decision not in {"recognized", "unknown", "ambiguous"} or (
                    decision == "recognized"
                ) != bool(profile_id):
                    raise EvaluationError("invalid_identification_result")
                if profile_id is not None and profile_id not in self.profile_map():
                    raise EvaluationError("unowned_profile_in_result")
                operation.update(
                    decision=decision, predicted_speaker_id=self.profile_map().get(profile_id)
                )
                self.assert_gallery()
                operation["profiles_unchanged"] = True
        else:
            self.assert_gallery()
        try:
            created, started, finished = [
                benchmark.parse_timestamp(response.get(key))
                for key in ("created_at", "started_at", "finished_at")
            ]
            if not created <= started <= finished:
                raise EvaluationError("invalid_server_timestamps")
            operation["timing"] = {
                "queue_seconds": (started - created).total_seconds(),
                "execution_seconds": (finished - started).total_seconds(),
                "server_total_seconds": (finished - created).total_seconds(),
            }
        except benchmark.BenchmarkFailure:
            operation["timing"] = None
        self.state["expected_profiles"] = next_profiles
        self.state["operations"][identifier] = operation
        self.save()
        print(
            f"Completed {len([item for item in self.state['operations'].values() if item.get('status') in TERMINAL])} operations; gallery stage {operation['stage']}.",
            flush=True,
        )
        return operation

    def execute(self, *, batch_size: int = 4) -> None:
        self.login()
        # Resolve jobs already accepted before a stopped process before comparing its gallery.
        for identifier, operation in list(self.state["operations"].items()):
            if operation.get("status") not in TERMINAL:
                key, response = self.prepare(
                    self.rows[operation["recording_id"]], operation["purpose"], operation["stage"]
                )
                self.finish(key, response)
        self.assert_gallery()
        for size in self.state["binding"]["gallery_sizes"]:
            gallery = self.manifest["gallery_order"][:size]
            for speaker in gallery:
                row = next(
                    item
                    for item in self.rows.values()
                    if item["role"] == "enrollment" and item["speaker_id"] == speaker
                )
                identifier, response = self.prepare(row, "enroll", "enrollment")
                self.finish(identifier, response)
            rows = [
                row
                for row in self.rows.values()
                if (row["role"] == "known_query" and row["speaker_id"] in gallery)
                or row["role"] == "unknown_query"
            ]
            for offset in range(0, len(rows), batch_size):
                pending = [
                    self.prepare(row, "identify", size)
                    for row in rows[offset : offset + batch_size]
                ]
                for identifier, response in pending:
                    self.finish(identifier, response)
            self.assert_gallery()
        for row in self.rows.values():
            if row["role"] == "new_enrollment":
                self.finish(*self.prepare(row, "enroll", "return"))
        for row in self.rows.values():
            if row["role"] == "return_query":
                self.finish(*self.prepare(row, "identify", "return"))
        self.assert_gallery()
        self.state["status"] = "complete"
        self.state.pop("error_code", None)
        self.save()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "audio-root", "credentials", "output", "state"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--gallery-sizes", default="5,10,20,50")
    parser.add_argument(
        "--policy", type=Path, help="Reviewed frozen policy JSON; omitted uses historical defaults"
    )
    parser.add_argument(
        "--require-preprocessing-provenance",
        action="store_true",
        help="Freeze supported preprocessing versions and require one on every successful job",
    )
    parser.add_argument("--job-timeout", type=float, default=660)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Bounded queued identify jobs; inference remains serialized",
    )
    args = parser.parse_args(argv)
    runner = None
    try:
        sizes = [int(value) for value in args.gallery_sizes.split(",")]
        if (
            not 0 < args.job_timeout <= 900
            or not 0.1 <= args.poll_seconds <= 10
            or not 1 <= args.batch_size <= 4
        ):
            raise EvaluationError("invalid_runtime_bounds")
        policy = validate_policy(read_json(args.policy, 4096) if args.policy else POLICY)
        manifest = read_json(args.manifest, 4 * 1024 * 1024)
        validate_manifest(manifest, args.audio_root, sizes)
        credentials = read_json(args.credentials, 65536)
        if not isinstance(credentials, dict) or any(
            not isinstance(credentials.get(key), str) or not credentials[key]
            for key in ("url", "username", "password", "tenant_id")
        ):
            raise EvaluationError("invalid_credentials_file")
        UUID(credentials["tenant_id"])
        api = EvaluationApi(credentials["url"], "/api/voiceup/v1")
        binding = {
            "protocol": "public-speaker-api-v1",
            "manifest_sha256": hashlib.sha256(
                json.dumps(
                    manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
            ).hexdigest(),
            "tenant_id": credentials["tenant_id"],
            "origin": api.origin,
            "gallery_sizes": sizes,
            "policy": policy,
            "model_revision": MODEL_REVISION,
        }
        if args.require_preprocessing_provenance:
            binding["required_preprocessing_versions"] = list(PREPROCESSING_VERSIONS)
        protected = {
            args.manifest,
            args.credentials,
            *(audio_path(args.audio_root, row["path"]) for row in manifest["recordings"]),
        }
        if args.policy is not None:
            protected.add(args.policy)
        check_output_paths(args.output, args.state, protected)
        with state_lock(args.state):
            if args.state.exists():
                state = read_json(args.state)
                validate_state(state, binding)
            else:
                if args.output.exists():
                    raise EvaluationError("output_exists_without_resume_state")
                state = {
                    "schema_version": 1,
                    "binding": binding,
                    "run_id": uuid4().hex,
                    "started_at": now(),
                    "status": "incomplete",
                    "operations": {},
                    "uploads": {},
                    "expected_profiles": [],
                }
            runner = Evaluator(
                manifest=manifest,
                audio_root=args.audio_root,
                credentials=credentials,
                state=state,
                state_path=args.state,
                output=args.output,
                job_timeout=args.job_timeout,
                poll_seconds=args.poll_seconds,
                api=api,
            )
            try:
                runner.execute(batch_size=args.batch_size)
            except (
                EvaluationError,
                benchmark.BenchmarkFailure,
                OSError,
                ValueError,
                KeyError,
                TypeError,
            ) as exc:
                code = (
                    str(exc)
                    if isinstance(exc, (EvaluationError, benchmark.BenchmarkFailure))
                    else "invalid_local_input_or_response"
                )
                state["status"], state["error_code"] = "incomplete", code
                runner.save()
                raise EvaluationError(code) from None
    except (
        EvaluationError,
        benchmark.BenchmarkFailure,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        code = (
            str(exc)
            if isinstance(exc, (EvaluationError, benchmark.BenchmarkFailure))
            else "invalid_local_input_or_response"
        )
        print("Evaluation incomplete: " + code, file=sys.stderr)
        return 1
    print(
        "Evaluation complete. Inspect planned denominators, quality errors, and external-data limitations."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
