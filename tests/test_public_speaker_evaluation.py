"""Public evaluation metrics and a resumable real-contract API orchestration."""

import hashlib
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate-public-speakers.py"


@pytest.fixture
def evaluation():
    spec = importlib.util.spec_from_file_location("public_speaker_evaluation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failed_probes_and_missing_enrollment_stay_in_denominator(evaluation):
    records = [
        {
            "speaker_id": "a",
            "kind": "known",
            "status": "succeeded",
            "decision": "recognized",
            "predicted_speaker_id": "a",
        },
        {
            "speaker_id": "b",
            "kind": "known",
            "status": "failed",
            "error_code": "insufficient_speech",
        },
        {
            "speaker_id": "b",
            "kind": "known",
            "status": "succeeded",
            "decision": "unknown",
            "predicted_speaker_id": None,
        },
        {
            "speaker_id": "u",
            "kind": "unknown",
            "status": "succeeded",
            "decision": "recognized",
            "predicted_speaker_id": "a",
        },
        {
            "speaker_id": "u",
            "kind": "unknown",
            "status": "failed",
            "error_code": "inference_unavailable",
        },
    ]
    result = evaluation.summarize_probes(records, known_planned=4, unknown_planned=3)
    assert result["counts"]["known_completed"] == 3
    assert result["counts"]["known_job_failed"] == 1
    assert result["counts"]["known_not_run"] == 1
    assert result["rates"]["DIR"] == 0.25
    assert result["rates"]["FPIR_observed_lower_bound"] == 1 / 3
    assert result["rates"]["FPIR_worst_case_upper_bound"] == 1.0
    assert result["complete_decisions"] is False


def test_wilson_interval_includes_nonzero_uncertainty_at_zero_errors(evaluation):
    interval = evaluation.wilson_interval(0, 100)
    assert interval["lower"] == 0
    assert 0.03 < interval["upper"] < 0.04
    assert evaluation.wilson_interval(0, 0) is None


def manifest_fixture(tmp_path, *, gallery_size=1, unknown_size=1):
    recordings = []
    gallery = ["a"] + [f"p{index:03d}" for index in range(1, gallery_size)]
    for speaker, roles in [
        *[
            (person, ["enrollment", "known_query", "known_query", "known_query"])
            for person in gallery
        ],
        ("u", ["unknown_query", "new_enrollment", "return_query"]),
        *[(f"u{index:03d}", ["unknown_query"]) for index in range(1, unknown_size)],
    ]:
        for index, role in enumerate(roles):
            identifier = f"{speaker}-{index}"
            payload = b"RIFF" + identifier.encode()
            path = tmp_path / f"{identifier}.wav"
            path.write_bytes(payload)
            recordings.append(
                {
                    "id": identifier,
                    "speaker_id": speaker,
                    "role": role,
                    "source_split": "test-clean",
                    "chapter_id": str(index),
                    "source_utterance_ids": [identifier],
                    "path": path.name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "duration_seconds": 30,
                }
            )
    return {
        "schema_version": 1,
        "dataset_id": "fixture",
        "language": "en",
        "split": "test",
        "gallery_order": gallery,
        "unknown_order": ["u"] + [f"u{index:03d}" for index in range(1, unknown_size)],
        "recordings": recordings,
    }


def test_manifest_preflight_rejects_hash_mismatch_before_api(evaluation, tmp_path):
    manifest = manifest_fixture(tmp_path)
    manifest["recordings"][0]["sha256"] = "0" * 64
    with pytest.raises(evaluation.EvaluationError, match="audio_hash_mismatch"):
        evaluation.validate_manifest(manifest, tmp_path, [1])


def test_new_gallery_accepts_fifty_without_truncating_historical_manifest(evaluation, tmp_path):
    manifest = manifest_fixture(tmp_path, gallery_size=51)
    original = json.dumps(manifest, sort_keys=True)
    evaluation.validate_manifest(manifest, tmp_path, [50])
    assert json.dumps(manifest, sort_keys=True) == original
    assert len(manifest["gallery_order"]) == 51
    assert sum(row["role"] == "unknown_query" for row in manifest["recordings"]) == 1


@pytest.mark.parametrize("size", [51, 100, 200])
def test_new_gallery_accepts_quality_target_and_larger_manifests(evaluation, tmp_path, size):
    manifest = manifest_fixture(tmp_path, gallery_size=size, unknown_size=200)
    original = json.dumps(manifest, sort_keys=True)
    evaluation.validate_manifest(manifest, tmp_path, [size])
    assert json.dumps(manifest, sort_keys=True) == original
    assert len(manifest["unknown_order"]) == 200


def test_manifest_person_budget_is_an_input_resource_bound(evaluation, tmp_path):
    manifest = manifest_fixture(tmp_path, gallery_size=201)
    with pytest.raises(evaluation.EvaluationError, match="invalid_gallery_order"):
        evaluation.validate_manifest(manifest, tmp_path, [201])
    manifest = manifest_fixture(tmp_path, unknown_size=201)
    with pytest.raises(evaluation.EvaluationError, match="invalid_unknown_order"):
        evaluation.validate_manifest(manifest, tmp_path, [1])


@pytest.mark.parametrize(
    "declared,error",
    [
        (None, "invalid_unknown_order"),
        ("u", "invalid_unknown_order"),
        (["u", "u"], "invalid_unknown_order"),
        (["absent"], "unknown_recordings_mismatch"),
        ([], "invalid_unknown_order"),
        (["u"] + [f"extra-{index}" for index in range(200)], "invalid_unknown_order"),
    ],
)
def test_cli_rejects_inconsistent_unknown_declaration_before_http(
    evaluation, tmp_path, api_server, declared, error, capsys
):
    args = provenance_cli_fixture(evaluation, tmp_path, api_server)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text())
    if declared is None:
        manifest.pop("unknown_order")
    else:
        manifest["unknown_order"] = declared
    path.write_text(json.dumps(manifest))
    assert evaluation.main(args) == 1
    assert error in capsys.readouterr().err
    assert not api_server["calls"]
    assert not (tmp_path / "state.json").exists()


def test_recording_resource_budget_remains_fifteen_hundred(evaluation, tmp_path):
    manifest = manifest_fixture(tmp_path)
    manifest["recordings"] = [{}] * 1501
    with pytest.raises(evaluation.EvaluationError, match="invalid_manifest"):
        evaluation.validate_manifest(manifest, tmp_path, [1])


def test_large_nested_gallery_rejects_over_twenty_thousand_operations(evaluation, tmp_path):
    manifest = manifest_fixture(tmp_path, gallery_size=200, unknown_size=200)
    with pytest.raises(evaluation.EvaluationError, match="operation_limit"):
        evaluation.validate_manifest(manifest, tmp_path, list(range(1, 201)))


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda m: m["recordings"][1].update(chapter_id="0"), "source_role_leakage"),
        (
            lambda m: m["recordings"][1].update(source_utterance_ids=["a-0"]),
            "duplicate_source_utterance",
        ),
        (lambda m: m["recordings"][0].update(path="../outside.wav"), "unsafe_audio_path"),
        (lambda m: m.update(gallery_order=["a", "a"]), "invalid_gallery_order"),
        (lambda m: m.update(language="tr"), "invalid_manifest"),
    ],
)
def test_manifest_guards(evaluation, tmp_path, mutation, code):
    manifest = manifest_fixture(tmp_path)
    mutation(manifest)
    with pytest.raises(evaluation.EvaluationError, match=code):
        evaluation.validate_manifest(manifest, tmp_path, [1])


def test_resume_binding_refuses_different_tenant_and_manifest(evaluation):
    binding = {"tenant_id": "a", "manifest_sha256": "h", "gallery_sizes": [1]}
    with pytest.raises(evaluation.EvaluationError, match="resume_binding_mismatch"):
        evaluation.validate_state(
            {
                "schema_version": 1,
                "binding": binding,
                "run_id": "run",
                "operations": {},
                "uploads": {},
                "expected_profiles": [],
            },
            {**binding, "tenant_id": "b"},
        )


def test_stable_keys_bind_run_and_operation(evaluation):
    assert evaluation.operation_key("run", "upload:a") == evaluation.operation_key(
        "run", "upload:a"
    )
    assert evaluation.operation_key("run", "upload:a") != evaluation.operation_key("run", "job:a")
    assert evaluation.operation_key("run", "job:a") != evaluation.operation_key("other", "job:a")


def test_atomic_json_refuses_overwriting_protected_inputs(evaluation, tmp_path):
    source = tmp_path / "manifest.json"
    source.write_text("original")
    with pytest.raises(evaluation.EvaluationError, match="output_would_overwrite_input"):
        evaluation.check_output_paths(source, tmp_path / "state.json", {source})
    assert source.read_text() == "original"


@pytest.fixture
def api_server(evaluation):
    """Real loopback HTTP, independently implementing the public response shape."""
    profiles, jobs, uploads, keys = {}, {}, {}, {}
    state = {
        "profiles": profiles,
        "jobs": jobs,
        "uploads": uploads,
        "keys": keys,
        "calls": [],
        "tenant": str(uuid4()),
        "fail_enrollment": False,
        "fail_known_probe": False,
        "change_policy": False,
        "change_gallery": False,
        "lose_response": False,
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def send_json(self, value, status=200):
            payload = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            assert self.headers["x-tenant-id"] == state["tenant"]
            state["calls"].append(("GET", self.path))
            if self.path.startswith("/api/voiceup/v1/speaker-profiles?"):
                query = parse_qs(urlsplit(self.path).query)
                offset, limit = int(query["offset"][0]), int(query["limit"][0])
                self.send_json(
                    {
                        "items": list(profiles.values())[offset : offset + limit],
                        "total": len(profiles),
                        "offset": offset,
                        "limit": limit,
                    }
                )
            elif self.path.startswith("/api/voiceup/v1/speaker-jobs/"):
                self.send_json(jobs[self.path.rsplit("/", 1)[1]])
            else:
                self.send_json({}, 404)

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            state["calls"].append(("POST", self.path))
            if self.path.endswith("/auth/login"):
                assert json.loads(body) == {
                    "username": "evaluation",
                    "password": "private-password",
                }
                self.send_json(
                    {"access_token": "private-token", "user": {"tenant_id": state["tenant"]}}
                )
                return
            assert self.headers["x-tenant-id"] == state["tenant"]
            assert self.headers["Authorization"] == "Bearer private-token"
            key = (self.path, self.headers["Idempotency-Key"])
            if key in keys:
                self.send_json(keys[key])
                return
            if self.path.endswith("/recordings"):
                payload = body.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0]
                identifier = str(uuid4())
                uploads[identifier] = payload
                response = {
                    "public_id": identifier,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "duration_seconds": 30,
                    "format": "WAV",
                    "created_at": "2026-09-09T00:00:00Z",
                }
                keys[key] = response
                self.send_json(response, 201)
                return
            if not self.path.endswith("/speaker-jobs"):
                self.send_json({}, 404)
                return
            request = json.loads(body)
            if "submission_error" in state:
                self.send_json(state["submission_error"], state.get("submission_status", 409))
                return
            assert set(request) == (
                {"recording_public_id", "purpose", "name"}
                if request["purpose"] == "enroll"
                else {"recording_public_id", "purpose"}
            )
            sample = uploads[request["recording_public_id"]]
            speaker = sample[4:].decode().rsplit("-", 1)[0]
            if (
                request["purpose"] == "enroll"
                and "max_profiles" in state
                and len(profiles) >= state["max_profiles"]
            ):
                self.send_json(
                    {"detail": {"code": "profile_limit", "message": "Capacity full"}}, 409
                )
                return
            failed = (
                request["purpose"] == "enroll" and speaker == "a" and state["fail_enrollment"]
            ) or (
                request["purpose"] == "identify"
                and sample == b"RIFFa-2"
                and state["fail_known_probe"]
            )
            profile = next(
                (item for item in profiles.values() if item["name"].endswith("-" + speaker)), None
            )
            if request["purpose"] == "enroll" and not failed:
                profile = {
                    "public_id": str(uuid4()),
                    "name": request["name"],
                    "sample_count": 1,
                    "model_id": evaluation.MODEL_ID,
                    "model_revision": evaluation.MODEL_REVISION,
                    "created_at": "2026-09-09T00:00:00Z",
                    "updated_at": "2026-09-09T00:00:00Z",
                }
                profiles[profile["public_id"]] = profile
            decision = (
                "enrolled"
                if request["purpose"] == "enroll"
                else "recognized"
                if profile
                else "unknown"
            )
            result = {
                "decision": decision,
                "profile_public_id": profile["public_id"] if profile else None,
                "profile_name": profile["name"] if profile else None,
                "profile_deleted": False,
                "similarity": 0.95 if profile else 0.2,
                "runner_up_similarity": 0.1,
                "speech_seconds": 20,
                "windows_count": 3,
                "model_id": evaluation.MODEL_ID,
                "model_revision": evaluation.MODEL_REVISION,
                "device": "cuda:0",
                "reason": "matched",
                "policy": dict(state.get("policy_override", evaluation.POLICY)),
            }
            if "preprocessing_version" in state:
                result["preprocessing_version"] = state["preprocessing_version"]
            if request["purpose"] == "identify" and "identify_preprocessing_version" in state:
                result["preprocessing_version"] = state["identify_preprocessing_version"]
            if state["change_policy"]:
                result["policy"]["match_threshold"] = 0.5
            identifier = str(uuid4())
            response = {
                "public_id": identifier,
                "purpose": request["purpose"],
                "status": "failed" if failed else "succeeded",
                "recording_public_id": request["recording_public_id"],
                "created_at": "2026-09-09T00:00:00Z",
                "started_at": "2026-09-09T00:00:01Z",
                "finished_at": "2026-09-09T00:00:02Z",
                "attempt_count": 1,
                "result": None if failed else result,
                "error": {"code": "insufficient_speech", "message": "Insufficient speech"}
                if failed
                else None,
            }
            jobs[identifier] = response
            keys[key] = response
            if state["change_gallery"] and request["purpose"] == "identify":
                profiles[next(iter(profiles))]["sample_count"] += 1
            self.send_json(response, 202)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state["origin"] = f"http://127.0.0.1:{server.server_port}"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def runner_fixture(evaluation, tmp_path, server, *, existing=None, gallery_size=1):
    manifest = manifest_fixture(tmp_path, gallery_size=gallery_size)
    binding = {
        "tenant_id": server["tenant"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest(),
        "gallery_sizes": [gallery_size],
        "policy": dict(server.get("policy_override", evaluation.POLICY)),
        "model_revision": evaluation.MODEL_REVISION,
    }
    state = existing or {
        "schema_version": 1,
        "binding": binding,
        "run_id": "12345678-fixture-run",
        "started_at": "2026-09-09T00:00:00Z",
        "status": "incomplete",
        "operations": {},
        "uploads": {},
        "expected_profiles": [],
    }
    credentials = {
        "url": server["origin"],
        "username": "evaluation",
        "password": "private-password",
        "tenant_id": server["tenant"],
    }
    return evaluation.Evaluator(
        manifest=manifest,
        audio_root=tmp_path,
        credentials=credentials,
        state=state,
        state_path=tmp_path / "state.json",
        output=tmp_path / "output.json",
        job_timeout=2,
        poll_seconds=0.001,
    )


def test_public_http_enrollment_query_return_and_completed_resume(evaluation, tmp_path, api_server):
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.execute()
    report = json.loads((tmp_path / "output.json").read_text())
    assert report["status"] == "complete"
    assert report["stages"][0]["rates"]["DIR"] == 1
    assert report["stages"][0]["counts"]["unknown_unknown"] == 1
    assert report["return_phase"][-1]["predicted_speaker_id"] == "u"
    assert report["return_phase_planned"] == {"enrollments": 1, "queries": 1}
    assert len(api_server["profiles"]) == 2
    assert len(api_server["jobs"]) == 7
    assert all(item["sample_count"] == 1 for item in api_server["profiles"].values())
    assert all(
        item["profiles_unchanged"] for item in report["operations"] if item["purpose"] == "identify"
    )
    assert "private-password" not in (tmp_path / "state.json").read_text()
    assert "private-token" not in (tmp_path / "output.json").read_text()
    calls = len(
        [call for call in api_server["calls"] if call == ("POST", "/api/voiceup/v1/speaker-jobs")]
    )
    resumed = runner_fixture(
        evaluation, tmp_path, api_server, existing=json.loads((tmp_path / "state.json").read_text())
    )
    resumed.execute()
    assert (
        len(
            [
                call
                for call in api_server["calls"]
                if call == ("POST", "/api/voiceup/v1/speaker-jobs")
            ]
        )
        == calls
    )
    assert len(api_server["profiles"]) == 2


def load_reporter_module(filename):
    spec = importlib.util.spec_from_file_location(filename, SCRIPT.with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_fifty_gallery_capacity_return_preserves_metrics_and_resume(
    evaluation, tmp_path, api_server
):
    api_server["max_profiles"] = 50
    runner = runner_fixture(evaluation, tmp_path, api_server, gallery_size=50)
    runner.execute()
    report = json.loads(runner.output.read_text())
    rejected, returned = report["return_phase"]
    assert report["status"] == "complete" and report["error_code"] is None
    assert rejected["status"] == "failed" and rejected["error_code"] == "profile_limit"
    assert rejected["result"] is None and rejected.get("job_public_id") is None
    assert rejected["attempt_count"] == 0 and rejected["timing"] is None
    assert rejected["finished_at"] and rejected["profiles_unchanged"] is True
    assert returned["status"] == "succeeded" and returned["decision"] == "unknown"
    assert returned["predicted_speaker_id"] is None
    assert len(api_server["profiles"]) == len(runner.state["expected_profiles"]) == 50
    assert len(api_server["jobs"]) == 202
    assert len(runner.profile_map()) == 50 and "u" not in runner.profile_map().values()
    stage = report["stages"][0]
    assert stage["gallery_size_enrolled"] == 50 and stage["enrollment_failed"] == 0
    assert stage["counts"]["known_planned"] == stage["counts"]["known_correct"] == 150
    assert stage["counts"]["unknown_planned"] == stage["counts"]["unknown_unknown"] == 1

    metrics = load_reporter_module("speaker_metrics.py").summarize_metrics(report, runner.manifest)
    assert metrics["source_run_complete"] is True and metrics["status"] == "complete"
    assert metrics["stages"][0]["metrics_complete"] is True
    assert metrics["stages"][0]["voiceup_score"] == 100
    assert metrics["return_phase"]["enrollment_failed"] == 1
    assert metrics["return_phase"]["enrollment_quality_failed"] == 0
    assert metrics["return_phase"]["enrollment_other_or_unclassified_failed"] == 1
    assert metrics["return_phase"]["error_counts"]["enrollment"] == {"profile_limit": 1}
    assert metrics["return_phase"]["correct"] == 0 and metrics["return_phase"]["unknown"] == 1
    legacy = load_reporter_module("report-public-speakers.py").summarize(report)
    assert legacy["status"] == "complete" and legacy["stages"][0]["rates"]["DIR"] == 1
    assert legacy["return_phase"]["enrollment_failed"] == 1
    assert legacy["return_phase"]["correct"] == 0

    posts = api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs"))
    assert posts == 203
    resumed = runner_fixture(
        evaluation,
        tmp_path,
        api_server,
        gallery_size=50,
        existing=json.loads(runner.state_path.read_text()),
    )
    resumed.execute()
    assert api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs")) == posts
    assert resumed.report()["return_phase"][0] == rejected
    assert len(api_server["profiles"]) == 50 and len(api_server["jobs"]) == 202


def test_capacity_rejection_is_persisted_before_resuming_return_query(
    evaluation, tmp_path, api_server, monkeypatch
):
    api_server["max_profiles"] = 1
    runner = runner_fixture(evaluation, tmp_path, api_server)
    original = runner.prepare

    def stop_before_return(row, purpose, stage):
        if row["role"] == "return_query":
            raise evaluation.EvaluationError("fixture_interruption")
        return original(row, purpose, stage)

    monkeypatch.setattr(runner, "prepare", stop_before_return)
    with pytest.raises(evaluation.EvaluationError, match="fixture_interruption"):
        runner.execute()
    state = json.loads(runner.state_path.read_text())
    rejection = state["operations"]["return:enroll:u-1"]
    assert rejection["status"] == "failed" and rejection["error_code"] == "profile_limit"
    assert rejection.get("job_public_id") is None and len(state["expected_profiles"]) == 1
    posts = api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs"))
    assert posts == 6
    resumed = runner_fixture(evaluation, tmp_path, api_server, existing=state)
    resumed.execute()
    assert api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs")) == posts + 1
    assert resumed.report()["return_phase"][0] == rejection
    assert resumed.report()["status"] == "complete" and len(api_server["profiles"]) == 1


def test_cli_full_fifty_gallery_records_capacity_and_preserves_complete_scores(
    evaluation, tmp_path, api_server
):
    api_server["max_profiles"] = 50
    runner = runner_fixture(evaluation, tmp_path, api_server, gallery_size=50)
    manifest_path, credentials_path = tmp_path / "manifest.json", tmp_path / "credentials.json"
    manifest_path.write_text(json.dumps(runner.manifest))
    credentials_path.write_text(json.dumps(runner.credentials))
    args = [
        "--manifest",
        str(manifest_path),
        "--audio-root",
        str(tmp_path),
        "--credentials",
        str(credentials_path),
        "--output",
        str(runner.output),
        "--state",
        str(runner.state_path),
        "--gallery-sizes",
        "50",
    ]
    assert evaluation.main(args) == 0
    report = json.loads(runner.output.read_text())
    rejection = report["return_phase"][0]
    assert rejection["status"] == "failed" and rejection["error_code"] == "profile_limit"
    assert rejection.get("job_public_id") is None and rejection["result"] is None
    metrics = load_reporter_module("speaker_metrics.py").summarize_metrics(report, runner.manifest)
    assert metrics["source_run_complete"] is True and metrics["status"] == "complete"
    assert metrics["stages"][0]["voiceup_score"] == 100
    assert metrics["return_phase"]["enrollment_failed"] == 1
    assert metrics["return_phase"]["correct"] == 0 and metrics["return_phase"]["unknown"] == 1
    calls = api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs"))
    assert calls == 203 and len(api_server["jobs"]) == 202 and len(api_server["profiles"]) == 50
    assert evaluation.main(args) == 0
    assert api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs")) == calls
    assert len(api_server["jobs"]) == 202 and len(api_server["profiles"]) == 50


def test_cli_gallery_above_fifty_completes_without_product_quota(evaluation, tmp_path, api_server):
    args = provenance_cli_fixture(evaluation, tmp_path, api_server, gallery_size=51)
    assert evaluation.main(args) == 0
    report = json.loads((tmp_path / "output.json").read_text())
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    metrics = load_reporter_module("speaker_metrics.py").summarize_metrics(report, manifest)
    assert metrics["source_run_complete"] is True and metrics["status"] == "complete"
    assert metrics["stages"][0]["gallery_size_enrolled"] == 51
    assert metrics["stages"][0]["counts"]["known_correct"] == 153
    assert metrics["stages"][0]["voiceup_score"] == 100
    assert metrics["return_phase"]["enrollment_succeeded"] == 1
    assert metrics["return_phase"]["correct"] == 1
    assert len(api_server["profiles"]) == 52 and len(api_server["jobs"]) == 207
    submissions = api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs"))
    assert evaluation.main(args) == 0
    assert api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs")) == submissions


def test_planned_two_hundred_gallery_enrolls_returner_as_profile_201(
    evaluation, tmp_path, api_server
):
    runner = runner_fixture(evaluation, tmp_path, api_server, gallery_size=200)
    for person in runner.manifest["gallery_order"]:
        identifier = str(uuid4())
        api_server["profiles"][identifier] = {
            "public_id": identifier,
            "name": "existing-" + person,
            "sample_count": 1,
            "model_id": evaluation.MODEL_ID,
            "model_revision": evaluation.MODEL_REVISION,
            "created_at": "2026-09-10T00:00:00Z",
            "updated_at": "2026-09-10T00:00:00Z",
        }
    runner.state["expected_profiles"] = sorted(
        api_server["profiles"].values(), key=lambda row: row["public_id"]
    )
    runner.login()
    for role, purpose in (("new_enrollment", "enroll"), ("return_query", "identify")):
        row = next(row for row in runner.rows.values() if row["role"] == role)
        operation = runner.finish(*runner.prepare(row, purpose, "return"))
        assert operation["status"] == "succeeded"
    assert operation["predicted_speaker_id"] == "u"
    assert len(api_server["profiles"]) == len(runner.state["expected_profiles"]) == 201
    assert len(api_server["jobs"]) == 2
    assert ("GET", "/api/voiceup/v1/speaker-profiles?offset=200&limit=100") in api_server["calls"]
    runner.assert_gallery()


@pytest.mark.parametrize(
    "payload",
    [
        {"detail": {"code": "idempotency_conflict", "message": "PRIVATE-BODY"}},
        {"detail": {"code": "profile_limit_private", "message": "PRIVATE-BODY"}},
        {"detail": "profile_limit"},
        {"detail": [{"code": "profile_limit"}]},
        {"detail": {"code": ["profile_limit"]}},
        {"code": "profile_limit"},
        b'{"detail":{"code":"profile_limit"},"detail":{"code":"profile_limit"}}',
        b'{"detail":{"code":"profile_limit"},"extra":NaN}',
        b'{"detail":{"code":"profile_limit"}',
        {"detail": {"code": "profile_limit", "message": "x" * 20000}},
    ],
)
def test_noncapacity_or_malformed_conflict_stays_fail_closed(
    evaluation, tmp_path, api_server, payload
):
    api_server["submission_error"] = payload
    runner = runner_fixture(evaluation, tmp_path, api_server)
    with pytest.raises(evaluation.EvaluationError, match="^http_409$"):
        runner.execute()
    assert api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs")) == 1
    operation = next(iter(runner.state["operations"].values()))
    assert operation["status"] == "pending" and "error_code" not in operation
    assert not api_server["jobs"] and not api_server["profiles"]
    assert "PRIVATE-BODY" not in runner.state_path.read_text()


@pytest.mark.parametrize(
    "purpose,extra,status",
    [
        ("identify", {}, 409),
        ("enroll", {"profile_public_id": "existing-profile"}, 409),
        ("enroll", {}, 400),
    ],
)
def test_profile_limit_is_not_accepted_for_append_identify_or_other_status(
    evaluation, tmp_path, api_server, purpose, extra, status
):
    api_server.update(
        submission_error={"detail": {"code": "profile_limit"}}, submission_status=status
    )
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.login()
    with pytest.raises(evaluation.EvaluationError, match=f"^http_{status}$"):
        runner.post(
            "/speaker-jobs", {"recording_public_id": "upload", "purpose": purpose, **extra}, "key"
        )
    assert api_server["calls"].count(("POST", "/api/voiceup/v1/speaker-jobs")) == 1
    assert not api_server["jobs"] and not api_server["profiles"]


def test_failed_enrollment_does_not_drop_known_probes(evaluation, tmp_path, api_server):
    api_server["fail_enrollment"] = True
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.execute()
    stage = runner.report()["stages"][0]
    assert stage["gallery_size_planned"] == 1
    assert stage["gallery_size_enrolled"] == 0
    assert stage["enrollment_failed"] == 1
    assert stage["counts"]["known_planned"] == 3
    assert stage["counts"]["known_completed"] == 3
    assert stage["rates"]["DIR"] == 0


def test_failed_quality_job_is_retained_in_live_metric_denominator(
    evaluation, tmp_path, api_server
):
    api_server["fail_known_probe"] = True
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.execute()
    stage = runner.report()["stages"][0]
    assert stage["counts"]["known_job_failed"] == 1
    assert stage["rates"]["DIR"] == 2 / 3
    assert stage["error_counts"] == {"insufficient_speech": 1}


def test_lost_job_response_replays_key_without_duplicate_profile(
    evaluation, tmp_path, api_server, monkeypatch
):
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.login()
    original = runner.post

    def lost_response(path, body, key):
        original(path, body, key)
        raise evaluation.EvaluationError("http_transport_failure")

    monkeypatch.setattr(runner, "post", lost_response)
    with pytest.raises(evaluation.EvaluationError, match="http_transport_failure"):
        runner.prepare(runner.manifest["recordings"][0], "enroll", "enrollment")
    assert len(api_server["profiles"]) == 1
    resumed = runner_fixture(
        evaluation, tmp_path, api_server, existing=json.loads((tmp_path / "state.json").read_text())
    )
    resumed.execute()
    assert len(api_server["profiles"]) == 2
    assert len(api_server["jobs"]) == 7
    assert resumed.report()["stages"][0]["rates"]["DIR"] == 1


@pytest.mark.parametrize(
    "flag,code",
    [
        ("change_policy", "frozen_inference_contract_changed"),
        ("change_gallery", "evaluation_gallery_changed"),
    ],
)
def test_frozen_contract_and_identify_mutation_are_detected(
    evaluation, tmp_path, api_server, flag, code
):
    api_server[flag] = True
    runner = runner_fixture(evaluation, tmp_path, api_server)
    with pytest.raises(evaluation.EvaluationError, match=code):
        runner.execute()
    assert runner.state["status"] != "complete"


def test_nonempty_fresh_gallery_is_rejected_before_upload(evaluation, tmp_path, api_server):
    api_server["profiles"]["foreign"] = {"public_id": "foreign", "name": "existing-person"}
    runner = runner_fixture(evaluation, tmp_path, api_server)
    with pytest.raises(evaluation.EvaluationError, match="evaluation_gallery_changed"):
        runner.execute()
    assert not api_server["uploads"]
    assert not api_server["jobs"]


def test_state_lock_prevents_two_runners_and_releases_after_error(evaluation, tmp_path):
    path = tmp_path / "state.json"
    with pytest.raises(RuntimeError), evaluation.state_lock(path):
        with (
            pytest.raises(evaluation.EvaluationError, match="evaluation_already_running"),
            evaluation.state_lock(path),
        ):
            pytest.fail("lock must not be acquired twice")
        raise RuntimeError("test interruption")
    with evaluation.state_lock(path):
        pass


def test_poll_timeout_leaves_resumable_pending_operation(
    evaluation, tmp_path, api_server, monkeypatch
):
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.login()
    identifier, response = runner.prepare(runner.manifest["recordings"][0], "enroll", "enrollment")
    ticks = iter([0, 3])
    monkeypatch.setattr(evaluation.time, "monotonic", lambda: next(ticks))
    with pytest.raises(evaluation.EvaluationError, match="job_poll_deadline_exceeded"):
        runner.finish(identifier, {**response, "status": "running"})
    assert runner.state["operations"][identifier]["status"] == "pending"
    assert runner.state["expected_profiles"] == []
    monkeypatch.undo()
    resumed = runner_fixture(
        evaluation, tmp_path, api_server, existing=json.loads((tmp_path / "state.json").read_text())
    )
    resumed.execute()
    assert len(api_server["profiles"]) == 2


def test_invalid_timestamps_do_not_partially_commit_resume_gallery(
    evaluation, tmp_path, api_server
):
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.login()
    identifier, response = runner.prepare(runner.manifest["recordings"][0], "enroll", "enrollment")
    with pytest.raises(evaluation.EvaluationError, match="invalid_server_timestamps"):
        runner.finish(identifier, {**response, "finished_at": "2026-09-08T00:00:00Z"})
    assert runner.state["expected_profiles"] == []
    assert runner.state["operations"][identifier]["status"] == "pending"
    runner.finish(identifier, response)
    assert len(runner.state["expected_profiles"]) == 1


def test_expired_token_reauthenticates_once_and_preserves_request(
    evaluation, tmp_path, api_server, monkeypatch
):
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.login()
    original = runner.api.request
    calls = []

    def expiring(method, path, *, payload=None, headers=None):
        calls.append((method, path, payload, headers))
        if len(calls) == 1:
            raise evaluation.benchmark.BenchmarkFailure("http_401")
        return original(method, path, payload=payload, headers=headers)

    monkeypatch.setattr(runner.api, "request", expiring)
    assert runner.profiles() == []
    assert calls[0] == calls[-1]
    assert sum(path == "/auth/login" for _, path, _, _ in calls) == 1


def test_returning_wrong_tenant_never_uploads(evaluation, tmp_path, api_server):
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.credentials["tenant_id"] = str(uuid4())
    with pytest.raises(evaluation.EvaluationError, match="authenticated_tenant_mismatch"):
        runner.execute()
    assert not api_server["uploads"]


def test_main_rejects_bad_data_before_network_or_state(evaluation, tmp_path, monkeypatch):
    manifest = manifest_fixture(tmp_path)
    manifest["recordings"][0]["sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))

    def unavailable_api(*_args, **_kwargs):
        pytest.fail("preflight must precede transport construction")

    monkeypatch.setattr(evaluation.benchmark, "Api", unavailable_api)
    result = evaluation.main(
        [
            "--manifest",
            str(path),
            "--audio-root",
            str(tmp_path),
            "--credentials",
            str(tmp_path / "nonexistent-credentials.json"),
            "--output",
            str(tmp_path / "output.json"),
            "--state",
            str(tmp_path / "state.json"),
            "--gallery-sizes",
            "1",
        ]
    )
    assert result == 1
    assert not (tmp_path / "state.json").exists()


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"match_threshold": 0.6, "new_threshold": 0.45, "margin": True},
        {"match_threshold": "0.6", "new_threshold": 0.45, "margin": 0.1},
        {"match_threshold": float("nan"), "new_threshold": 0.45, "margin": 0.1},
        {"match_threshold": 0.6, "new_threshold": float("inf"), "margin": 0.1},
        {"match_threshold": 0.6, "new_threshold": 0.45, "margin": -0.1},
        {"match_threshold": 0.6, "new_threshold": 0.45, "margin": 2.1},
        {"match_threshold": 1.1, "new_threshold": 0.45, "margin": 0.1},
        {"match_threshold": 0.6, "new_threshold": -1.1, "margin": 0.1},
        {"match_threshold": 0.45, "new_threshold": 0.45, "margin": 0.1},
        {"match_threshold": 0.4, "new_threshold": 0.45, "margin": 0.1},
        {"match_threshold": 0.6, "new_threshold": 0.45, "margin": 0.1, "ignored": 1},
        {"match_threshold": 10**1000, "new_threshold": 0.45, "margin": 0.1},
    ],
)
def test_invalid_frozen_policies_fail_closed(evaluation, value):
    with pytest.raises(evaluation.EvaluationError, match="invalid_frozen_policy"):
        evaluation.validate_policy(value)


def test_different_frozen_policy_uses_binding_without_altering_defaults(
    evaluation, tmp_path, api_server
):
    historical = dict(evaluation.POLICY)
    api_server["policy_override"] = {"match_threshold": 0.6, "new_threshold": 0.45, "margin": 0.1}
    runner = runner_fixture(evaluation, tmp_path, api_server)
    runner.execute()
    assert runner.report()["frozen_policy"] == api_server["policy_override"]
    assert runner.state["binding"]["policy"] == api_server["policy_override"]
    assert evaluation.POLICY == historical
    altered = {**runner.state["binding"], "policy": historical}
    with pytest.raises(evaluation.EvaluationError, match="resume_binding_mismatch"):
        evaluation.validate_state(runner.state, altered)


def test_api_cannot_silently_change_selected_policy(evaluation, tmp_path, api_server):
    api_server["policy_override"] = {"match_threshold": 0.6, "new_threshold": 0.45, "margin": 0.1}
    runner = runner_fixture(evaluation, tmp_path, api_server)
    api_server["policy_override"]["match_threshold"] = 0.55
    with pytest.raises(evaluation.EvaluationError, match="frozen_inference_contract_changed"):
        runner.execute()


def test_invalid_policy_precedes_all_network_and_input_reads(evaluation, tmp_path, monkeypatch):
    path = tmp_path / "policy.json"
    path.write_text('{"match_threshold":true,"new_threshold":0.45,"margin":0.1}')

    def forbidden_api(*_args, **_kwargs):
        pytest.fail("invalid policy must never reach transport construction")

    monkeypatch.setattr(evaluation.benchmark, "Api", forbidden_api)
    assert (
        evaluation.main(
            [
                "--manifest",
                str(tmp_path / "missing-manifest.json"),
                "--audio-root",
                str(tmp_path),
                "--credentials",
                str(tmp_path / "missing-credentials.json"),
                "--output",
                str(tmp_path / "output.json"),
                "--state",
                str(tmp_path / "state.json"),
                "--policy",
                str(path),
            ]
        )
        == 1
    )
    assert not (tmp_path / "state.json").exists()


def test_policy_file_is_protected_from_output_overwrite(evaluation, tmp_path, api_server):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(manifest_fixture(tmp_path)))
    policy = tmp_path / "policy.json"
    original = json.dumps(evaluation.POLICY)
    policy.write_text(original)
    credentials = tmp_path / "credentials.json"
    credentials.write_text(
        json.dumps(
            {
                "url": api_server["origin"],
                "username": "evaluation",
                "password": "private-password",
                "tenant_id": api_server["tenant"],
            }
        )
    )
    assert (
        evaluation.main(
            [
                "--manifest",
                str(manifest),
                "--audio-root",
                str(tmp_path),
                "--credentials",
                str(credentials),
                "--output",
                str(policy),
                "--state",
                str(tmp_path / "state.json"),
                "--policy",
                str(policy),
                "--gallery-sizes",
                "1",
            ]
        )
        == 1
    )
    assert policy.read_text() == original
    assert api_server["calls"] == []


def provenance_cli_fixture(evaluation, tmp_path, api_server, *, gallery_size=1):
    runner = runner_fixture(evaluation, tmp_path, api_server, gallery_size=gallery_size)
    manifest, credentials = tmp_path / "manifest.json", tmp_path / "credentials.json"
    manifest.write_text(json.dumps(runner.manifest), encoding="utf-8")
    credentials.write_text(json.dumps(runner.credentials), encoding="utf-8")
    return [
        "--manifest",
        str(manifest),
        "--audio-root",
        str(tmp_path),
        "--credentials",
        str(credentials),
        "--output",
        str(tmp_path / "output.json"),
        "--state",
        str(tmp_path / "state.json"),
        "--gallery-sizes",
        str(gallery_size),
    ]


@pytest.mark.parametrize("version", ["vad-windows-v1", "vad-packed-fallback-v1"])
def test_required_preprocessing_provenance_is_bound_and_completed_resume_is_stable(
    evaluation, tmp_path, api_server, version
):
    api_server["preprocessing_version"] = version
    args = provenance_cli_fixture(evaluation, tmp_path, api_server) + [
        "--require-preprocessing-provenance"
    ]
    assert evaluation.main(args) == 0
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["binding"]["required_preprocessing_versions"] == [
        "vad-windows-v1",
        "vad-packed-fallback-v1",
    ]
    assert all(
        item["result"]["preprocessing_version"] == version for item in state["operations"].values()
    )
    job_count = len(api_server["jobs"])
    assert evaluation.main(args) == 0
    assert len(api_server["jobs"]) == job_count


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"preprocessing_version": None},
        {"preprocessing_version": "private-untrusted-value"},
        {"preprocessing_version": True},
        {"preprocessing_version": []},
        {"preprocessing_version": {"private": "value"}},
    ],
)
def test_required_preprocessing_provenance_rejects_missing_and_invalid_http_results(
    evaluation, tmp_path, api_server, metadata, capsys
):
    api_server.update(metadata)
    args = provenance_cli_fixture(evaluation, tmp_path, api_server) + [
        "--require-preprocessing-provenance"
    ]
    assert evaluation.main(args) == 1
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["status"] == "incomplete"
    assert state["error_code"] == "frozen_inference_contract_changed"
    assert state["expected_profiles"] == []
    assert all(item["status"] == "pending" for item in state["operations"].values())
    assert "private-untrusted-value" not in capsys.readouterr().err


def test_required_preprocessing_does_not_require_metadata_from_failed_jobs(
    evaluation, tmp_path, api_server
):
    api_server.update(fail_enrollment=True, preprocessing_version="vad-windows-v1")
    args = provenance_cli_fixture(evaluation, tmp_path, api_server) + [
        "--require-preprocessing-provenance"
    ]
    assert evaluation.main(args) == 0
    operations = json.loads((tmp_path / "state.json").read_text())["operations"].values()
    assert any(item["status"] == "failed" and item["result"] is None for item in operations)


@pytest.mark.parametrize("version", [None, "unsupported-identify-version"])
def test_required_preprocessing_validates_queries_after_valid_enrollment(
    evaluation, tmp_path, api_server, version
):
    api_server.update(
        preprocessing_version="vad-windows-v1", identify_preprocessing_version=version
    )
    args = provenance_cli_fixture(evaluation, tmp_path, api_server) + [
        "--require-preprocessing-provenance"
    ]
    assert evaluation.main(args) == 1
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["error_code"] == "frozen_inference_contract_changed"
    successes = [item for item in state["operations"].values() if item["status"] == "succeeded"]
    assert len(successes) == 1 and successes[0]["purpose"] == "enroll"
    assert len(state["expected_profiles"]) == 1


def test_omitted_provenance_flag_preserves_exact_historical_binding(
    evaluation, tmp_path, api_server
):
    args = provenance_cli_fixture(evaluation, tmp_path, api_server)
    assert evaluation.main(args) == 0
    state = json.loads((tmp_path / "state.json").read_text())
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert state["binding"] == {
        "protocol": "public-speaker-api-v1",
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest(),
        "tenant_id": api_server["tenant"],
        "origin": api_server["origin"],
        "gallery_sizes": [1],
        "policy": evaluation.POLICY,
        "model_revision": evaluation.MODEL_REVISION,
    }
    assert evaluation.main(args) == 0


@pytest.mark.parametrize("required_initially", [False, True])
def test_provenance_requirement_cannot_change_on_resume(
    evaluation, tmp_path, api_server, required_initially, capsys
):
    api_server["preprocessing_version"] = "vad-windows-v1"
    args = provenance_cli_fixture(evaluation, tmp_path, api_server)
    flag = ["--require-preprocessing-provenance"]
    assert evaluation.main(args + (flag if required_initially else [])) == 0
    original = (tmp_path / "state.json").read_bytes()
    calls = len(api_server["calls"])
    assert evaluation.main(args + ([] if required_initially else flag)) == 1
    assert "resume_binding_mismatch" in capsys.readouterr().err
    assert (tmp_path / "state.json").read_bytes() == original
    assert len(api_server["calls"]) == calls


@pytest.mark.parametrize(
    "mutation,error",
    [("binding", "resume_binding_mismatch"), ("result", "frozen_inference_contract_changed")],
)
def test_required_provenance_resume_revalidates_bound_versions_and_retained_successes(
    evaluation, tmp_path, api_server, mutation, error, capsys
):
    api_server["preprocessing_version"] = "vad-windows-v1"
    args = provenance_cli_fixture(evaluation, tmp_path, api_server) + [
        "--require-preprocessing-provenance"
    ]
    assert evaluation.main(args) == 0
    path = tmp_path / "state.json"
    state = json.loads(path.read_text())
    if mutation == "binding":
        state["binding"]["required_preprocessing_versions"] = ["unreviewed-version"]
    else:
        next(iter(state["operations"].values()))["result"].pop("preprocessing_version")
    path.write_text(json.dumps(state))
    original, calls = path.read_bytes(), len(api_server["calls"])
    assert evaluation.main(args) == 1
    assert error in capsys.readouterr().err
    assert path.read_bytes() == original and len(api_server["calls"]) == calls
