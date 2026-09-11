"""Prepared-host startup uses real files and real Compose normalization with safe fixtures."""

import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import create_autospec

import pytest

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "sha256:" + "1" * 64
KEY = "fixture-only-private-inference-key-1234567890"
READY = {
    "ready": True,
    "model_id": "speechbrain/spkrec-ecapa-voxceleb",
    "model_revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
    "dimensions": 192,
    "device": "cuda:0",
}
MODEL_FILES = (
    "ecapa/classifier.ckpt",
    "ecapa/embedding_model.ckpt",
    "ecapa/hyperparams.yaml",
    "ecapa/label_encoder.txt",
    "ecapa/mean_var_norm_emb.ckpt",
    "silero/silero_vad.jit",
)


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location(
        "ensure_spark_runtime", ROOT / "scripts/ensure-spark-runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / "voiceup-runtime"
    root.mkdir()
    for name in ("compose.spark.yml", "nginx.spark.conf"):
        shutil.copyfile(ROOT / "app/inference" / name, root / name)
    (root / ".env.spark").write_text(
        f"SPARK_INFERENCE_IMAGE={IMAGE}\nINFERENCE_INTERNAL_KEY='{KEY}'\n", encoding="utf-8"
    )
    (root / ".env.spark").chmod(0o600)
    models = root / "models/speaker-pilot"
    for relative in MODEL_FILES:
        target = models / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fixture; no real model or credential")
    (models / "manifest.json").write_text(
        json.dumps(
            {
                **{key: READY[key] for key in ("model_id", "model_revision", "dimensions")},
                "schema_version": 1,
                "silero_version": "6.2.1",
                "files": {relative: "a" * 64 for relative in MODEL_FILES},
            }
        ),
        encoding="utf-8",
    )
    # The fixture shape comes from Compose itself, not a hand-built consumer mock.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COMPOSE_", "SPARK_", "INFERENCE_"))
    }
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            "voiceup-spark",
            "--env-file",
            str(root / ".env.spark"),
            "-f",
            str(root / "compose.spark.yml"),
            "config",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
        env=environment,
    )
    assert result.returncode == 0, "Fixture Compose config failed; output withheld"
    return {"root": root, "document": json.loads(result.stdout)}


@pytest.fixture
def runtime(helper, prepared, monkeypatch):
    state = {**prepared, "calls": [], "clock": 0.0, "ready": READY, "requests": []}
    monkeypatch.setattr(helper.platform, "system", lambda: "Linux")
    monkeypatch.setattr(helper.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(helper.os, "geteuid", lambda: 1000, raising=False)
    # Windows cannot represent POSIX 0600; contents, ancestry and file types remain real.
    if os.name == "nt":
        monkeypatch.setattr(helper, "private_mode", lambda path: 0o600)
    monkeypatch.setattr(helper.time, "monotonic", lambda: state["clock"])

    def sleep(seconds):
        state["clock"] += seconds

    monkeypatch.setattr(helper.time, "sleep", sleep)

    def run(argv, *, cwd, stdin, capture_output, text, check, timeout, env):
        assert cwd == state["root"]
        assert stdin == subprocess.DEVNULL and capture_output and text and not check
        assert env == {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": str(Path.home()),
            "LC_ALL": "C",
        }
        assert argv[:3] == ["docker", "--host", "unix:///var/run/docker.sock"]
        assert KEY not in " ".join(argv)
        state["calls"].append(argv)
        if argv[3:] == ["info", "--format", "{{json .}}"]:
            assert timeout == 15
            output = json.dumps(state.get("daemon", {"OSType": "linux", "Architecture": "aarch64"}))
        else:
            assert argv[3:10] == [
                "compose",
                "--project-name",
                "voiceup-spark",
                "--env-file",
                str(state["root"] / ".env.spark"),
                "-f",
                str(state["root"] / "compose.spark.yml"),
            ]
            if argv[10:] == ["config", "--format", "json"]:
                assert timeout == 30
                output = json.dumps(state["document"])
            else:
                assert argv[10:] == ["up", "-d", "--no-build", "--pull", "never"]
                assert timeout == 120
                output = "private captured Docker output"
        return subprocess.CompletedProcess(argv, 0, output, "")

    runner = create_autospec(subprocess.run, side_effect=run)
    monkeypatch.setattr(helper.subprocess, "run", runner)

    def open_ready(request, data=None, timeout=None):
        assert data is None and 0 < timeout <= 3
        assert request.full_url == "http://127.0.0.1:8090/ready"
        assert request.get_method() == "GET" and not request.headers
        state["requests"].append(request.full_url)
        if isinstance(state["ready"], Exception):
            raise state["ready"]
        body = state["ready"]
        return io.BytesIO(body if isinstance(body, bytes) else json.dumps(body).encode())

    opener = create_autospec(urllib.request.OpenerDirector, instance=True)
    opener.open.side_effect = open_ready

    def build(*handlers):
        assert len(handlers) == 2
        assert isinstance(handlers[0], urllib.request.ProxyHandler) and handlers[0].proxies == {}
        assert isinstance(handlers[1], urllib.request.HTTPRedirectHandler)
        return opener

    monkeypatch.setattr(
        helper.urllib.request,
        "build_opener",
        create_autospec(urllib.request.build_opener, side_effect=build),
    )
    state["runner"] = runner
    return state


def test_prepared_runtime_starts_and_repeated_start_is_safe(helper, runtime):
    for _ in range(2):
        assert helper.ensure_runtime(runtime["root"]) == {"status": "ready", "image_id": IMAGE}
    assert len(runtime["calls"]) == 6
    assert len(runtime["requests"]) == 2


def test_current_reviewed_meeting_proxy_preparation_is_accepted_without_docker(helper, runtime):
    assert helper.validate_preparation(runtime["root"]) == {
        "SPARK_INFERENCE_IMAGE": IMAGE,
        "INFERENCE_INTERNAL_KEY": KEY,
    }
    runtime["runner"].assert_not_called()


@pytest.mark.parametrize(
    "missing",
    [
        "compose.spark.yml",
        "nginx.spark.conf",
        ".env.spark",
        "models/speaker-pilot/manifest.json",
        "models/speaker-pilot/ecapa/embedding_model.ckpt",
    ],
)
def test_missing_preparation_fails_before_docker(helper, runtime, missing):
    (runtime["root"] / missing).unlink()
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_missing_preparation"):
        helper.ensure_runtime(runtime["root"])
    runtime["runner"].assert_not_called()


@pytest.mark.parametrize("changed", ["compose.spark.yml", "nginx.spark.conf"])
def test_changed_reviewed_templates_fail_before_docker(helper, runtime, changed):
    with (runtime["root"] / changed).open("ab") as output:
        output.write(b"\n# changed template\n")
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_template_changed"):
        helper.ensure_runtime(runtime["root"])
    runtime["runner"].assert_not_called()


@pytest.mark.parametrize("mode", [0o644, 0o400, 0o660])
def test_private_environment_requires_exact_permissions(helper, runtime, monkeypatch, mode):
    monkeypatch.setattr(helper, "private_mode", lambda path: mode)
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_env_permissions"):
        helper.ensure_runtime(runtime["root"])
    runtime["runner"].assert_not_called()


@pytest.mark.parametrize(
    "content",
    [
        f"SPARK_INFERENCE_IMAGE=mutable:latest\nINFERENCE_INTERNAL_KEY={KEY}\n",
        f"SPARK_INFERENCE_IMAGE={IMAGE}\nINFERENCE_INTERNAL_KEY=short\n",
        f"SPARK_INFERENCE_IMAGE={IMAGE}\nINFERENCE_INTERNAL_KEY={KEY}\nEXTRA=value\n",
        f"SPARK_INFERENCE_IMAGE={IMAGE}\nINFERENCE_INTERNAL_KEY={KEY}\nINFERENCE_INTERNAL_KEY={KEY}\n",
    ],
)
def test_invalid_private_configuration_never_reaches_docker_or_logs(helper, runtime, content):
    (runtime["root"] / ".env.spark").write_text(content, encoding="utf-8")
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_invalid_env") as error:
        helper.ensure_runtime(runtime["root"])
    assert KEY not in str(error.value)
    runtime["runner"].assert_not_called()


@pytest.mark.parametrize(
    "defect",
    [
        "service",
        "profile",
        "image",
        "key",
        "port",
        "network",
        "cdi",
        "root",
        "writable",
        "mount",
        "privileged",
    ],
)
def test_unsafe_resolved_compose_fails_before_start(helper, runtime, defect):
    document = runtime["document"]
    inference = document["services"]["inference"]
    relay = document["services"]["relay"]
    if defect == "service":
        document["services"]["extra"] = copy.deepcopy(relay)
    elif defect == "profile":
        inference["profiles"] = ["unexpected"]
    elif defect == "image":
        inference["image"] = "mutable:latest"
    elif defect == "key":
        inference["environment"]["VOICEUP_INFERENCE_INTERNAL_KEY"] = "another-private-value"
    elif defect == "port":
        relay["ports"][0]["host_ip"] = "0.0.0.0"
    elif defect == "network":
        inference["networks"]["edge"] = None
    elif defect == "cdi":
        inference["devices"] = []
    elif defect == "root":
        inference["user"] = "0:0"
    elif defect == "writable":
        inference["read_only"] = False
    elif defect == "mount":
        inference["volumes"][0]["source"] = "/var/run/docker.sock"
    else:
        inference["privileged"] = True
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_unsafe_compose"):
        helper.ensure_runtime(runtime["root"])
    assert len(runtime["calls"]) == 2


@pytest.mark.parametrize(
    "daemon",
    [
        {"OSType": "windows", "Architecture": "aarch64"},
        {"OSType": "linux", "Architecture": "x86_64"},
    ],
)
def test_wrong_daemon_never_starts_services(helper, runtime, daemon):
    runtime["daemon"] = daemon
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_requires_linux_arm64"):
        helper.ensure_runtime(runtime["root"])
    assert len(runtime["calls"]) == 1


@pytest.mark.parametrize("failed", ["unavailable", "timeout", "command"])
def test_docker_errors_are_bounded_and_sanitized(helper, runtime, failed):
    if failed == "unavailable":
        runtime["runner"].side_effect = FileNotFoundError("private path")
    elif failed == "timeout":
        runtime["runner"].side_effect = subprocess.TimeoutExpired([KEY], 15, output=KEY)
    else:
        runtime["runner"].side_effect = None
        runtime["runner"].return_value = subprocess.CompletedProcess([], 1, KEY, KEY)
    with pytest.raises(helper.RuntimeStartError) as error:
        helper.ensure_runtime(runtime["root"])
    assert str(error.value).startswith("spark_runtime_docker_") and KEY not in str(error.value)
    assert len(runtime["runner"].call_args_list) == 1


@pytest.mark.parametrize(
    "ready",
    [
        {**READY, "device": "cpu"},
        {**READY, "model_revision": "unexpected"},
        {**READY, "dimensions": 256},
        {**READY, "ready": False},
        {**READY, "ready": 1},
        pytest.param(b"x" * 5000, id="oversized_response"),
        urllib.error.URLError("private failure"),
    ],
)
def test_unready_incorrect_or_unavailable_runtime_has_finite_failure(helper, runtime, ready):
    runtime["ready"] = ready
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_not_ready"):
        helper.ensure_runtime(runtime["root"])
    assert 1 <= len(runtime["requests"]) <= 61
    assert runtime["clock"] == 60


def test_redirect_does_not_forward_to_another_origin(helper):
    with pytest.raises(urllib.error.HTTPError):
        helper.NoRedirect().redirect_request(None, None, 302, "found", {}, "http://other/ready")


def test_cli_returns_one_safe_json_document(helper, runtime, monkeypatch, capsys):
    monkeypatch.setattr(helper.Path, "home", lambda: runtime["root"].parent)
    assert helper.main() == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {"status": "ready", "image_id": IMAGE}
    assert KEY not in captured.out


def test_cli_failure_never_prints_traceback_or_private_data(helper, runtime, monkeypatch, capsys):
    monkeypatch.setattr(helper.Path, "home", lambda: runtime["root"].parent)
    runtime["runner"].side_effect = subprocess.TimeoutExpired([KEY], 15, output=KEY)
    assert helper.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "error", "code": "spark_runtime_docker_timeout"}
    assert KEY not in captured.err


def test_symlinked_model_is_rejected_before_docker(helper, runtime):
    original = runtime["root"] / "models/speaker-pilot/ecapa/embedding_model.ckpt"
    original.unlink()
    try:
        original.symlink_to(runtime["root"] / "compose.spark.yml")
    except OSError:
        pytest.skip("This Windows account cannot create symbolic links")
    with pytest.raises(helper.RuntimeStartError, match="spark_runtime_unsafe_path"):
        helper.ensure_runtime(runtime["root"])
    runtime["runner"].assert_not_called()
