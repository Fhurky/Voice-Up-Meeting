"""Frozen Turkish episode metrics must retain misses and unknown failures."""

import importlib.util
import json
import os
import subprocess
import sys
import wave
from argparse import Namespace
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import create_autospec
from uuid import uuid4

import pytest


@pytest.fixture
def runner():
    path = Path(__file__).parents[1] / "scripts/run-turkish-meeting-evaluation.py"
    spec = importlib.util.spec_from_file_location("turkish_meeting_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_perfect_chain_has_six_new_and_six_return_episodes(runner):
    rows = [
        dict(
            row,
            outcome="recognized" if row["known"] else "unknown",
            predicted=row["speaker_id"] if row["known"] else None,
        )
        for row in runner.planned_episodes()
    ]
    result = runner.score_episodes(rows, complete=True)
    assert result["support"]["known_probes"] == 6
    assert result["support"]["unknown_probes"] == 6
    assert result["identity"]["macro_f1"] == 1
    assert result["voiceup_score"] == 100


def test_failed_first_enrollment_does_not_remove_future_known_support(runner):
    rows = [dict(row, outcome="uncertain", predicted=None) for row in runner.planned_episodes()]
    result = runner.score_episodes(rows, complete=True)
    assert result["identity"]["false_negative"] == 6
    assert result["identity"]["recall"] == 0
    assert result["unknown"]["f1"] == 0
    assert result["decision_coverage"] == 0


def test_wrong_identity_is_both_false_positive_and_false_negative(runner):
    rows = [
        dict(
            row,
            outcome="recognized" if row["known"] else "unknown",
            predicted=row["speaker_id"] if row["known"] else None,
        )
        for row in runner.planned_episodes()
    ]
    row = next(row for row in rows if row["known"])
    row["predicted"] = "p01"
    result = runner.score_episodes(rows, complete=True)
    assert result["identity"]["true_positive"] == 5
    assert result["identity"]["false_positive"] == 1
    assert result["identity"]["false_negative"] == 1
    assert result["identity"]["micro_f1"] == pytest.approx(5 / 6)


def test_incomplete_run_has_no_final_scores(runner):
    result = runner.score_episodes([], complete=False)
    assert result["voiceup_score"] is None
    assert result["identity"]["recall"] is None
    assert result["support"]["known_probes"] == 6


def test_duplicate_episode_is_rejected(runner):
    row = dict(runner.planned_episodes()[0], outcome="unknown", predicted=None)
    with pytest.raises(ValueError, match="episode"):
        runner.score_episodes([row, row], complete=False)


def test_unknown_false_accept_is_not_successful_rejection(runner):
    rows = [
        dict(
            row,
            outcome="recognized" if row["known"] else "unknown",
            predicted=row["speaker_id"] if row["known"] else None,
        )
        for row in runner.planned_episodes()
    ]
    rows[0].update(outcome="recognized", predicted="p01")
    result = runner.score_episodes(rows, complete=True)
    assert result["identity"]["false_positive"] == 1
    assert result["unknown"]["false_negative"] == 1
    assert result["unknown"]["recall"] == pytest.approx(5 / 6)


def protocol_file(runner, tmp_path):
    cases = []
    for index, people in enumerate(runner.CHAIN, 1):
        key = f"rec{index:02}"
        path = tmp_path / (key + ".wav")
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            wav.writeframes(bytes([index, 0]) * 32000)
        cases.append(
            {
                "key": key,
                "path": path.name,
                "speaker_ids": list(people),
                "expected_speakers": 2,
                "sha256": runner.base.source_hash(path),
                "duration_seconds": 2.0,
                "intervals": [
                    {"speaker_id": people[0], "start_seconds": 0.1, "end_seconds": 0.6},
                    {"speaker_id": people[1], "start_seconds": 1.0, "end_seconds": 1.6},
                ],
                "reference": [{"speaker_id": person, "text": "gizli metin"} for person in people],
            }
        )
    value = {
        "schema_version": 1,
        "protocol_id": runner.PROTOCOL,
        "language": "tr",
        "dataset_revision": runner.REVISION,
        "cases": cases,
    }
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path, value


def test_real_protocol_file_validates_without_undeclared_helper(runner, tmp_path):
    path, value = protocol_file(runner, tmp_path)
    assert runner.validate_protocol(path) == value


@pytest.mark.parametrize("mutation", ["duplicate", "oversized", "nan_duration", "truncated"])
def test_invalid_source_or_text_reference_cannot_shrink_scoring_denominator(
    runner, tmp_path, mutation
):
    path, value = protocol_file(runner, tmp_path)
    case = value["cases"][0]
    if mutation == "duplicate":
        case["reference"].append(dict(case["reference"][0], text="omitted words"))
    elif mutation == "oversized":
        case["reference"][0]["text"] = "x" * 500_001
    elif mutation == "nan_duration":
        case["duration_seconds"] = float("nan")
    else:
        audio = tmp_path / case["path"]
        audio.write_bytes(audio.read_bytes()[:-2])
        case["sha256"] = runner.base.source_hash(audio)
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises((ValueError, runner.base.helpers.EvaluationError)):
        runner.validate_protocol(path)


def test_destinations_cannot_alias_sources_or_each_other_through_hardlinks(runner, tmp_path):
    source = tmp_path / "input.json"
    source.write_text("preserved")
    linked = tmp_path / "linked.json"
    os.link(source, linked)
    with pytest.raises((ValueError, runner.base.helpers.EvaluationError)):
        runner.check_paths(tmp_path / "output.json", linked, {source})
    with pytest.raises((ValueError, runner.base.helpers.EvaluationError)):
        runner.check_paths(linked, source, set())
    assert source.read_text() == "preserved"


def test_resume_rejects_duplicate_memory_profiles_and_out_of_order_cases(runner):
    profile = str(uuid4())
    state = {
        "schema_version": 1,
        "run_id": str(uuid4()),
        "status": "incomplete",
        "protocol_sha256": "a" * 64,
        "mapping_policy": runner.base.MAPPING_POLICY,
        "identity_profiles": {"p06": profile, "p03": profile},
        "identity_names": {},
        "cases": {},
    }
    with pytest.raises(ValueError, match="state|profile"):
        runner.validate_state(state, "a" * 64)
    state["identity_profiles"] = {}
    state["cases"] = {"rec02": {"meeting_public_id": str(uuid4())}}
    with pytest.raises(ValueError, match="state|case"):
        runner.validate_state(state, "a" * 64)


def observation_fixture(runner, tmp_path):
    path, protocol = protocol_file(runner, tmp_path)
    case = protocol["cases"][0]
    profiles, tracks = [str(uuid4()) for _ in range(2)], [str(uuid4()) for _ in range(2)]
    speakers = [
        {
            "public_id": track,
            "profile_public_id": profile,
            "decision": "enrolled",
            "profile_deleted": False,
        }
        for track, profile in zip(tracks, profiles)
    ]
    rows = [
        {
            "public_id": str(uuid4()),
            "ordinal": index,
            "speaker_public_id": track,
            "start_seconds": interval["start_seconds"],
            "end_seconds": interval["end_seconds"],
            "text": "gizli metin",
        }
        for index, (track, interval) in enumerate(zip(tracks, case["intervals"]))
    ]
    state = {"identity_profiles": {}, "identity_names": {}, "cases": {"rec01": {}}}
    value = runner.TurkishEvaluation.__new__(runner.TurkishEvaluation)
    value.state = state
    value.args = Namespace(state=tmp_path / "state.private.json")
    value.protocol = protocol
    value.page = create_autospec(
        value.page, side_effect=lambda route: speakers if route.endswith("speakers") else rows
    )
    value.gallery = create_autospec(
        value.gallery, return_value=[{"public_id": p} for p in profiles]
    )
    return value, case, speakers, rows, profiles


def test_duplicate_api_track_id_is_rejected(runner, tmp_path):
    value, case, speakers, _, _ = observation_fixture(runner, tmp_path)
    speakers[1]["public_id"] = speakers[0]["public_id"]
    with pytest.raises((ValueError, runner.base.EvaluationError), match="duplicate|track"):
        value.observe("/meetings/test", case, {"status": "succeeded"})


def test_shared_enrolled_profile_never_creates_two_ground_truth_identities(runner, tmp_path):
    value, case, speakers, _, profiles = observation_fixture(runner, tmp_path)
    speakers[1]["profile_public_id"] = profiles[0]
    value.observe("/meetings/test", case, {"status": "succeeded"})
    assert not value.state["identity_profiles"]
    assert all(row["outcome"] == "uncertain" for row in value.state["cases"]["rec01"]["episodes"])


def test_failed_meeting_keeps_both_reference_episodes_and_all_reference_words(runner, tmp_path):
    value, case, speakers, rows, _ = observation_fixture(runner, tmp_path)
    speakers.clear()
    rows.clear()
    value.observe("/meetings/test", case, {"status": "failed"})
    result = value.state["cases"]["rec01"]
    assert len(result["episodes"]) == 2
    assert all(row["outcome"] == "failed" for row in result["episodes"])
    assert result["transcript_metrics"]["counts"]["reference_words"] == 4
    assert result["transcript_metrics"]["cpwer"]["deletions"] == 4


def cli_arguments(runner, tmp_path):
    protocol, _ = protocol_file(runner, tmp_path)
    credentials = tmp_path / "credentials.private.json"
    credentials.write_text(
        json.dumps(
            {
                "url": "http://127.0.0.1:8081",
                "username": "private-user",
                "password": "private-password",
            }
        ),
        encoding="utf-8",
    )
    return [
        "--protocol",
        str(protocol),
        "--credentials",
        str(credentials),
        "--state",
        str(tmp_path / "state.private.json"),
        "--output",
        str(tmp_path / "result.json"),
    ]


def run_cli(runner, arguments):
    return subprocess.run(
        [sys.executable, str(Path(runner.__file__)), *arguments],
        text=True,
        capture_output=True,
        timeout=15,
    )


def test_existing_files_require_explicit_resume_without_network_or_overwrite(runner, tmp_path):
    arguments = cli_arguments(runner, tmp_path)
    output = tmp_path / "result.json"
    output.write_text("user-owned")
    result = run_cli(runner, arguments)
    assert result.returncode != 0
    assert output.read_text() == "user-owned"
    assert not (tmp_path / "state.private.json").exists()
    assert "private-password" not in result.stderr + result.stdout
    assert "Traceback" not in result.stderr


def test_live_state_lock_rejects_concurrent_process_before_network(runner, tmp_path):
    arguments = cli_arguments(runner, tmp_path)
    with runner.base.helpers.state_lock(tmp_path / "state.private.json"):
        result = run_cli(runner, arguments)
    assert result.returncode != 0
    assert not (tmp_path / "result.json").exists()
    assert not (tmp_path / "state.private.json").exists()
    assert "Traceback" not in result.stderr


def test_duplicate_json_metadata_fields_are_rejected(runner, tmp_path):
    arguments = cli_arguments(runner, tmp_path)
    path = tmp_path / "protocol.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}')
    result = run_cli(runner, arguments)
    assert result.returncode != 0
    assert not (tmp_path / "result.json").exists()
    assert "Traceback" not in result.stderr


def test_incomplete_api_attempt_keeps_resumable_state_and_anonymous_ledger(
    runner, tmp_path, monkeypatch
):
    arguments = cli_arguments(runner, tmp_path)
    metadata = tmp_path / "experiment.json"
    metadata.write_text(
        json.dumps(
            {
                "experiment_id": "tr-chain-smoke",
                "date": "2026-09-13",
                "dataset": "real-turnturk",
                "dataset_revision": runner.REVISION,
                "language": "tr",
                "role": "smoke",
                "pipeline": "meeting-memory",
            }
        )
    )
    ledger = tmp_path / "results.md"
    monkeypatch.syspath_prepend(str(Path(runner.__file__).parent))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            runner.__file__,
            *arguments,
            "--experiment-metadata",
            str(metadata),
            "--results-md",
            str(ledger),
        ],
    )
    execute = create_autospec(
        runner.TurkishEvaluation.execute,
        side_effect=runner.base.benchmark.BenchmarkFailure("http_503"),
    )
    monkeypatch.setattr(runner.TurkishEvaluation, "execute", execute)
    with pytest.raises(runner.base.benchmark.BenchmarkFailure):
        runner.main()
    state = json.loads((tmp_path / "state.private.json").read_text())
    assert state["status"] == "incomplete"
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["support"]["planned_probes"] == 12
    assert report["identity"]["recall"] is None
    published = ledger.read_text(encoding="utf-8")
    assert "tr-chain-smoke" in published
    assert "incomplete" in published
    assert "private-user" not in published
    assert "private-password" not in published
    assert str(tmp_path) not in published
    assert "p06" not in published


def test_resume_will_not_overwrite_unrelated_existing_aggregate(runner, tmp_path, monkeypatch):
    arguments = cli_arguments(runner, tmp_path)
    protocol_hash = runner.base.source_hash(tmp_path / "protocol.json")
    state = {
        "schema_version": 1,
        "run_id": str(uuid4()),
        "status": "incomplete",
        "protocol_sha256": protocol_hash,
        "mapping_policy": runner.base.MAPPING_POLICY,
        "identity_profiles": {},
        "identity_names": {},
        "cases": {},
    }
    (tmp_path / "state.private.json").write_text(json.dumps(state))
    output = tmp_path / "result.json"
    output.write_text('{"unrelated": true}')
    monkeypatch.setattr(sys, "argv", [runner.__file__, *arguments, "--resume"])
    execute = create_autospec(runner.TurkishEvaluation.execute)
    monkeypatch.setattr(runner.TurkishEvaluation, "execute", execute)
    with pytest.raises(ValueError, match="resume_output_mismatch"):
        runner.main()
    assert output.read_text() == '{"unrelated": true}'
    execute.assert_not_called()


@pytest.mark.parametrize("hint", [None, False, True, "legacy"])
def test_known_count_request_body_is_explicit_and_default_bytes_stay_unchanged(
    runner, tmp_path, hint
):
    path, protocol = protocol_file(runner, tmp_path)
    case, meeting_id, observed = protocol["cases"][0], str(uuid4()), []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, value):
            payload = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            observed.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.reply({"public_id": meeting_id})

        def do_GET(self):
            self.reply({"public_id": meeting_id, "status": "succeeded", "sha256": case["sha256"]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        args = Namespace(
            protocol=path,
            state=tmp_path / "state.private.json",
            base_url=f"http://127.0.0.1:{server.server_port}",
            api_prefix="/api/voiceup/v1",
        )
        if hint is not None and hint != "legacy":
            args.use_known_speaker_count = hint
        evaluation_class = (
            runner.base.MeetingEvaluation if hint == "legacy" else runner.TurkishEvaluation
        )
        value = evaluation_class(args, protocol, {}, {"run_id": str(uuid4()), "cases": {}})
        value.upload("rec01", case)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    expected = {
        "title": "Evaluation rec01",
        "format": "WAV",
        "size_bytes": (tmp_path / case["path"]).stat().st_size,
        "language": "en" if hint == "legacy" else "tr",
        "auto_enroll": True,
    }
    if hint is True:
        expected.update(expected_speakers=2, participant_count=2)
    assert observed == [json.dumps(expected).encode()]


def test_resume_count_mode_cannot_change_and_legacy_state_means_no_hint(runner):
    state = {
        "schema_version": 1,
        "run_id": str(uuid4()),
        "status": "incomplete",
        "protocol_sha256": "a" * 64,
        "mapping_policy": runner.base.MAPPING_POLICY,
        "identity_profiles": {},
        "identity_names": {},
        "cases": {},
    }
    runner.validate_state(state, "a" * 64, use_known_speaker_count=False)
    with pytest.raises(ValueError, match="count"):
        runner.validate_state(state, "a" * 64, use_known_speaker_count=True)
    state["use_known_speaker_count"] = True
    runner.validate_state(state, "a" * 64, use_known_speaker_count=True)
    with pytest.raises(ValueError, match="count"):
        runner.validate_state(state, "a" * 64, use_known_speaker_count=False)


def test_first_enrollment_coverage_does_not_count_late_enrollment_as_first_success(runner):
    episodes = [
        dict(
            row,
            outcome="recognized" if row["known"] else "unknown",
            predicted=row["speaker_id"] if row["known"] else None,
        )
        for row in runner.planned_episodes()
    ]
    for row in [r for r in episodes if not r["known"]][:2]:
        row.update(outcome="uncertain", predicted=None)
    state = {
        "status": "complete",
        "protocol_sha256": "a" * 64,
        "identity_profiles": {str(i): str(uuid4()) for i in range(6)},
        "cases": {
            f"rec{i:02}": {
                "episodes": [r for r in episodes if r["case"] == f"rec{i:02}"],
                "observed": True,
            }
            for i in range(1, 7)
        },
    }
    report = runner.aggregate(state, {"cases": []})
    assert report["enrollment_coverage"] == 1.0
    assert report["first_enrollment_coverage"] == pytest.approx(4 / 6)
    state["status"] = "incomplete"
    assert runner.aggregate(state, {"cases": []})["first_enrollment_coverage"] is None


def expanded_protocol(runner, start=300):
    producer = runner.producer
    return {
        "protocol_id": f"voiceup-real-turnturk-window{start}-v1",
        "source_manifest_sha256": producer.SOURCE_MANIFEST_SHA256,
        "selection": {"start_seconds": start, "duration_seconds": 300},
        "reference_quality": {"activity": "automatic-silero", "transcript": "unverified-source"},
        "mixing": {"sample_rate": 16000, "format": "PCM_16", "gain_per_channel": 0.5},
        "timeline_policy": "decoded-sample-clock-v1",
        "timeline_alignment": "unverified-source-timestamps",
    }


@pytest.mark.parametrize("start", [300, 600])
def test_new_protocol_identity_pins_selection_and_source_contract(runner, start):
    value = expanded_protocol(runner, start)
    assert runner.validate_selection(value) == value["selection"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("selection", {"start_seconds": 0, "duration_seconds": 300}),
        ("selection", {"start_seconds": 300, "duration_seconds": 180}),
        ("selection", {"start_seconds": 300, "duration_seconds": 300, "extra": 1}),
        ("source_manifest_sha256", "0" * 64),
        ("timeline_policy", "pts-clock"),
        ("timeline_alignment", "human-verified"),
        ("reference_quality", {"activity": "gold", "transcript": "unverified-source"}),
        ("mixing", {"sample_rate": 16000, "format": "PCM_16", "gain_per_channel": 1}),
    ],
)
def test_new_protocol_cannot_relabel_old_audio_or_invent_gold_reference(runner, field, value):
    protocol = expanded_protocol(runner)
    protocol[field] = value
    with pytest.raises(ValueError, match="invalid_excerpt_selection"):
        runner.validate_selection(protocol)


def test_expanded_aggregate_keeps_metric_math_and_names_temporal_scope(runner):
    protocol = expanded_protocol(runner)
    protocol["cases"] = [{"key": "rec01", "sha256": "a" * 64, "duration_seconds": 300}]
    state = {
        "status": "incomplete",
        "protocol_sha256": "b" * 64,
        "identity_profiles": {},
        "cases": {"rec01": {"observed": True}},
    }
    report = runner.aggregate(state, protocol)
    assert report["metrics_protocol"] == runner.PROTOCOL
    assert report["source_protocol_id"] == protocol["protocol_id"]
    assert report["selection"] == {"start_seconds": 300, "duration_seconds": 300}
    assert report["source_sessions"] == 6
    assert report["planned_audio_seconds"] == 1800
    assert report["observed_audio_seconds"] == 300
    assert report["support"]["planned_probes"] == 12


def test_resume_cannot_change_preset_even_if_declared_state_hash_is_replaced(runner):
    protocol = expanded_protocol(runner)
    state = {
        "schema_version": 1,
        "run_id": str(uuid4()),
        "status": "incomplete",
        "protocol_sha256": "a" * 64,
        "mapping_policy": runner.base.MAPPING_POLICY,
        "identity_profiles": {},
        "identity_names": {},
        "cases": {},
        "source_protocol_id": protocol["protocol_id"],
        "selection": protocol["selection"],
    }
    runner.validate_state(state, "a" * 64, source_protocol=protocol)
    state["source_protocol_id"] = "voiceup-real-turnturk-window600-v1"
    with pytest.raises(ValueError, match="resume_source_selection_mismatch"):
        runner.validate_state(state, "a" * 64, source_protocol=protocol)


@pytest.mark.parametrize("mutation", ["source", "duration", "offset", "insufficient_audio"])
def test_new_source_binding_and_sample_offset_cannot_be_substituted(runner, mutation):
    value = expanded_protocol(runner)
    case = {
        "source": runner.producer.source_binding(0),
        "duration_seconds": 300,
        "decoding": {
            channel: {
                "selection_start_samples": 4_800_000,
                "selected_samples": 4_800_000,
                "output_samples": 15_000_000,
                "timeline_policy": "decoded-sample-clock-v1",
                "timeline_alignment": "unverified-source-timestamps",
            }
            for channel in ("left", "right")
        },
    }
    runner.validate_source_selection(case, 0, value["selection"])
    if mutation == "source":
        case["source"] = runner.producer.source_binding(1)
    elif mutation == "duration":
        case["duration_seconds"] = 180
    elif mutation == "offset":
        case["decoding"]["left"]["selection_start_samples"] = 0
    else:
        case["decoding"]["left"]["output_samples"] = 9_000_000
    with pytest.raises(ValueError, match="source_selection"):
        runner.validate_source_selection(case, 0, value["selection"])
