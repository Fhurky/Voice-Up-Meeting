"""Exercise frozen A/B/D/C meeting fixtures through the real loopback HTTP API."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
import time
import wave
from collections import defaultdict
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


def _existing_runner():
    spec = importlib.util.spec_from_file_location(
        "voiceup_meeting_evaluation_helpers",
        Path(__file__).with_name("evaluate-public-speakers.py"),
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = _existing_runner()
benchmark = helpers.benchmark
PART_BYTES = 4 * 1024 * 1024
CASE_KEYS = ("A", "B", "D", "C")
CASE_FILES = (
    "meeting-a-five.wav",
    "meeting-b-return.wav",
    "meeting-d-short-sixth.wav",
    "meeting-c-sixth-new.wav",
)
MAPPING_POLICY = {
    "minimum_dominant_share": 0.90,
    "split_minimum_seconds": 0.5,
    "split_minimum_share": 0.10,
    "minimum_assigned_seconds": 0.5,
}
REQUIRED_PERMISSIONS = {
    "meeting_analysis:read",
    "meeting_analysis:run",
    "speaker_profiles:read",
    "speaker_profiles:write",
}


class EvaluationError(Exception):
    """Only stable, secret-free error codes leave the runner."""


def identifier(value: Any) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise EvaluationError("invalid_public_identifier") from None


def finite(value: Any) -> float:
    if type(value) not in {int, float} or not math.isfinite(value):
        raise EvaluationError("invalid_finite_number")
    return float(value)


def observed_count(value: Any) -> int | None:
    return value if type(value) is int and 0 <= value <= 1000000 else None


def source_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def operation_key(run_id: str, case: str) -> str:
    return "meeting-eval-" + hashlib.sha256(f"{run_id}:{case}".encode()).hexdigest()


def union_seconds(ranges: list[tuple[float, float]]) -> float:
    merged: list[list[float]] = []
    for start, end in sorted(ranges):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged)


def load_protocol(path: Path) -> dict[str, Any]:
    protocol = helpers.read_json(path, maximum=2 * 1024 * 1024)
    if (
        not isinstance(protocol, dict)
        or protocol.get("schema_version") != 1
        or protocol.get("protocol_id") != "voiceup-meeting-first-six-v1"
    ):
        raise EvaluationError("unsupported_protocol")
    identities = protocol.get("identities")
    if (
        not isinstance(identities, list)
        or len(identities) != 6
        or len(set(identities)) != 6
        or any(not isinstance(i, str) or not re.fullmatch(r"ls-[0-9]+", i) for i in identities)
    ):
        raise EvaluationError("invalid_protocol_identities")
    cases = protocol.get("cases")
    if not isinstance(cases, list) or len(cases) != 4:
        raise EvaluationError("invalid_protocol_cases")
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or case.get("path") != CASE_FILES[index]:
            raise EvaluationError("invalid_fixture_path")
        audio = path.parent / case["path"]
        if (
            audio.is_symlink()
            or audio.is_junction()
            or audio.resolve().parent != path.parent.resolve()
        ):
            raise EvaluationError("invalid_fixture_path")
        if not audio.is_file() or not 0 < audio.stat().st_size <= 2 * 1024**3:
            raise EvaluationError("invalid_fixture_size")
        if source_hash(audio) != case.get("sha256"):
            raise EvaluationError("source_hash_mismatch")
        with wave.open(str(audio), "rb") as reader:
            rate = reader.getframerate()
            duration = reader.getnframes() / rate
            if (reader.getnchannels(), reader.getsampwidth(), rate, reader.getcomptype()) != (
                1,
                2,
                16000,
                "NONE",
            ):
                raise EvaluationError("invalid_fixture_format")
        expected = 5 if index < 2 else 6
        if (
            case.get("sample_rate") != rate
            or abs(finite(case.get("duration_seconds")) - duration) > 1 / rate
            or not 0 < duration <= 14400
            or case.get("expected_speakers") != expected
            or case.get("expected_gallery_total") != (6 if index == 3 else 5)
        ):
            raise EvaluationError("invalid_fixture_metadata")
        intervals = case.get("intervals")
        if not isinstance(intervals, list) or not 1 <= len(intervals) <= 10000:
            raise EvaluationError("invalid_reference_intervals")
        prior_end = 0.0
        sources: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for row in intervals:
            identity = row.get("speaker_id")
            start, end = finite(row.get("start_seconds")), finite(row.get("end_seconds"))
            left, right = row.get("source_start_frame"), row.get("source_end_frame")
            if (
                identity not in identities[:expected]
                or not 0 <= prior_end <= start < end <= duration + 1 / rate
                or type(left) is not int
                or type(right) is not int
                or not 0 <= left < right
                or abs((right - left) / rate - (end - start)) > 1 / rate
            ):
                raise EvaluationError("invalid_reference_intervals")
            if any(
                max(left, old_left) < min(right, old_right)
                for old_left, old_right in sources[identity]
            ):
                raise EvaluationError("repeated_source_evidence")
            sources[identity].append((left, right))
            prior_end = end
        if set(sources) != set(identities[:expected]):
            raise EvaluationError("missing_reference_identity")
    return protocol


def map_identities(
    intervals: list[dict], rows: list[dict], track_ids: set[str], *, duration_seconds: float = 14400
) -> dict[str, Any]:
    """Source-interval temporal voting, not DER, WER or biometric identity F1."""
    track_ids = {identifier(value) for value in track_ids}
    votes: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    references: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in intervals:
        start, end = finite(row["start_seconds"]), finite(row["end_seconds"])
        if start < 0 or end <= start:
            raise EvaluationError("invalid_reference_intervals")
        references[row["speaker_id"]].append((start, end))
    ordinals, seen_ids = set(), set()
    text_hash = hashlib.sha256()
    characters, unassigned = 0, []
    for row in rows:
        public_id = identifier(row.get("public_id"))
        ordinal = row.get("ordinal")
        start, end = finite(row.get("start_seconds")), finite(row.get("end_seconds"))
        if (
            type(ordinal) is not int
            or ordinal < 0
            or ordinal in ordinals
            or public_id in seen_ids
            or start < 0
            or end <= start
            or end > finite(duration_seconds) + 1 / 16000
            or not isinstance(row.get("text"), str)
            or not row["text"].strip()
        ):
            raise EvaluationError("invalid_transcript_contract")
        ordinals.add(ordinal)
        seen_ids.add(public_id)
        characters += len(row["text"])
        text_hash.update(json.dumps([ordinal, row["text"]], ensure_ascii=False).encode())
        raw_track = row.get("speaker_public_id")
        if raw_track is None:
            unassigned.append((start, end))
            continue
        track = identifier(raw_track)
        if track not in track_ids:
            raise EvaluationError("unknown_transcript_track")
        for identity, source_ranges in references.items():
            for left, right in source_ranges:
                if max(start, left) < min(end, right):
                    votes[identity][track].append((max(start, left), min(end, right)))
    mapping, amounts, shares = {}, {}, {}
    missing, split, weak = [], [], []
    for identity in references:
        amounts[identity] = {
            track: union_seconds(ranges) for track, ranges in votes[identity].items()
        }
        ranked = sorted(amounts[identity].items(), key=lambda item: (-item[1], item[0]))
        total = sum(value for _, value in ranked)
        if total < MAPPING_POLICY["minimum_assigned_seconds"]:
            missing.append(identity)
            continue
        mapping[identity] = ranked[0][0]
        shares[identity] = ranked[0][1] / total
        if shares[identity] < MAPPING_POLICY["minimum_dominant_share"]:
            weak.append(identity)
        if any(
            value >= MAPPING_POLICY["split_minimum_seconds"]
            and value / total >= MAPPING_POLICY["split_minimum_share"]
            for _, value in ranked[1:]
        ):
            split.append(identity)
    merged = sorted(
        {track for track in mapping.values() if list(mapping.values()).count(track) > 1}
    )
    return {
        "passed": not (missing or split or merged or weak),
        "mapping": mapping,
        "votes_seconds": amounts,
        "dominant_share": shares,
        "split_identities": split,
        "merged_tracks": merged,
        "missing_identities": missing,
        "weak_majority_identities": weak,
        "unassigned_transcript_seconds": union_seconds(unassigned),
        "transcript_segments": len(rows),
        "transcript_characters": characters,
        "transcript_sha256": text_hash.hexdigest(),
        "policy": MAPPING_POLICY,
        "measurement": "Reference source-interval agreement; not manual DER, WER or identity F1",
    }


class MeetingEvaluation:
    def __init__(
        self,
        args: argparse.Namespace,
        protocol: dict[str, Any],
        credentials: dict[str, str],
        state: dict[str, Any],
    ) -> None:
        self.args, self.protocol, self.credentials, self.state = args, protocol, credentials, state
        self.api = benchmark.Api(args.base_url or credentials["url"], args.api_prefix)

    def save(self) -> None:
        helpers.atomic_json(self.args.state, self.state)

    def login(self) -> None:
        result = self.api.json(
            "/auth/login",
            {"username": self.credentials["username"], "password": self.credentials["password"]},
        )
        user = result.get("user", {})
        if user.get("is_super_admin") is not False or "super_admin" in user.get("roles", []):
            raise EvaluationError("ordinary_role_required")
        if not REQUIRED_PERMISSIONS <= set(user.get("permissions", [])):
            raise EvaluationError("evaluation_permissions_missing")
        identity = {
            "user_public_id": identifier(user.get("public_id")),
            "tenant_public_id": identifier(user.get("tenant_id")),
            "origin": self.api.origin,
            "api_prefix": self.api.prefix,
        }
        if self.state.get("binding") not in (None, identity):
            raise EvaluationError("resume_binding_mismatch")
        token = result.get("access_token")
        if (
            not isinstance(token, str)
            or not token
            or len(token) > 16384
            or "\r" in token
            or "\n" in token
        ):
            raise EvaluationError("invalid_authentication_response")
        self.state["binding"] = identity
        self.api.headers = {
            "Authorization": "Bearer " + token,
            "x-tenant-id": identity["tenant_public_id"],
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        payload: bytes | None = None,
        headers: dict | None = None,
    ) -> dict:
        if body is not None:
            payload = json.dumps(body).encode()
            headers = {**(headers or {}), "Content-Type": "application/json"}
        try:
            return self.api.request(method, path, payload=payload, headers=headers)
        except benchmark.BenchmarkFailure as exc:
            if str(exc) != "http_401":
                raise
            self.login()
            return self.api.request(method, path, payload=payload, headers=headers)

    def page(self, path: str) -> list[dict]:
        items, total = [], None
        for offset in range(0, 1000001, 100):
            result = self.request("GET", f"{path}?offset={offset}&limit=100")
            rows, observed = result.get("items"), result.get("total")
            if (
                not isinstance(rows, list)
                or type(observed) is not int
                or not 0 <= observed <= 1000000
                or len(rows) > 100
            ):
                raise EvaluationError("invalid_page_contract")
            if total is not None and observed != total:
                raise EvaluationError("page_changed_during_evaluation")
            total = observed
            items.extend(rows)
            if len(items) == total:
                return items
            if not rows or len(items) > total:
                raise EvaluationError("incomplete_page_contract")
        raise EvaluationError("page_limit")

    def gallery(self, expected: int | None = None) -> list[dict]:
        profiles = self.page("/speaker-profiles")
        if expected is not None and len(profiles) != expected:
            raise EvaluationError("unexpected_gallery_total")
        identifiers = [identifier(row.get("public_id")) for row in profiles]
        if len(set(identifiers)) != len(profiles):
            raise EvaluationError("duplicate_gallery_identity")
        return profiles

    def verify_recorded_memory(self, profiles: list[dict]) -> None:
        current = {identifier(row["public_id"]): row for row in profiles}
        for identity, public_id in self.state["identity_profiles"].items():
            profile = current.get(identifier(public_id))
            expected_name = self.state["identity_names"].get(identity)
            if profile is None or (
                expected_name is not None and profile.get("name") != expected_name
            ):
                raise EvaluationError("resume_gallery_identity_or_name_changed")

    def upload(self, key: str, case: dict[str, Any]) -> tuple[str, dict]:
        path = self.args.protocol.parent / case["path"]
        size = path.stat().st_size
        checkpoint = self.state["cases"].setdefault(key, {})
        body = {
            "title": f"Evaluation {key}",
            "format": "WAV",
            "size_bytes": size,
            "language": "en",
            "auto_enroll": True,
        }
        if "meeting_public_id" not in checkpoint:
            meeting = self.request(
                "POST",
                "/meetings",
                body=body,
                headers={"Idempotency-Key": operation_key(self.state["run_id"], key)},
            )
            checkpoint["meeting_public_id"] = identifier(meeting.get("public_id"))
            self.save()
        meeting_id = identifier(checkpoint["meeting_public_id"])
        route = "/meetings/" + meeting_id
        meeting = self.request("GET", route)
        if meeting.get("public_id") != meeting_id:
            raise EvaluationError("meeting_identity_mismatch")
        if meeting.get("status") != "uploading":
            if meeting.get("sha256") != case["sha256"]:
                raise EvaluationError("server_source_hash_mismatch")
            return route, meeting
        manifest = self.request("GET", route + "/upload-parts")
        parts = manifest.get("parts")
        if (
            not isinstance(parts, list)
            or len(parts) > 512
            or manifest.get("meeting_public_id") != meeting_id
        ):
            raise EvaluationError("invalid_upload_manifest")
        accepted = 0
        with path.open("rb") as stream:
            for index, part in enumerate(parts):
                data = stream.read(PART_BYTES)
                if (
                    not data
                    or type(part.get("index")) is not int
                    or part.get("index") != index
                    or part.get("size_bytes") != len(data)
                    or part.get("sha256") != hashlib.sha256(data).hexdigest()
                ):
                    raise EvaluationError("resume_upload_hash_mismatch")
                accepted += len(data)
            if manifest.get("uploaded_bytes") != accepted or manifest.get("next_index") != len(
                parts
            ):
                raise EvaluationError("invalid_upload_manifest")
            index = len(parts)
            while data := stream.read(PART_BYTES):
                ack = self.request(
                    "PUT",
                    route + f"/upload-parts/{index}",
                    payload=data,
                    headers={
                        "Content-Type": "application/octet-stream",
                        "X-Chunk-SHA256": hashlib.sha256(data).hexdigest(),
                    },
                )
                accepted += len(data)
                index += 1
                if ack.get("uploaded_bytes") != accepted or ack.get("next_index") != index:
                    raise EvaluationError("invalid_upload_acknowledgement")
                checkpoint["acknowledged_bytes"] = accepted
                self.save()
        if accepted != size:
            raise EvaluationError("incomplete_local_upload")
        checkpoint["upload_verified"] = True
        self.save()
        return route, meeting

    def analyze(self, route: str, key: str, case: dict) -> dict:
        meeting = self.request("POST", route + "/complete")
        if meeting.get("public_id") != route.rsplit("/", 1)[1]:
            raise EvaluationError("meeting_identity_mismatch")
        if self.args.repeat_complete:
            repeated = self.request("POST", route + "/complete")
            if repeated.get("public_id") != meeting.get("public_id"):
                raise EvaluationError("complete_not_idempotent")
            self.state["cases"][key]["repeat_complete_verified"] = True
            self.save()
        started = time.monotonic()
        while meeting.get("status") in {"queued", "running", "finalizing"}:
            if time.monotonic() - started >= self.args.timeout:
                raise EvaluationError("meeting_poll_timeout")
            self.state["cases"][key]["last_observed_status"] = meeting["status"]
            self.state["cases"][key]["completed_chunks"] = observed_count(
                meeting.get("completed_chunks")
            )
            self.save()
            time.sleep(self.args.poll_seconds)
            meeting = self.request("GET", route)
            if meeting.get("public_id") != route.rsplit("/", 1)[1]:
                raise EvaluationError("meeting_identity_mismatch")
        self.record_terminal_observation(meeting, key, case)
        if meeting.get("status") != "succeeded":
            raise EvaluationError("meeting_not_succeeded")
        if (
            meeting.get("sha256") != case["sha256"]
            or meeting.get("observed_speakers") != case["expected_speakers"]
        ):
            raise EvaluationError("source_or_speaker_count_mismatch")
        return meeting

    def record_terminal_observation(self, meeting: dict, key: str, case: dict) -> None:
        # Persist a strict numeric/enum projection before any acceptance check.
        # Never copy arbitrary server fields, transcript, names, tokens or vectors.
        status = meeting.get("status")
        if not isinstance(status, str) or status not in {
            "uploading",
            "queued",
            "running",
            "finalizing",
            "succeeded",
            "failed",
            "cancelled",
        }:
            status = "invalid_status"
        duration = meeting.get("duration_seconds")
        duration = (
            float(duration)
            if type(duration) in {int, float}
            and 0 <= duration <= 1000000
            and math.isfinite(duration)
            else None
        )
        observed = {
            "status": status,
            "duration_seconds": duration,
            "observed_speakers": observed_count(meeting.get("observed_speakers")),
            "completed_chunks": observed_count(meeting.get("completed_chunks")),
            "expected_speakers": case["expected_speakers"],
            "expected_gallery_total": case["expected_gallery_total"],
            "source_hash_matches": meeting.get("sha256") == case["sha256"],
            "gallery_total": None,
        }
        checkpoint = self.state["cases"][key]
        checkpoint.update(
            {
                "last_observed_status": status,
                "completed_chunks": observed["completed_chunks"],
                "observed": observed,
            }
        )
        self.save()
        try:
            observed["gallery_total"] = len(self.gallery())
        except (
            EvaluationError,
            benchmark.BenchmarkFailure,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ):
            # A diagnostic read must not replace the primary acceptance failure.
            observed["gallery_observation_error"] = "unavailable"
        self.save()

    def case_result(self, route: str, key: str, case: dict) -> dict:
        speakers = self.page(route + "/speakers")
        tracks = {identifier(row.get("public_id")): row for row in speakers}
        if len(tracks) != len(speakers):
            raise EvaluationError("duplicate_meeting_track")
        rows = self.page(route + "/transcript")
        result = map_identities(
            case["intervals"], rows, set(tracks), duration_seconds=case["duration_seconds"]
        )
        result["mapping_passed"], result["passed"] = result["passed"], False
        result.update({"source_sha256": case["sha256"], "observed_tracks": len(tracks)})
        self.state["cases"][key]["result"] = result
        self.save()
        if not result["mapping_passed"] or len(tracks) != case["expected_speakers"]:
            raise EvaluationError("reference_mapping_failed")
        profiles = self.gallery(case["expected_gallery_total"])
        gallery_ids = {identifier(row["public_id"]) for row in profiles}
        memory = self.state["identity_profiles"]
        names = self.state["identity_names"]
        for identity, track_id in result["mapping"].items():
            row = tracks[track_id]
            raw_profile = row.get("profile_public_id")
            profile_id = identifier(raw_profile) if raw_profile is not None else None
            sixth = identity == self.protocol["identities"][5]
            if key == "D" and sixth:
                if profile_id is not None or row.get("decision") != "profile_pending":
                    raise EvaluationError("short_new_person_not_pending")
                continue
            if (
                profile_id is None
                or profile_id not in gallery_ids
                or row.get("profile_deleted") is not False
            ):
                raise EvaluationError("missing_persistent_identity")
            if key == "A" or (key == "C" and sixth):
                if row.get("decision") != "enrolled" or profile_id in {
                    value for other, value in memory.items() if other != identity
                }:
                    raise EvaluationError("new_person_identity_collision")
                if identity in memory and memory[identity] != profile_id:
                    raise EvaluationError("profile_changed_during_resume")
                memory[identity] = profile_id
                if key == "A":
                    target = "Evaluation person " + str(
                        self.protocol["identities"].index(identity) + 1
                    )
                    if row.get("profile_name") != target or row.get("display_name") != target:
                        if identity in names:
                            raise EvaluationError("manual_name_changed_after_checkpoint")
                        renamed = self.request(
                            "PATCH",
                            route + "/speakers/" + track_id,
                            body={
                                "name": target,
                                "version": row["version"],
                                "profile_updated_at": row.get("profile_updated_at"),
                            },
                        )
                        if (
                            renamed.get("profile_public_id") != profile_id
                            or renamed.get("profile_name") != target
                            or renamed.get("display_name") != target
                        ):
                            raise EvaluationError("manual_name_not_persistent")
                    names[identity] = target
                    self.save()
            elif (
                row.get("decision") != "recognized"
                or memory.get(identity) != profile_id
                or names.get(identity) != row.get("profile_name")
            ):
                raise EvaluationError("returning_identity_or_name_mismatch")
        if len(set(memory.values())) != len(memory):
            raise EvaluationError("persistent_identity_merge")
        result["gallery_total"] = len(profiles)
        result["profile_ids"] = {identity: memory.get(identity) for identity in result["mapping"]}
        result["passed"] = True
        return result

    def execute(self) -> None:
        self.login()
        if self.state["identity_profiles"]:
            self.verify_recorded_memory(self.gallery())
        if not self.state.get("initial_gallery_verified"):
            self.gallery(0)
            self.state["initial_gallery_verified"] = True
            self.save()
        for key, case in zip(CASE_KEYS, self.protocol["cases"], strict=True):
            checkpoint = self.state["cases"].get(key, {})
            if checkpoint.get("passed"):
                continue
            route, meeting = self.upload(key, case)
            if (
                key == "B"
                and self.args.stop_after_upload_b
                and meeting.get("status") == "uploading"
            ):
                self.state["status"] = "paused_after_b_upload"
                self.save()
                return
            self.analyze(route, key, case)
            result = self.case_result(route, key, case)
            self.state["cases"][key].update({"result": result, "passed": True})
            self.save()
            print(f"Meeting {key}: accepted.", flush=True)
        self.verify_recorded_memory(self.gallery(6))
        self.state["status"] = "passed"
        self.save()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--base-url")
    parser.add_argument("--api-prefix", default="/api/voiceup/v1")
    parser.add_argument("--repeat-complete", action="store_true")
    parser.add_argument(
        "--stop-after-upload-b",
        action="store_true",
        help="Pause before B completion; restart the application externally, then resume without this option",
    )
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--poll-seconds", type=float, default=1)
    args = parser.parse_args()
    args.state = args.state or args.output.with_suffix(".state.json")
    report: dict[str, Any] = {
        "status": "incomplete",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "mapping_policy": MAPPING_POLICY,
        "model_hints_used": False,
        "limitations": [
            "Constructed English source intervals, not representative Turkish meetings.",
            "Temporal mapping is not manual DER, WER or identity F1.",
            "CLI resume alone does not prove a device or worker restart.",
        ],
    }
    can_write, state = False, None
    locks = ExitStack()
    code = 0
    try:
        if (
            not math.isfinite(args.timeout)
            or args.timeout <= 0
            or not math.isfinite(args.poll_seconds)
            or not 0.1 <= args.poll_seconds <= 10
        ):
            raise EvaluationError("invalid_poll_settings")
        protocol = load_protocol(args.protocol)
        protected = {
            args.protocol,
            args.credentials,
            *(args.protocol.parent / case["path"] for case in protocol["cases"]),
        }
        helpers.check_output_paths(args.output, args.state, protected)
        credentials = helpers.read_json(args.credentials, maximum=65536)
        if not isinstance(credentials, dict) or any(
            not isinstance(credentials.get(k), str) or not credentials[k]
            for k in ("url", "username", "password")
        ):
            raise EvaluationError("invalid_credentials_file")
        protocol_hash = source_hash(args.protocol)
        report.update(
            {
                "protocol_sha256": protocol_hash,
                "protocol_id": protocol["protocol_id"],
                "runner_sha256": source_hash(Path(__file__)),
                "source_manifest_sha256": protocol.get("source_manifest_sha256"),
                "frozen_sources": [
                    {
                        name: case[name]
                        for name in (
                            "sha256",
                            "duration_seconds",
                            "expected_speakers",
                            "expected_gallery_total",
                        )
                    }
                    for case in protocol["cases"]
                ],
            }
        )
        locks.enter_context(helpers.state_lock(args.state))
        if not args.resume and (args.output.exists() or args.state.exists()):
            raise EvaluationError("output_exists_use_resume")
        can_write = True
        if args.resume:
            state = helpers.read_json(args.state)
            if (
                not isinstance(state, dict)
                or state.get("schema_version") != 1
                or state.get("protocol_sha256") != protocol_hash
                or state.get("mapping_policy") != MAPPING_POLICY
                or state.get("repeat_complete") != args.repeat_complete
            ):
                raise EvaluationError("resume_protocol_mismatch")
            identifier(state.get("run_id"))
        else:
            state = {
                "schema_version": 1,
                "run_id": str(uuid4()),
                "status": "incomplete",
                "protocol_sha256": protocol_hash,
                "mapping_policy": MAPPING_POLICY,
                "repeat_complete": args.repeat_complete,
                "cases": {},
                "identity_profiles": {},
                "identity_names": {},
            }
        runner = MeetingEvaluation(args, protocol, credentials, state)
        runner.execute()
        report.update(
            {
                "status": state["status"],
                "run_id": state["run_id"],
                "protocol_sha256": protocol_hash,
                "cases": state["cases"],
                "resumed": args.resume,
                "ordinary_role": True,
            }
        )
    except (EvaluationError, helpers.EvaluationError, benchmark.BenchmarkFailure) as exc:
        error = str(exc)
        report["error_code"] = (
            error if re.fullmatch(r"[a-z0-9_]{1,96}", error) else "evaluation_failed"
        )
        print("Meeting evaluation incomplete: " + report["error_code"], file=sys.stderr)
        code = 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, wave.Error):
        report["error_code"] = "invalid_local_input_or_response"
        print("Meeting evaluation incomplete: invalid local input or response.", file=sys.stderr)
        code = 1
    finally:
        if can_write:
            if state is not None:
                report["cases"] = state.get("cases", {})
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            try:
                helpers.atomic_json(args.output, report)
            except OSError:
                print("Meeting evaluation incomplete: result_write_failed.", file=sys.stderr)
                code = 1
        locks.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
