"""Evaluation mapping, frozen source validation and loopback-only transport."""

import hashlib
import importlib.util
import json
import sys
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-meeting-evaluation.py"


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location("meeting_http_evaluation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def transcript(track, start, end, ordinal=0):
    return {
        "public_id": str(uuid4()),
        "ordinal": ordinal,
        "speaker_public_id": track,
        "start_seconds": start,
        "end_seconds": end,
        "text": "Private fixture text",
        "uncertain": False,
        "overlap": False,
    }


def test_mapping_uses_union_seconds_without_duplicate_word_votes(runner):
    first, second = str(uuid4()), str(uuid4())
    intervals = [
        {"speaker_id": "ls-1", "start_seconds": 0, "end_seconds": 4},
        {"speaker_id": "ls-2", "start_seconds": 5, "end_seconds": 9},
    ]
    rows = [transcript(first, 0, 3), transcript(first, 1, 4, 1), transcript(second, 5, 9, 2)]
    result = runner.map_identities(intervals, rows, {first, second})
    assert result["mapping"] == {"ls-1": first, "ls-2": second}
    assert result["votes_seconds"]["ls-1"][first] == 4
    assert result["passed"]
    assert "Private fixture text" not in json.dumps(result)


def test_material_split_is_a_failure_even_when_main_track_is_closest(runner):
    first, second = str(uuid4()), str(uuid4())
    result = runner.map_identities(
        [{"speaker_id": "ls-1", "start_seconds": 0, "end_seconds": 10}],
        [transcript(first, 0, 8), transcript(second, 8, 10, 1)],
        {first, second},
    )
    assert not result["passed"] and result["split_identities"] == ["ls-1"]


def test_two_people_mapping_to_one_track_is_explicit_merge_failure(runner):
    track = str(uuid4())
    result = runner.map_identities(
        [
            {"speaker_id": "ls-1", "start_seconds": 0, "end_seconds": 2},
            {"speaker_id": "ls-2", "start_seconds": 3, "end_seconds": 5},
        ],
        [transcript(track, 0, 2), transcript(track, 3, 5, 1)],
        {track},
    )
    assert not result["passed"] and result["merged_tracks"] == [track]


def test_frozen_boundary_tolerance_does_not_hide_missing_text(runner):
    first, second = str(uuid4()), str(uuid4())
    interval = [{"speaker_id": "ls-1", "start_seconds": 0, "end_seconds": 10}]
    result = runner.map_identities(
        interval, [transcript(first, 0, 9.8), transcript(second, 9.8, 10, 1)], {first, second}
    )
    assert result["passed"] and not result["split_identities"]
    missing = runner.map_identities(interval, [], {first})
    assert not missing["passed"] and missing["missing_identities"] == ["ls-1"]


@pytest.mark.parametrize(
    "change",
    [
        {"start_seconds": float("nan")},
        {"end_seconds": -1},
        {"speaker_public_id": "not-a-uuid"},
        {"ordinal": True},
    ],
)
def test_malformed_transcript_cannot_become_a_score(runner, change):
    track = str(uuid4())
    row = transcript(track, 0, 1)
    row.update(change)
    with pytest.raises(runner.EvaluationError):
        runner.map_identities(
            [{"speaker_id": "ls-1", "start_seconds": 0, "end_seconds": 2}], [row], {track}
        )


def fixture_protocol(tmp_path: Path):
    identities = [f"ls-{index}" for index in range(6)]
    cases = []
    for name, count, gallery in zip(
        [
            "meeting-a-five.wav",
            "meeting-b-return.wav",
            "meeting-d-short-sixth.wav",
            "meeting-c-sixth-new.wav",
        ],
        [5, 5, 6, 6],
        [5, 5, 5, 6],
        strict=True,
    ):
        path = tmp_path / name
        with wave.open(str(path), "wb") as target:
            target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            target.writeframes(b"\x01\x00" * (count * 16000))
        intervals = [
            {
                "speaker_id": identity,
                "start_seconds": i,
                "end_seconds": i + 1,
                "source_start_frame": 0,
                "source_end_frame": 16000,
            }
            for i, identity in enumerate(identities[:count])
        ]
        cases.append(
            {
                "path": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "duration_seconds": count,
                "sample_rate": 16000,
                "intervals": intervals,
                "expected_speakers": count,
                "expected_gallery_total": gallery,
            }
        )
    protocol = {
        "schema_version": 1,
        "protocol_id": "voiceup-meeting-first-six-v1",
        "identities": identities,
        "source_manifest_sha256": "a" * 64,
        "cases": cases,
    }
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    return path, protocol


def test_protocol_verifies_all_case_bytes_before_http(runner, tmp_path: Path):
    path, document = fixture_protocol(tmp_path)
    assert len(runner.load_protocol(path)["cases"]) == 4
    (tmp_path / document["cases"][0]["path"]).write_bytes(b"changed")
    with pytest.raises(runner.EvaluationError, match="source_hash_mismatch"):
        runner.load_protocol(path)


@pytest.mark.parametrize(
    "unsafe", ["../outside.wav", "C:/outside.wav", "/outside.wav", "nested/source.wav"]
)
def test_protocol_audio_cannot_escape_fixture_directory(runner, tmp_path: Path, unsafe):
    path, document = fixture_protocol(tmp_path)
    document["cases"][0]["path"] = unsafe
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(runner.EvaluationError):
        runner.load_protocol(path)


def test_duplicate_reference_source_frames_are_not_new_evidence(runner, tmp_path: Path):
    path, document = fixture_protocol(tmp_path)
    document["cases"][0]["intervals"].append(document["cases"][0]["intervals"][0])
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(runner.EvaluationError):
        runner.load_protocol(path)


@pytest.mark.parametrize(
    "origin",
    ["http://example.com", "http://user:secret@127.0.0.1", "http://127.0.0.1?token=secret"],
)
def test_api_never_sends_credentials_to_remote_or_ambiguous_origin(runner, origin):
    with pytest.raises(runner.benchmark.BenchmarkFailure):
        runner.benchmark.Api(origin, "/api/voiceup/v1")


def test_operation_keys_are_stable_and_bound_to_run_and_case(runner):
    assert runner.operation_key("first", "A") == runner.operation_key("first", "A")
    assert runner.operation_key("first", "A") != runner.operation_key("second", "A")
    assert runner.operation_key("first", "A") != runner.operation_key("first", "B")


def test_transcript_outside_source_is_not_a_valid_measurement(runner):
    track = str(uuid4())
    with pytest.raises(runner.EvaluationError, match="invalid_transcript_contract"):
        runner.map_identities(
            [{"speaker_id": "ls-1", "start_seconds": 0, "end_seconds": 1}],
            [transcript(track, 0, 10)],
            {track},
            duration_seconds=1,
        )


@pytest.fixture
def http_fixture(runner, tmp_path):
    path, protocol = fixture_protocol(tmp_path)
    data = {
        "meetings": {},
        "profiles": {},
        "keys": {},
        "calls": [],
        "corrupt_manifest": False,
        "wrong_return": False,
        "short_enrolled": False,
        "super_admin": False,
        "user": str(uuid4()),
        "tenant": str(uuid4()),
        "redirect": False,
        "fail_part_ack_once": False,
        "part_sizes": [],
    }
    cases = dict(zip(runner.CASE_KEYS, protocol["cases"], strict=True))
    data["cases"] = cases

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def send_json(self, payload, status=200):
            content = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def handle_call(self):
            route = urlsplit(self.path).path.removeprefix("/api/voiceup/v1")
            payload = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            data["calls"].append((self.command, route))
            if data["redirect"]:
                self.send_response(302)
                self.send_header("Location", "https://example.com/?secret=private")
                self.end_headers()
                return
            if route == "/auth/login":
                return self.send_json(
                    {
                        "access_token": "private-token",
                        "user": {
                            "public_id": data["user"],
                            "tenant_id": data["tenant"],
                            "is_super_admin": data["super_admin"],
                            "roles": ["ordinary"],
                            "permissions": sorted(runner.REQUIRED_PERMISSIONS),
                        },
                    }
                )
            if (
                self.headers.get("Authorization") != "Bearer private-token"
                or self.headers.get("x-tenant-id") != data["tenant"]
            ):
                return self.send_json({"private": "must never print"}, 401)
            if route == "/speaker-profiles":
                if data.get("gallery_error_after_complete") and any(
                    item["dto"]["status"] == "succeeded" for item in data["meetings"].values()
                ):
                    return self.send_json({"detail": "private response and token"}, 503)
                rows = list(data["profiles"].values())
                return self.send_json(
                    {"items": rows, "total": len(rows), "offset": 0, "limit": 100}
                )
            if route == "/meetings":
                body = json.loads(payload)
                key = self.headers["Idempotency-Key"]
                if key in data["keys"]:
                    return self.send_json(data["meetings"][data["keys"][key]]["dto"])
                case_key = body["title"].split()[-1]
                meeting_id = str(uuid4())
                data["keys"][key] = meeting_id
                item = {
                    "dto": {
                        "public_id": meeting_id,
                        "status": "uploading",
                        "sha256": None,
                        "observed_speakers": 0,
                        "completed_chunks": 0,
                    },
                    "parts": [],
                    "case_key": case_key,
                    "speakers": [],
                    "transcript": [],
                }
                data["meetings"][meeting_id] = item
                return self.send_json(item["dto"], 201)
            pieces = route.strip("/").split("/")
            item = data["meetings"][pieces[1]]
            case_key, case = item["case_key"], cases[item["case_key"]]
            if len(pieces) == 2:
                return self.send_json(item["dto"])
            if pieces[2] == "upload-parts":
                if self.command == "PUT":
                    assert int(pieces[3]) == len(item["parts"])
                    assert self.headers["X-Chunk-SHA256"] == hashlib.sha256(payload).hexdigest()
                    item["parts"].append(
                        {
                            "index": len(item["parts"]),
                            "size_bytes": len(payload),
                            "sha256": hashlib.sha256(payload).hexdigest(),
                        }
                    )
                    data["part_sizes"].append(len(payload))
                    if data["fail_part_ack_once"]:
                        data["fail_part_ack_once"] = False
                        return self.send_json({"detail": "private server response"}, 503)
                parts = [dict(row) for row in item["parts"]]
                if data["corrupt_manifest"] and parts:
                    parts[0]["sha256"] = "0" * 64
                return self.send_json(
                    {
                        "meeting_public_id": pieces[1],
                        "parts": parts,
                        "uploaded_bytes": sum(row["size_bytes"] for row in parts),
                        "next_index": len(parts),
                    }
                )
            if pieces[2] == "complete":
                if item["dto"]["status"] != "succeeded":
                    for index, identity in enumerate(
                        protocol["identities"][: case["expected_speakers"]]
                    ):
                        is_new = case_key == "A" or (index == 5 and case_key == "C")
                        pending = case_key == "D" and index == 5 and not data["short_enrolled"]
                        if is_new or (case_key == "D" and index == 5 and data["short_enrolled"]):
                            data["profiles"][identity] = {
                                "public_id": str(uuid4()),
                                "name": "Initial name",
                            }
                        profile = None if pending else data["profiles"][identity]
                        if data["wrong_return"] and case_key == "B" and index == 0:
                            profile = data["profiles"][protocol["identities"][1]]
                        track_id = str(uuid4())
                        item["speakers"].append(
                            {
                                "public_id": track_id,
                                "ordinal": index,
                                "profile_public_id": (
                                    None if profile is None else profile["public_id"]
                                ),
                                "display_name": None,
                                "profile_name": None if profile is None else profile["name"],
                                "profile_deleted": False,
                                "decision": (
                                    "profile_pending"
                                    if pending
                                    else "enrolled"
                                    if is_new
                                    else "recognized"
                                ),
                                "version": 1,
                                "profile_updated_at": "2026-09-10T00:00:00Z",
                            }
                        )
                        item["transcript"].append(transcript(track_id, index, index + 1, index))
                    item["dto"].update(
                        {
                            "status": "succeeded",
                            "sha256": case["sha256"],
                            "observed_speakers": len(item["speakers"]),
                            "completed_chunks": 1,
                            "duration_seconds": case["duration_seconds"],
                        }
                    )
                    item["dto"].update(data.get("terminal_changes", {}))
                return self.send_json(item["dto"])
            if pieces[2] == "speakers" and self.command == "PATCH":
                body = json.loads(payload)
                row = next(row for row in item["speakers"] if row["public_id"] == pieces[3])
                assert (
                    body["version"] == row["version"]
                    and body["profile_updated_at"] == row["profile_updated_at"]
                )
                row.update(
                    {
                        "profile_name": body["name"],
                        "display_name": body["name"],
                        "version": row["version"] + 1,
                    }
                )
                profile = next(
                    row2
                    for row2 in data["profiles"].values()
                    if row2["public_id"] == row["profile_public_id"]
                )
                profile["name"] = body["name"]
                return self.send_json(row)
            rows = item[pieces[2]]
            return self.send_json(
                {"items": rows, "total": len(rows), "offset": 0, "limit": 100, "provisional": False}
            )

        do_POST = do_GET = do_PUT = do_PATCH = handle_call

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    credentials = tmp_path / "credentials.json"
    credentials.write_text(
        json.dumps(
            {
                "url": f"http://127.0.0.1:{server.server_port}",
                "username": "private-user",
                "password": "private-password",
            }
        )
    )
    data["argv"] = [
        "--protocol",
        str(path),
        "--credentials",
        str(credentials),
        "--output",
        str(tmp_path / "result.json"),
        "--repeat-complete",
    ]
    try:
        yield data
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def invoke(runner, monkeypatch, http_fixture, *extra):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), *http_fixture["argv"], *extra])
    return runner.main()


def test_http_contract_flow_enroll_names_return_short_pending_and_new_six(
    runner, monkeypatch, http_fixture, tmp_path, capsys
):
    assert invoke(runner, monkeypatch, http_fixture) == 0
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["status"] == "passed"
    assert [report["cases"][key]["result"]["gallery_total"] for key in runner.CASE_KEYS] == [
        5,
        5,
        5,
        6,
    ]
    assert len(http_fixture["meetings"]) == 4 and len(http_fixture["profiles"]) == 6
    assert sum(method == "PATCH" for method, _ in http_fixture["calls"]) == 5
    assert all(report["cases"][key]["repeat_complete_verified"] for key in runner.CASE_KEYS)
    output = (
        json.dumps(report) + (tmp_path / "result.state.json").read_text() + str(capsys.readouterr())
    )
    assert all(
        secret not in output
        for secret in ["private-user", "private-password", "private-token", "Private fixture text"]
    )


def test_pause_and_resume_b_verifies_bytes_preserves_ids_and_does_not_create_twice(
    runner, monkeypatch, http_fixture, tmp_path
):
    assert invoke(runner, monkeypatch, http_fixture, "--stop-after-upload-b") == 0
    before = json.loads((tmp_path / "result.state.json").read_text())
    assert before["status"] == "paused_after_b_upload" and len(http_fixture["meetings"]) == 2
    assert invoke(runner, monkeypatch, http_fixture, "--resume") == 0
    after = json.loads((tmp_path / "result.state.json").read_text())
    assert all(
        after["identity_profiles"][key] == value
        for key, value in before["identity_profiles"].items()
    )
    assert before["cases"]["B"]["meeting_public_id"] == after["cases"]["B"]["meeting_public_id"]
    assert len(http_fixture["meetings"]) == 4
    assert sum(method == "PUT" for method, _ in http_fixture["calls"]) == 4


def test_resume_refuses_corrupt_server_part_without_sending_new_audio(
    runner, monkeypatch, http_fixture, tmp_path
):
    assert invoke(runner, monkeypatch, http_fixture, "--stop-after-upload-b") == 0
    http_fixture["corrupt_manifest"] = True
    assert invoke(runner, monkeypatch, http_fixture, "--resume") == 1
    assert len(http_fixture["meetings"]) == 2
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["error_code"] == "resume_upload_hash_mismatch" and report["cases"]["A"]["passed"]


def test_partial_identity_failure_is_not_reported_as_passing_case(
    runner, monkeypatch, http_fixture, tmp_path
):
    http_fixture["wrong_return"] = True
    assert invoke(runner, monkeypatch, http_fixture) == 1
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["error_code"] == "returning_identity_or_name_mismatch"
    assert report["cases"]["A"]["passed"]
    assert report["cases"]["B"]["result"]["mapping_passed"]
    assert not report["cases"]["B"]["result"]["passed"]


def test_resume_rechecks_recorded_memory_and_names(runner, monkeypatch, http_fixture, tmp_path):
    assert invoke(runner, monkeypatch, http_fixture, "--stop-after-upload-b") == 0
    next(iter(http_fixture["profiles"].values()))["name"] = "Changed outside evaluation"
    calls = len(http_fixture["calls"])
    assert invoke(runner, monkeypatch, http_fixture, "--resume") == 1
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["error_code"] == "resume_gallery_identity_or_name_changed"
    assert not any(
        method in {"PUT", "POST", "PATCH"} and route != "/auth/login"
        for method, route in http_fixture["calls"][calls:]
    )


@pytest.mark.parametrize(
    "option,error", [("super_admin", "ordinary_role_required"), ("redirect", "redirect_refused")]
)
def test_http_auth_and_redirect_rejections_preserve_secrets(
    runner, monkeypatch, http_fixture, tmp_path, capsys, option, error
):
    http_fixture[option] = True
    assert invoke(runner, monkeypatch, http_fixture) == 1
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["error_code"] == error
    assert not http_fixture["meetings"]
    assert "private" not in str(capsys.readouterr())


def test_final_report_write_failure_has_no_private_path_traceback(
    runner, monkeypatch, http_fixture, capsys
):
    def fail_write(_path, _value):
        raise OSError("private-user/private-password")

    monkeypatch.setattr(runner.helpers, "atomic_json", fail_write)
    assert invoke(runner, monkeypatch, http_fixture) == 1
    assert "private" not in str(capsys.readouterr())


def test_simultaneous_run_cannot_overwrite_active_report(
    runner, monkeypatch, http_fixture, tmp_path
):
    target = tmp_path / "result.json"
    target.write_text('{"active":true}')
    with runner.helpers.state_lock(tmp_path / "result.state.json"):
        assert invoke(runner, monkeypatch, http_fixture, "--resume") == 1
    assert target.read_text() == '{"active":true}'
    assert not http_fixture["calls"]


def test_lost_upload_ack_resumes_four_mib_parts_without_duplicate_upload(
    runner, monkeypatch, http_fixture, tmp_path
):
    protocol_path = tmp_path / "protocol.json"
    document = json.loads(protocol_path.read_text())
    audio = tmp_path / document["cases"][0]["path"]
    with wave.open(str(audio), "wb") as target:
        target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        target.writeframes(b"\x01\x00" * (160 * 16000))
    document["cases"][0].update({"duration_seconds": 160, "sha256": runner.source_hash(audio)})
    http_fixture["cases"]["A"].update(document["cases"][0])
    protocol_path.write_text(json.dumps(document))
    # The server reads the same frozen source declaration, not model-produced data.
    http_fixture["fail_part_ack_once"] = True
    assert invoke(runner, monkeypatch, http_fixture) == 1
    state = json.loads((tmp_path / "result.state.json").read_text())
    assert len(http_fixture["meetings"]) == 1 and state["cases"]["A"]["meeting_public_id"]
    assert http_fixture["part_sizes"] == [runner.PART_BYTES]
    # Resume validates the acknowledged server prefix before transmitting the remainder.
    http_fixture["corrupt_manifest"] = True
    assert invoke(runner, monkeypatch, http_fixture, "--resume") == 1
    assert http_fixture["part_sizes"] == [runner.PART_BYTES]
    http_fixture["corrupt_manifest"] = False
    assert invoke(runner, monkeypatch, http_fixture, "--resume") == 0
    assert http_fixture["part_sizes"][:2] == [
        runner.PART_BYTES,
        audio.stat().st_size - runner.PART_BYTES,
    ]
    assert len(http_fixture["part_sizes"]) == 5 and len(http_fixture["meetings"]) == 4


def test_short_sixth_must_not_grow_gallery(runner, monkeypatch, http_fixture, tmp_path):
    http_fixture["short_enrolled"] = True
    assert invoke(runner, monkeypatch, http_fixture) == 1
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["error_code"] == "unexpected_gallery_total"
    assert report["cases"]["B"]["passed"] and not report["cases"]["D"]["result"]["passed"]
    assert "C" not in report["cases"]


def test_output_cannot_overwrite_credentials(runner, monkeypatch, http_fixture, tmp_path):
    target = tmp_path / "credentials.json"
    before = target.read_bytes()
    assert invoke(runner, monkeypatch, http_fixture, "--output", str(target)) == 1
    assert target.read_bytes() == before and not http_fixture["calls"]


@pytest.mark.parametrize("change", [{"observed_speakers": 11}, {"sha256": "0" * 64}])
def test_terminal_mismatch_preserves_observed_counts_before_failure(
    runner, monkeypatch, http_fixture, tmp_path, capsys, change
):
    http_fixture["terminal_changes"] = {
        **change,
        "text": "private transcript",
        "embedding": [0.123456789],
        "access_token": "private-token",
        "title": "private-user",
    }
    assert invoke(runner, monkeypatch, http_fixture) == 1
    report = json.loads((tmp_path / "result.json").read_text())
    state = json.loads((tmp_path / "result.state.json").read_text())
    assert (
        report["status"] == "incomplete"
        and report["error_code"] == "source_or_speaker_count_mismatch"
    )
    for artifact in (report, state):
        case = artifact["cases"]["A"]
        assert case["last_observed_status"] == "succeeded"
        assert case["observed"] == {
            "status": "succeeded",
            "duration_seconds": 5.0,
            "observed_speakers": change.get("observed_speakers", 5),
            "completed_chunks": 1,
            "expected_speakers": 5,
            "expected_gallery_total": 5,
            "gallery_total": 5,
            "source_hash_matches": "sha256" not in change,
        }
        assert not case.get("passed") and "B" not in artifact["cases"]
    output = json.dumps(report) + json.dumps(state) + str(capsys.readouterr())
    assert all(
        value not in output
        for value in (
            "private-user",
            "private-password",
            "private-token",
            "private transcript",
            "0.123456789",
        )
    )


def test_gallery_observation_failure_preserves_primary_mismatch(
    runner, monkeypatch, http_fixture, tmp_path
):
    http_fixture["terminal_changes"] = {"observed_speakers": 11}
    http_fixture["gallery_error_after_complete"] = True
    assert invoke(runner, monkeypatch, http_fixture) == 1
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["error_code"] == "source_or_speaker_count_mismatch"
    assert report["cases"]["A"]["observed"]["observed_speakers"] == 11
    assert report["cases"]["A"]["observed"]["gallery_total"] is None
    assert report["cases"]["A"]["observed"]["gallery_observation_error"] == "unavailable"


def test_invalid_observed_metrics_are_not_serialized_as_private_values(
    runner, monkeypatch, http_fixture, tmp_path
):
    http_fixture["terminal_changes"] = {
        "observed_speakers": "private-token",
        "duration_seconds": float("nan"),
        "completed_chunks": {"text": "private transcript"},
        "sha256": "private source",
    }
    assert invoke(runner, monkeypatch, http_fixture) == 1
    report = json.loads((tmp_path / "result.json").read_text())
    observed = report["cases"]["A"]["observed"]
    assert observed["duration_seconds"] is None and observed["observed_speakers"] is None
    assert observed["completed_chunks"] is None and observed["source_hash_matches"] is False
    assert "private" not in (tmp_path / "result.json").read_text()
