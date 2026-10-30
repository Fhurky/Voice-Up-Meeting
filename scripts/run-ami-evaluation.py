#!/usr/bin/env python3
"""Run the AMI public benchmark through the real loopback HTTP API (PRD 015).

Diarization is scored as DER against human RTTM references. Cross-meeting identity
uses person-disjoint speaker components: gallery components enroll through the
product's automatic memory and must be recognized later; non-gallery components run
without automatic memory, and any recognition there is a false accept.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import uuid4

PROTOCOL = "voiceup-ami-public-benchmark-v1"
PART_BYTES = 4 * 1024 * 1024
MIN_PROBE_SECONDS = 3.0
MIN_DOMINANT_SHARE = 0.5
BOOTSTRAP_ROUNDS = 2000
BOOTSTRAP_SEED = 20261029
REQUIRED_PERMISSIONS = {
    "meeting_analysis:read",
    "meeting_analysis:run",
    "speaker_profiles:read",
    "speaker_profiles:write",
}


class EvaluationError(Exception):
    """Only stable, secret-free error codes leave the runner."""


def _helpers():
    spec = importlib.util.spec_from_file_location(
        "voiceup_ami_helpers", Path(__file__).with_name("evaluate-public-speakers.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- protocol and plan


def read_rttm(path: Path, meeting: str) -> list[tuple[float, float, str]]:
    segments = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 8 or fields[0] != "SPEAKER" or fields[1] != meeting:
            raise EvaluationError("invalid_rttm")
        start, duration = float(fields[3]), float(fields[4])
        segments.append((start, start + duration, fields[7]))
    return segments


def components(meetings: list[dict]) -> list[list[dict]]:
    """Group meetings that share any person; groups are person-disjoint by construction."""
    parent = {row["meeting"]: row["meeting"] for row in meetings}

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    owner: dict[str, str] = {}
    for row in meetings:
        for person in row["speakers"]:
            if person in owner:
                parent[find(row["meeting"])] = find(owner[person])
            else:
                owner[person] = row["meeting"]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in meetings:
        grouped[find(row["meeting"])].append(row)
    return sorted(
        (sorted(rows, key=lambda row: row["meeting"]) for rows in grouped.values()),
        key=lambda rows: rows[0]["meeting"],
    )


def plan(meetings: list[dict], rotation: int) -> list[dict]:
    """Gallery components first (automatic memory on), then non-gallery (memory off)."""
    groups = components(meetings)
    gallery = [group for index, group in enumerate(groups) if index % 2 == rotation - 1]
    others = [group for index, group in enumerate(groups) if index % 2 != rotation - 1]
    steps = [{**row, "role": "gallery"} for group in gallery for row in group]
    steps += [{**row, "role": "non_gallery"} for group in others for row in group]
    return steps


# ---------------------------------------------------------------- scoring


def overlap(first: tuple[float, float], second: tuple[float, float]) -> float:
    return max(0.0, min(first[1], second[1]) - max(first[0], second[0]))


def dominant_people(
    turns: list[dict], reference: list[tuple[float, float, str]], uem: tuple[float, float]
) -> dict[str, tuple[str | None, float]]:
    """Map each hypothesis speaker to (reference person, share) when one person dominates."""
    totals: dict[str, float] = defaultdict(float)
    shared: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for turn in turns:
        speaker = turn["speaker_public_id"]
        if speaker is None:
            continue
        span = (max(turn["start_seconds"], uem[0]), min(turn["end_seconds"], uem[1]))
        if span[1] <= span[0]:
            continue
        totals[speaker] += span[1] - span[0]
        for start, end, person in reference:
            shared[speaker][person] += overlap(span, (start, end))
    result = {}
    for speaker, total in totals.items():
        person, seconds = max(shared[speaker].items(), key=lambda item: item[1], default=(None, 0))
        share = seconds / total if total else 0.0
        result[speaker] = (person if share >= MIN_DOMINANT_SHARE else None, share)
    return result


def reference_seconds(reference: list[tuple[float, float, str]]) -> dict[str, float]:
    seconds: dict[str, float] = defaultdict(float)
    for start, end, person in reference:
        seconds[person] += end - start
    return seconds


def score_meeting(
    role: str,
    speakers: list[dict],
    dominance: dict[str, tuple[str | None, float]],
    reference: list[tuple[float, float, str]],
    owners: dict[str, str | None],
) -> list[dict]:
    """Return one outcome per person with enough reference speech; update profile owners.

    A profile's owner is the person dominating the cluster that enrolled it (None when no
    person dominated). Recognition is correct only when the linked profile's owner is the
    same person.
    """
    known_before = {owner for owner in owners.values() if owner is not None}
    linked: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in speakers:
        person = dominance.get(row["public_id"], (None, 0.0))[0]
        decision, profile = row.get("decision") or "", row.get("profile_public_id") or ""
        if decision == "enrolled" and profile:
            owners.setdefault(profile, person)
        if person is not None:
            linked[person].append((decision, profile))
    outcomes = []
    for person, seconds in sorted(reference_seconds(reference).items()):
        if seconds < MIN_PROBE_SECONDS:
            continue
        rows = linked.get(person, [])
        if role == "non_gallery":
            accepted = any(decision == "recognized" and profile for decision, profile in rows)
            outcomes.append(
                {"person": person, "kind": "unknown", "outcome": "false_accept" if accepted else "rejected"}
            )
            continue
        claimed = [owners.get(profile) for decision, profile in rows if decision == "recognized" and profile]
        enrolled_here = any(decision == "enrolled" and profile for decision, profile in rows)
        if person not in known_before:
            outcomes.append(
                {"person": person, "kind": "first", "outcome": "enrolled" if enrolled_here else "not_enrolled"}
            )
        elif any(owner != person for owner in claimed):
            outcomes.append({"person": person, "kind": "known", "outcome": "misidentified"})
        elif claimed:
            outcomes.append({"person": person, "kind": "known", "outcome": "correct"})
        elif enrolled_here:
            outcomes.append({"person": person, "kind": "known", "outcome": "duplicate_profile"})
        else:
            outcomes.append({"person": person, "kind": "known", "outcome": "missed"})
    return outcomes


def _annotations(turns: list[dict], reference: list[tuple[float, float, str]]):
    from pyannote.core import Annotation, Segment

    truth, hypothesis = Annotation(), Annotation()
    for index, (start, end, person) in enumerate(reference):
        truth[Segment(start, end), index] = person
    for index, turn in enumerate(turns):
        label = turn["speaker_public_id"] or f"unattributed-{index}"
        hypothesis[Segment(turn["start_seconds"], turn["end_seconds"]), index] = label
    return truth, hypothesis


def der_components(
    turns: list[dict], reference: list[tuple[float, float, str]], uem: tuple[float, float], collar: float
) -> dict[str, float]:
    from pyannote.core import Segment, Timeline
    from pyannote.metrics.diarization import DiarizationErrorRate

    metric = DiarizationErrorRate(collar=collar, skip_overlap=False)
    detail = metric(*_annotations(turns, reference), uem=Timeline([Segment(*uem)]), detailed=True)
    return {
        "total": detail["total"],
        "missed": detail["missed detection"],
        "false_alarm": detail["false alarm"],
        "confusion": detail["confusion"],
    }


def jer_components(
    turns: list[dict], reference: list[tuple[float, float, str]], uem: tuple[float, float], collar: float
) -> dict[str, float]:
    """Per-reference-speaker Jaccard error summed over speakers; pooled as error / count."""
    from pyannote.core import Segment, Timeline
    from pyannote.metrics.diarization import JaccardErrorRate

    metric = JaccardErrorRate(collar=collar, skip_overlap=False)
    detail = metric(*_annotations(turns, reference), uem=Timeline([Segment(*uem)]), detailed=True)
    return {"speaker_count": detail["speaker count"], "speaker_error": detail["speaker error"]}


def diarization_scores(
    turns: list[dict], reference: list[tuple[float, float, str]], uem: tuple[float, float]
) -> dict[str, dict]:
    # pyannote collars are total widths: 0.5 forgives 0.25 s on each side of a boundary.
    return {
        name: {
            "collar_0": function(turns, reference, uem, 0.0),
            "collar_0_25": function(turns, reference, uem, 0.5),
        }
        for name, function in (("der", der_components), ("jer", jer_components))
    }


def rate(top: float, bottom: float) -> float | None:
    return top / bottom if bottom else None


def interval(values: list[float | None]) -> list[float] | None:
    clean = sorted(value for value in values if value is not None)
    if not clean:
        return None
    return [clean[int(0.025 * (len(clean) - 1))], clean[int(0.975 * (len(clean) - 1))]]


def aggregate(meetings: list[dict]) -> dict[str, Any]:
    """Pool meeting results; bootstrap DER by meeting and identity by person."""
    generator = random.Random(BOOTSTRAP_SEED)
    diarization: dict[str, Any] = {"scored_seconds": sum(row["der"]["collar_0"]["total"] for row in meetings)}
    for key in ("collar_0", "collar_0_25"):
        total = sum(row["der"][key]["total"] for row in meetings)
        parts = {name: sum(row["der"][key][name] for row in meetings) for name in ("missed", "false_alarm", "confusion")}
        diarization[key] = {"der": rate(sum(parts.values()), total), **{name: rate(value, total) for name, value in parts.items()}}
        diarization[key]["jer"] = rate(
            sum(row["jer"][key]["speaker_error"] for row in meetings),
            sum(row["jer"][key]["speaker_count"] for row in meetings),
        )

    def pooled_der(sample):
        total = sum(row["der"]["collar_0"]["total"] for row in sample)
        return rate(sum(row["der"]["collar_0"][name] for row in sample for name in ("missed", "false_alarm", "confusion")), total)

    diarization["collar_0_interval"] = interval(
        [pooled_der(generator.choices(meetings, k=len(meetings))) for _ in range(BOOTSTRAP_ROUNDS)]
    )
    outcomes = [outcome for row in meetings for outcome in row["outcomes"]]
    by_person: dict[str, list[dict]] = defaultdict(list)
    for outcome in outcomes:
        by_person[outcome["person"]].append(outcome)

    def tally(sample):
        flat = [item for person in sample for item in by_person[person]]
        known = [item for item in flat if item["kind"] == "known"]
        unknown = [item for item in flat if item["kind"] == "unknown"]
        return (
            rate(sum(item["outcome"] == "correct" for item in known), len(known)),
            rate(sum(item["outcome"] == "false_accept" for item in unknown), len(unknown)),
        )

    people = sorted(by_person)
    samples = [tally(generator.choices(people, k=len(people))) for _ in range(BOOTSTRAP_ROUNDS)]
    first = [item for item in outcomes if item["kind"] == "first"]
    known = [item for item in outcomes if item["kind"] == "known"]
    unknown = [item for item in outcomes if item["kind"] == "unknown"]
    gallery_people = {item["person"] for item in outcomes if item["kind"] in {"first", "known"}}
    first_seen: dict[str, str] = {}
    for item in first:
        first_seen.setdefault(item["person"], item["outcome"])
    identity = {
        "gallery_people": len(gallery_people),
        "enrolled_first": sum(outcome == "enrolled" for outcome in first_seen.values()),
        "enrolled_cumulative": len({item["person"] for item in first if item["outcome"] == "enrolled"}),
        "known_probes": len(known),
        **{name: sum(item["outcome"] == name for item in known) for name in ("correct", "misidentified", "duplicate_profile", "missed")},
        "unknown_probes": len(unknown),
        "false_accept": sum(item["outcome"] == "false_accept" for item in unknown),
    }
    identity["recognition_rate"] = rate(identity["correct"], identity["known_probes"])
    identity["misidentification_rate"] = rate(identity["misidentified"], identity["known_probes"])
    identity["fpir"] = rate(identity["false_accept"], identity["unknown_probes"])
    identity["recognition_interval"] = interval([sample[0] for sample in samples])
    identity["fpir_interval"] = interval([sample[1] for sample in samples])
    return {"diarization": diarization, "identity": identity}


def creation_body(
    step: dict,
    size: int,
    owners: dict[str, str | None],
    *,
    known_speaker_count: bool,
    roster: bool,
) -> dict[str, Any]:
    """Meeting creation request; a roster lists saved profiles of people attending.

    The roster is the oracle invitation list: profiles already owned by this meeting's
    reference people. People not yet enrolled are absent, as unsaved attendees would be.
    """
    body: dict[str, Any] = {
        "title": f"AMI {step['meeting']}",
        "format": "WAV",
        "size_bytes": size,
        "language": "en",
        "auto_enroll": step["role"] == "gallery",
    }
    if known_speaker_count:
        body["expected_speakers"] = body["participant_count"] = len(step["speakers"])
    if roster and step["role"] == "gallery":
        attending = set(step["speakers"])
        body["participant_profile_ids"] = sorted(
            profile for profile, owner in owners.items() if owner in attending
        )
    return body


# ---------------------------------------------------------------- live run


class Runner:
    def __init__(self, args: argparse.Namespace, credentials: dict, state: dict) -> None:
        self.helpers = _helpers()
        self.args, self.state = args, state
        self.credentials = credentials
        self.api = self.helpers.benchmark.Api(args.base_url or credentials["url"], args.api_prefix)

    def save(self) -> None:
        self.helpers.atomic_json(self.args.state, self.state)

    def login(self) -> None:
        result = self.api.json(
            "/auth/login",
            {"username": self.credentials["username"], "password": self.credentials["password"]},
        )
        user = result.get("user", {})
        if user.get("is_super_admin") is not False:
            raise EvaluationError("ordinary_role_required")
        if not REQUIRED_PERMISSIONS <= set(user.get("permissions", [])):
            raise EvaluationError("evaluation_permissions_missing")
        binding = {"tenant": user.get("tenant_id"), "user": user.get("public_id")}
        if self.state.setdefault("binding", binding) != binding:
            raise EvaluationError("resume_binding_mismatch")
        self.api.headers = {
            "Authorization": "Bearer " + result["access_token"],
            "x-tenant-id": binding["tenant"],
        }

    def request(self, method: str, path: str, *, body=None, payload=None, headers=None) -> dict:
        if body is not None:
            payload = json.dumps(body).encode()
            headers = {**(headers or {}), "Content-Type": "application/json"}
        try:
            return self.api.request(method, path, payload=payload, headers=headers)
        except self.helpers.benchmark.BenchmarkFailure as exc:
            if str(exc) != "http_401":
                raise
            self.login()
            return self.api.request(method, path, payload=payload, headers=headers)

    def page(self, path: str) -> list[dict]:
        items: list[dict] = []
        while True:
            result = self.request("GET", f"{path}?offset={len(items)}&limit=100")
            items.extend(result["items"])
            if len(items) >= result["total"] or not result["items"]:
                return items

    def ensure_empty_gallery(self) -> None:
        if "started" not in self.state and self.page("/speaker-profiles"):
            raise EvaluationError("evaluation_tenant_not_empty")
        self.state["started"] = True
        self.save()

    def process(self, step: dict) -> dict:
        checkpoint = self.state["meetings"].setdefault(step["meeting"], {})
        reference = read_rttm(self.args.protocol.parent / step["rttm"], step["meeting"])
        uem = (float(step["uem"][0]), float(step["uem"][1]))
        if "result" in checkpoint:
            result = checkpoint["result"]
            if "jer" not in result:
                # Results checkpointed before JER existed are rescored from the stored turns.
                turns = self.page("/meetings/" + checkpoint["public_id"] + "/speaker-turns")
                result["jer"] = diarization_scores(turns, reference, uem)["jer"]
                self.save()
            return result
        audio = self.args.protocol.parent / step["audio"][self.args.condition]["path"]
        size = audio.stat().st_size
        if "public_id" not in checkpoint:
            body = creation_body(
                step,
                size,
                self.state["owners"],
                known_speaker_count=self.args.known_speaker_count,
                roster=self.args.roster,
            )
            checkpoint["participants"] = len(body.get("participant_profile_ids", []))
            meeting = self.request(
                "POST", "/meetings", body=body, headers={"Idempotency-Key": checkpoint.setdefault("key", str(uuid4()))}
            )
            checkpoint["public_id"] = meeting["public_id"]
            self.save()
        route = "/meetings/" + checkpoint["public_id"]
        meeting = self.request("GET", route)
        if meeting["status"] == "uploading":
            manifest = self.request("GET", route + "/upload-parts")
            uploaded = {part["index"] for part in manifest["parts"]}
            with audio.open("rb") as stream:
                for index in range((size + PART_BYTES - 1) // PART_BYTES):
                    chunk = stream.read(PART_BYTES)
                    if index in uploaded:
                        continue
                    self.request(
                        "PUT",
                        f"{route}/upload-parts/{index}",
                        payload=chunk,
                        headers={
                            "Content-Type": "application/octet-stream",
                            "X-Chunk-SHA256": hashlib.sha256(chunk).hexdigest(),
                        },
                    )
            self.request("POST", route + "/complete")
        started = time.monotonic()
        while meeting["status"] not in {"succeeded", "failed", "cancelled"}:
            if time.monotonic() - started > self.args.timeout:
                raise EvaluationError("meeting_timeout")
            time.sleep(self.args.poll_seconds)
            meeting = self.request("GET", route)
        if meeting["status"] != "succeeded":
            raise EvaluationError("meeting_" + meeting["status"])
        if meeting.get("sha256") != step["audio"][self.args.condition]["sha256"]:
            raise EvaluationError("server_source_hash_mismatch")
        turns = self.page(route + "/speaker-turns")
        speakers = self.page(route + "/speakers")
        outcomes = score_meeting(
            step["role"], speakers, dominant_people(turns, reference, uem), reference, self.state["owners"]
        )
        result = {
            "meeting": step["meeting"],
            "role": step["role"],
            "seconds": meeting.get("duration_seconds"),
            "processing_seconds": round(time.monotonic() - started, 1),
            **diarization_scores(turns, reference, uem),
            "outcomes": outcomes,
        }
        checkpoint["result"] = result
        self.save()
        return result


def run(args: argparse.Namespace) -> dict:
    helpers = _helpers()
    protocol = helpers.read_json(args.protocol)
    if protocol.get("protocol") != PROTOCOL or args.condition not in protocol.get("conditions", []):
        raise EvaluationError("unsupported_protocol")
    credentials = helpers.read_json(args.credentials, maximum=65536)
    state = helpers.read_json(args.state) if args.state.exists() else {}
    configuration = {
        "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
        "condition": args.condition,
        "rotation": args.rotation,
        "use_known_speaker_count": args.known_speaker_count,
        "participant_roster": args.roster,
    }
    # States written before the roster option existed resumed without a roster.
    state.get("configuration", {}).setdefault("participant_roster", False)
    if state.setdefault("configuration", configuration) != configuration:
        raise EvaluationError("resume_configuration_mismatch")
    state.setdefault("meetings", {})
    state.setdefault("owners", {})
    runner = Runner(args, credentials, state)
    runner.login()
    runner.ensure_empty_gallery()
    steps = plan(protocol["meetings"], args.rotation)
    results = []
    for number, step in enumerate(steps, start=1):
        results.append(runner.process(step))
        print(json.dumps({"stage": "meeting_scored", "completed": number, "total": len(steps)}), flush=True)
    report = {
        "status": "complete",
        "protocol": PROTOCOL,
        "protocol_sha256": configuration["protocol_sha256"],
        "condition": args.condition,
        "rotation": args.rotation,
        "use_known_speaker_count": args.known_speaker_count,
        "participant_roster": args.roster,
        "reference_quality": "human-annotated-public",
        "language": "en",
        "planned_meetings": len(steps),
        "observed_meetings": len(results),
        **aggregate(results),
    }
    helpers.atomic_json(args.output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--condition", choices=("headset", "array1"), required=True)
    parser.add_argument("--rotation", type=int, choices=(1, 2), required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--known-speaker-count", action="store_true")
    parser.add_argument(
        "--roster", action="store_true", help="List attending people's saved profiles (PRD 016)"
    )
    parser.add_argument("--base-url")
    parser.add_argument("--api-prefix", default="/api/voiceup/v1")
    parser.add_argument("--timeout", type=float, default=7200)
    parser.add_argument("--poll-seconds", type=float, default=5)
    args = parser.parse_args()
    failure = _helpers().benchmark.BenchmarkFailure
    try:
        report = run(args)
    except (EvaluationError, failure) as exc:
        print(json.dumps({"status": "failed", "code": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({key: report[key] for key in ("status", "condition", "rotation", "observed_meetings")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
