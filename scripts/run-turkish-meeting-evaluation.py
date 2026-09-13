"""Replay a pinned real Turkish conversation chain through the local application.

Automatic activity and unverified source text are diagnostic references, not gold.
The private checkpoint contains transcript/identity data; only aggregates may publish.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
import wave
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

from voiceup.meeting_metrics import score_transcript


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "turkish_existing_meeting_runner", Path(__file__).with_name("run-meeting-evaluation.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_runner()


def load_producer():
    spec = importlib.util.spec_from_file_location(
        "turkish_meeting_producer",
        Path(__file__).with_name("prepare-turkish-meeting-evaluation.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


producer = load_producer()
CHAIN = (
    ("p06", "p03"),
    ("p04", "p06"),
    ("p03", "p01"),
    ("p01", "p02"),
    ("p05", "p06"),
    ("p04", "p01"),
)
PROTOCOL = "voiceup-real-turnturk-v1"
REVISION = "db8f20f6eb6b215ec75fb466374fc5cc861b91df"
MAX_REFERENCE_CHARACTERS = 500_000
TERMINAL = {"succeeded", "failed", "cancelled"}


def checked_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("linked_path_refused")
    return path


def read_document(path, maximum=16 * 1024 * 1024):
    def unique_fields(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_field")
            result[key] = value
        return result

    def reject_constant(_value):
        raise ValueError("invalid_json_constant")

    with checked_path(path).open("rb") as stream:
        payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise ValueError("json_input_limit")
    return json.loads(payload, object_pairs_hook=unique_fields, parse_constant=reject_constant)


def check_paths(output, state, protected):
    output, state = checked_path(output), checked_path(state)
    protected = {checked_path(path) for path in protected}
    base.helpers.check_output_paths(output, state, protected)
    if output.exists() and state.exists() and output.samefile(state):
        raise ValueError("aliased_destinations")
    for path in (output, state):
        if path.exists() and (not path.is_file() or path.stat().st_nlink > 1):
            raise ValueError("linked_destination")
        lock = checked_path(path.with_suffix(path.suffix + ".lock"))
        if lock.exists() and (not lock.is_file() or lock.stat().st_nlink > 1):
            raise ValueError("linked_lock_path")


def validate_state(state, protocol_hash, *, use_known_speaker_count=False, source_protocol=None):
    if (
        not isinstance(state, dict)
        or type(state.get("schema_version")) is not int
        or state["schema_version"] != 1
        or state.get("protocol_sha256") != protocol_hash
        or state.get("mapping_policy") != base.MAPPING_POLICY
        or state.get("status") not in {"running", "incomplete", "complete"}
        or not isinstance(state.get("identity_profiles"), dict)
        or not isinstance(state.get("identity_names"), dict)
        or not isinstance(state.get("cases"), dict)
    ):
        raise ValueError("invalid_resume_state")
    if source_protocol is not None and source_protocol.get("protocol_id") != PROTOCOL:
        if (
            state.get("source_protocol_id") != source_protocol["protocol_id"]
            or state.get("selection") != source_protocol["selection"]
        ):
            raise ValueError("resume_source_selection_mismatch")
    prior_hint = state.get("use_known_speaker_count", False)
    if (
        type(prior_hint) is not bool
        or type(use_known_speaker_count) is not bool
        or prior_hint != use_known_speaker_count
    ):
        raise ValueError("resume_speaker_count_mode_mismatch")
    base.identifier(state.get("run_id"))
    memory = state["identity_profiles"]
    if not set(memory) <= {person for people in CHAIN for person in people}:
        raise ValueError("invalid_state_profile")
    profiles = [base.identifier(profile) for profile in memory.values()]
    if len(set(profiles)) != len(profiles):
        raise ValueError("duplicate_state_profile")
    keys = [f"rec{i:02}" for i in range(1, 7)]
    cases = state["cases"]
    if set(cases) != set(keys[: len(cases)]):
        raise ValueError("invalid_state_case_order")
    all_episodes = []
    for index, key in enumerate(keys[: len(cases)]):
        case = cases[key]
        if not isinstance(case, dict):
            raise ValueError("invalid_state_case")
        base.identifier(case.get("meeting_public_id"))
        observed = case.get("observed", False)
        if type(observed) is not bool or (not observed and index != len(cases) - 1):
            raise ValueError("invalid_state_case_order")
        if observed:
            episodes = case.get("episodes")
            expected = {
                (row["case"], row["speaker_id"]) for row in planned_episodes() if row["case"] == key
            }
            if (
                case.get("terminal_status") not in TERMINAL
                or not isinstance(episodes, list)
                or len(episodes) != 2
                or {(row["case"], row["speaker_id"]) for row in episodes} != expected
            ):
                raise ValueError("invalid_observed_state_case")
            all_episodes.extend(episodes)
    if state["status"] == "complete" and (
        len(cases) != 6 or not all(c.get("observed") is True for c in cases.values())
    ):
        raise ValueError("incomplete_state_cases")
    score_episodes(all_episodes, complete=state["status"] == "complete")
    if (memory or cases) and state.get("initial_gallery_verified") is not True:
        raise ValueError("unverified_initial_state")


def planned_episodes():
    seen, rows = set(), []
    for index, people in enumerate(CHAIN, 1):
        for person in people:
            rows.append({"case": f"rec{index:02}", "speaker_id": person, "known": person in seen})
        seen.update(people)
    return rows


def score_episodes(rows, *, complete):
    if type(complete) is not bool or not isinstance(rows, list) or len(rows) > 12:
        raise ValueError("invalid_episode_population")
    planned = {(r["case"], r["speaker_id"]): r for r in planned_episodes()}
    seen = set()
    for row in rows:
        key = (row["case"], row["speaker_id"])
        if (
            key in seen
            or key not in planned
            or row["known"] is not planned[key]["known"]
            or row["outcome"] not in {"recognized", "unknown", "uncertain", "failed"}
            or (row["outcome"] == "recognized") != (row["predicted"] is not None)
            or row["predicted"] not in {None, "unmapped", "p01", "p02", "p03", "p04", "p05", "p06"}
        ):
            raise ValueError("invalid_episode")
        seen.add(key)
    if complete and seen != set(planned):
        raise ValueError("incomplete_episodes")
    known = sum(row["known"] for row in planned.values())
    unknown = len(planned) - known
    tp = sum(
        row["known"] and row["outcome"] == "recognized" and row["predicted"] == row["speaker_id"]
        for row in rows
    )
    fp = sum(
        row["outcome"] == "recognized"
        and (not row["known"] or row["predicted"] != row["speaker_id"])
        for row in rows
    )
    utp = sum(not row["known"] and row["outcome"] == "unknown" for row in rows)
    ufp = sum(row["known"] and row["outcome"] == "unknown" for row in rows)

    def ratio(a, b):
        return a / b if b and complete else None

    per_person = []
    for person in sorted({row["speaker_id"] for row in planned.values() if row["known"]}):
        support = sum(row["known"] and row["speaker_id"] == person for row in planned.values())
        correct = sum(
            row["known"] and row["speaker_id"] == person and row["predicted"] == person
            for row in rows
        )
        wrong = sum(
            row["predicted"] == person and (not row["known"] or row["speaker_id"] != person)
            for row in rows
        )
        per_person.append(2 * correct / (correct + wrong + support))
    macro = sum(per_person) / len(per_person) if complete else None
    uf1 = ratio(2 * utp, utp + ufp + unknown)
    return {
        "support": {
            "known_probes": known,
            "unknown_probes": unknown,
            "known_speakers": len(per_person),
            "unique_speakers": 6,
            "observed_probes": len(rows),
            "planned_probes": len(planned),
        },
        "identity": {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": known - tp,
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, known),
            "micro_f1": ratio(2 * tp, tp + fp + known),
            "macro_f1": macro,
        },
        "unknown": {
            "true_positive": utp,
            "false_positive": ufp,
            "false_negative": unknown - utp,
            "precision": ratio(utp, utp + ufp),
            "recall": ratio(utp, unknown),
            "f1": uf1,
        },
        "decision_coverage": ratio(
            sum(r["outcome"] in {"recognized", "unknown"} for r in rows), len(planned)
        ),
        "voiceup_score": (200 * macro * uf1 / (macro + uf1) if macro + uf1 else 0)
        if complete
        else None,
    }


def validate_selection(value):
    protocol_id = value.get("protocol_id")
    if protocol_id == PROTOCOL:
        return None
    preset = next((row for row in producer.PRESETS.values() if row[0] == protocol_id), None)
    if preset is None:
        raise ValueError("invalid_turkish_protocol")
    expected = {"start_seconds": preset[1], "duration_seconds": preset[2]}
    if (
        value.get("selection") != expected
        or any(type(v) is not int for v in value["selection"].values())
        or value.get("source_manifest_sha256") != producer.SOURCE_MANIFEST_SHA256
        or value.get("reference_quality")
        != {"activity": "automatic-silero", "transcript": "unverified-source"}
        or value.get("mixing")
        != {"sample_rate": 16000, "format": "PCM_16", "gain_per_channel": 0.5}
        or value.get("timeline_policy") != "decoded-sample-clock-v1"
        or value.get("timeline_alignment") != "unverified-source-timestamps"
    ):
        raise ValueError("invalid_excerpt_selection")
    return expected


def validate_source_selection(case, index, selection):
    if case.get("source") != producer.source_binding(index):
        raise ValueError("source_selection_binding_mismatch")
    if case.get("duration_seconds") != selection["duration_seconds"]:
        raise ValueError("source_selection_duration_mismatch")
    decoding = case.get("decoding")
    if not isinstance(decoding, dict) or set(decoding) != {"left", "right"}:
        raise ValueError("source_selection_decoding_mismatch")
    start = selection["start_seconds"] * 16000
    samples = selection["duration_seconds"] * 16000
    for info in decoding.values():
        if (
            not isinstance(info, dict)
            or type(info.get("selection_start_samples")) is not int
            or info["selection_start_samples"] != start
            or type(info.get("selected_samples")) is not int
            or info["selected_samples"] != samples
            or type(info.get("output_samples")) is not int
            or info["output_samples"] < start + samples
            or info.get("timeline_policy") != "decoded-sample-clock-v1"
            or info.get("timeline_alignment") != "unverified-source-timestamps"
        ):
            raise ValueError("source_selection_decoding_mismatch")


def validate_protocol(path):
    path = checked_path(path)
    value = read_document(path)
    if (
        not isinstance(value, dict)
        or type(value.get("schema_version")) is not int
        or value["schema_version"] != 1
        or value.get("language") != "tr"
        or value.get("dataset_revision") != REVISION
        or not isinstance(value.get("cases"), list)
        or len(value["cases"]) != 6
    ):
        raise ValueError("invalid_turkish_protocol")
    selection = validate_selection(value)
    hashes = set()
    for i, (case, people) in enumerate(zip(value["cases"], CHAIN, strict=True), 1):
        key = f"rec{i:02}"
        if (
            not isinstance(case, dict)
            or case.get("key") != key
            or case.get("path") != key + ".wav"
            or case.get("speaker_ids") != list(people)
            or type(case.get("expected_speakers")) is not int
            or case["expected_speakers"] != 2
        ):
            raise ValueError("invalid_case")
        if selection is not None:
            validate_source_selection(case, i - 1, selection)
        audio = checked_path(path.parent / case["path"])
        if (
            not audio.is_file()
            or not 44 < audio.stat().st_size <= 20 * 1024 * 1024
            or base.source_hash(audio) != case.get("sha256")
            or case["sha256"] in hashes
        ):
            raise ValueError("source_hash_mismatch")
        hashes.add(case["sha256"])
        with wave.open(str(audio), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (
                1,
                2,
                16000,
                "NONE",
            ):
                raise ValueError("invalid_wav")
            frames = 0
            while pcm := wav.readframes(32768):
                if len(pcm) % 2:
                    raise ValueError("truncated_wav")
                frames += len(pcm) // 2
            if frames != wav.getnframes():
                raise ValueError("truncated_wav")
        if (
            not 0 < duration <= 600
            or abs(duration - base.finite(case["duration_seconds"])) > 1 / 16000
        ):
            raise ValueError("invalid_duration")
        previous = defaultdict(float)
        if not isinstance(case.get("intervals"), list) or not 2 <= len(case["intervals"]) <= 10_000:
            raise ValueError("invalid_activity_reference")
        for interval in case["intervals"]:
            if not isinstance(interval, dict):
                raise ValueError("invalid_activity_reference")
            person = interval["speaker_id"]
            start, end = (
                base.finite(interval["start_seconds"]),
                base.finite(interval["end_seconds"]),
            )
            if person not in people or not previous[person] <= start < end <= duration + 1 / 16000:
                raise ValueError("invalid_activity_reference")
            previous[person] = end
        if set(previous) != set(people):
            raise ValueError("missing_activity_reference")
        references = case.get("reference")
        if (
            not isinstance(references, list)
            or len(references) != 2
            or any(
                not isinstance(r, dict)
                or set(r) != {"speaker_id", "text"}
                or not isinstance(r["text"], str)
                or not 0 < len(r["text"]) <= MAX_REFERENCE_CHARACTERS
                or not r["text"].strip()
                for r in references
            )
            or {r["speaker_id"] for r in references} != set(people)
        ):
            raise ValueError("invalid_text_reference")
    return value


class TurkishEvaluation(base.MeetingEvaluation):
    def creation_body(self, key: str, size: int) -> dict:
        body = super().creation_body(key, size)
        body["language"] = "tr"
        if getattr(self.args, "use_known_speaker_count", False):
            body.update(expected_speakers=2, participant_count=2)
        return body

    def analyze(self, route, key, case):
        meeting = self.request("POST", route + "/complete")
        started = time.monotonic()
        while meeting.get("status") in {"queued", "running", "finalizing"}:
            if time.monotonic() - started >= self.args.timeout:
                raise ValueError("meeting_timeout")
            time.sleep(self.args.poll_seconds)
            meeting = self.request("GET", route)
        if (
            meeting.get("public_id") != route.rsplit("/", 1)[1]
            or meeting.get("sha256") != case["sha256"]
            or meeting.get("status") not in TERMINAL
        ):
            raise ValueError("meeting_source_mismatch")
        self.state["cases"][key]["terminal_status"] = meeting.get("status")
        self.save()
        return meeting

    def observe(self, route, case, meeting):
        key = case["key"]
        checkpoint = self.state["cases"][key]
        speakers = self.page(route + "/speakers")
        rows = self.page(route + "/transcript")
        tracks = {base.identifier(row["public_id"]): row for row in speakers}
        if len(tracks) != len(speakers):
            raise ValueError("duplicate_api_track")
        gallery = self.gallery()
        self.verify_recorded_memory(gallery)
        gallery_ids = {base.identifier(row["public_id"]) for row in gallery}
        profile_counts = Counter(
            base.identifier(row["profile_public_id"])
            for row in speakers
            if row.get("profile_public_id") is not None
        )
        # A time point with two active reference channels must not vote twice.
        exclusive = exclusive_intervals(case["intervals"])
        mapping = base.map_identities(
            exclusive, rows, set(tracks), duration_seconds=case["duration_seconds"]
        )
        invalid = set(
            mapping["missing_identities"]
            + mapping["split_identities"]
            + mapping["weak_majority_identities"]
        )
        inverse = {
            profile: identity for identity, profile in self.state["identity_profiles"].items()
        }
        episodes = []
        for expected in [r for r in planned_episodes() if r["case"] == key]:
            person = expected["speaker_id"]
            track = mapping["mapping"].get(person)
            outcome, predicted = "uncertain", None
            if meeting.get("status") != "succeeded":
                outcome = "failed"
            elif person not in invalid and track and track not in mapping["merged_tracks"]:
                speaker = tracks[track]
                profile = speaker.get("profile_public_id")
                usable = (
                    profile in gallery_ids
                    and speaker.get("profile_deleted") is False
                    and profile_counts[profile] == 1
                )
                if usable and speaker.get("decision") == "recognized":
                    outcome, predicted = "recognized", inverse.get(profile, "unmapped")
                elif usable and speaker.get("decision") == "enrolled" and profile not in inverse:
                    outcome = "unknown"
                    if person not in self.state["identity_profiles"]:
                        self.state["identity_profiles"][person] = base.identifier(profile)
                        inverse[profile] = person
            episodes.append(dict(expected, outcome=outcome, predicted=predicted))
        hypothesis = defaultdict(str)
        for row in sorted(rows, key=lambda row: row["ordinal"]):
            hypothesis[row.get("speaker_public_id")] += " " + row["text"]
        metrics = score_transcript(
            {r["speaker_id"]: r["text"] for r in case["reference"]},
            dict(hypothesis),
            normalization="turkish-words-v1",
        )
        for kind in ("cpwer", "assigned_only"):
            metrics[kind].pop("assignment", None)
        checkpoint.update(
            episodes=episodes,
            mapping=mapping,
            transcript_metrics=metrics,
            observed_tracks=len(tracks),
            gallery_total=len(gallery),
            observed=True,
            transcript=rows,
            speakers=speakers,
        )
        self.save()

    def execute(self):
        self.login()
        if not self.state.get("initial_gallery_verified"):
            self.gallery(0)
            self.state["initial_gallery_verified"] = True
            self.save()
        else:
            self.verify_recorded_memory(self.gallery())
        for case in self.protocol["cases"]:
            key = case["key"]
            if self.state["cases"].get(key, {}).get("observed"):
                continue
            route, _ = self.upload(key, case)
            meeting = self.analyze(route, key, case)
            self.observe(route, case, meeting)
            print(f"{key}: {meeting['status']}; diagnostic observation saved", flush=True)
        self.state["status"] = "complete"
        self.save()


def exclusive_intervals(intervals):
    boundaries = sorted({r[k] for r in intervals for k in ("start_seconds", "end_seconds")})
    result = []
    for start, end in zip(boundaries, boundaries[1:]):
        active = {
            r["speaker_id"] for r in intervals if r["start_seconds"] <= start < r["end_seconds"]
        }
        if len(active) == 1:
            person = next(iter(active))
            if result and result[-1]["speaker_id"] == person and result[-1]["end_seconds"] == start:
                result[-1]["end_seconds"] = end
            else:
                result.append({"speaker_id": person, "start_seconds": start, "end_seconds": end})
    return result


def aggregate(state, protocol):
    complete = state["status"] == "complete"
    rows = [r for case in state["cases"].values() for r in case.get("episodes", [])]
    result = score_episodes(rows, complete=complete)
    result.update(
        schema_version=1,
        metrics_protocol=PROTOCOL,
        status=state["status"],
        language="tr",
        dataset_revision=REVISION,
        protocol_sha256=state["protocol_sha256"],
        reference_quality="automatic-activity-unverified-text-diagnostic",
        planned_meetings=6,
        observed_meetings=sum(c.get("observed", False) for c in state["cases"].values()),
        enrollment_coverage=len(state["identity_profiles"]) / 6 if complete else None,
        first_enrollment_coverage=sum(
            not row["known"] and row["outcome"] == "unknown" for row in rows
        )
        / 6
        if complete
        else None,
        use_known_speaker_count=state.get("use_known_speaker_count", False),
        meetings=[],
    )
    if protocol.get("protocol_id", PROTOCOL) != PROTOCOL:
        result.update(
            source_protocol_id=protocol["protocol_id"],
            selection=protocol["selection"],
            source_sessions=6,
            planned_audio_seconds=6 * protocol["selection"]["duration_seconds"],
            observed_audio_seconds=sum(
                case["duration_seconds"]
                for case in protocol["cases"]
                if state["cases"].get(case["key"], {}).get("observed", False)
            ),
        )
    for case in protocol["cases"]:
        observed = state["cases"].get(case["key"], {})
        result["meetings"].append(
            {
                "case": case["key"],
                "source_sha256": case["sha256"],
                "status": observed.get("terminal_status", "unobserved"),
                "observed_tracks": observed.get("observed_tracks"),
                "gallery_total": observed.get("gallery_total"),
                "transcript_metrics": observed.get("transcript_metrics"),
                "mapping_passed": observed.get("mapping", {}).get("passed"),
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "credentials", "state", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--api-prefix", default="/api/voiceup/v1")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--use-known-speaker-count", action="store_true")
    parser.add_argument("--experiment-metadata", type=Path)
    parser.add_argument("--results-md", type=Path)
    args = parser.parse_args()
    if args.results_md is not None and args.experiment_metadata is None:
        parser.error("--results-md requires --experiment-metadata")
    if (
        not math.isfinite(args.timeout)
        or not 0 < args.timeout <= 86400
        or not math.isfinite(args.poll_seconds)
        or not 0.1 <= args.poll_seconds <= 10
    ):
        raise ValueError("invalid_poll_settings")
    protocol = validate_protocol(args.protocol)
    protected = {
        args.protocol,
        args.credentials,
        *(args.protocol.parent / case["path"] for case in protocol["cases"]),
    }
    if args.experiment_metadata is not None:
        protected.add(args.experiment_metadata)
        args.results_md = checked_path(
            args.results_md or Path(__file__).resolve().parents[1] / "results.md"
        )
        if args.results_md.suffix.lower() != ".md" or any(
            args.results_md.resolve() == path.resolve()
            or (args.results_md.exists() and path.exists() and args.results_md.samefile(path))
            for path in protected | {args.output, args.state}
        ):
            raise ValueError("ledger_source_path_conflict")
        protected.add(args.results_md)
    check_paths(args.output, args.state, protected)
    credentials = read_document(args.credentials, maximum=65536)
    if not isinstance(credentials, dict) or any(
        not isinstance(credentials.get(key), str) or not credentials[key]
        for key in ("url", "username", "password")
    ):
        raise ValueError("invalid_credentials_file")
    digest = hashlib.sha256(args.protocol.read_bytes()).hexdigest()
    with ExitStack() as locks:
        for path in sorted((args.state, args.output), key=lambda path: str(path.resolve())):
            locks.enter_context(base.helpers.state_lock(path))
        check_paths(args.output, args.state, protected)
        if not args.resume and (args.state.exists() or args.output.exists()):
            raise ValueError("output_exists_use_resume")
        if args.resume:
            state = read_document(args.state)
            validate_state(
                state,
                digest,
                use_known_speaker_count=args.use_known_speaker_count,
                source_protocol=protocol,
            )
            if args.output.exists():
                previous = read_document(args.output)
                if (
                    not isinstance(previous, dict)
                    or previous.get("protocol_sha256") != digest
                    or previous.get("metrics_protocol") != PROTOCOL
                    or (
                        protocol["protocol_id"] != PROTOCOL
                        and (
                            previous.get("source_protocol_id") != protocol["protocol_id"]
                            or previous.get("selection") != protocol["selection"]
                        )
                    )
                ):
                    raise ValueError("resume_output_mismatch")
        else:
            state = {
                "schema_version": 1,
                "run_id": str(uuid4()),
                "protocol_sha256": digest,
                "status": "incomplete",
                "mapping_policy": base.MAPPING_POLICY,
                "use_known_speaker_count": args.use_known_speaker_count,
                "identity_profiles": {},
                "identity_names": {},
                "cases": {},
            }
            if protocol["protocol_id"] != PROTOCOL:
                state.update(
                    source_protocol_id=protocol["protocol_id"], selection=protocol["selection"]
                )
        runner = TurkishEvaluation(args, protocol, credentials, state)
        try:
            runner.save()
            runner.execute()
        finally:
            report = aggregate(state, protocol)
            base.helpers.atomic_json(args.output, report)
            if args.experiment_metadata is not None:
                from experiment_ledger import DEFAULT_LEDGER, record_from_metadata_file

                record_from_metadata_file(
                    args.results_md or DEFAULT_LEDGER,
                    args.experiment_metadata,
                    report=report,
                    kind="meeting_identity",
                )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        AttributeError,
        OverflowError,
        RecursionError,
        wave.Error,
        base.EvaluationError,
        base.helpers.EvaluationError,
        base.benchmark.BenchmarkFailure,
    ):
        raise SystemExit(
            "Turkish evaluation incomplete; aggregate checkpoint retained when available."
        ) from None
