"""Bounded read-only remote facts; these tests never call a GPU or Docker daemon."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def inspection():
    path = Path(__file__).resolve().parents[1] / "scripts" / "inspect-spark.py"
    spec = importlib.util.spec_from_file_location("spark_inspection", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_command_output_is_bounded(inspection):
    result = inspection.run_command(
        [sys.executable, "-c", "print('x' * 100000)"], timeout=3, max_bytes=128
    )
    assert result["status"] == "output_limit"
    assert len(result["stdout"].encode()) <= 128


def test_missing_command_is_explicit(inspection):
    result = inspection.run_command(["voiceup-spark-inspection-nonexistent-tool"])
    assert result["status"] == "missing_tool"


def test_command_timeout_is_explicit(inspection):
    result = inspection.run_command(
        [sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1
    )
    assert result["status"] == "timeout"


def test_permission_error_never_returns_stderr_secrets(inspection):
    result = inspection.run_command(
        [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('permission denied: private-token'); sys.exit(1)",
        ]
    )
    assert result["status"] == "permission_denied"
    assert "private-token" not in json.dumps(result)


@pytest.fixture
def fake_host(inspection, monkeypatch):
    calls = []
    monkeypatch.setattr(inspection.platform, "system", lambda: "Linux")
    monkeypatch.setattr(inspection.platform, "machine", lambda: "aarch64")

    def read_file(path, limit=262144):
        values = {
            "/etc/os-release": 'ID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04"\nSECRET=must-not-appear\n',
            "/proc/cpuinfo": "processor\t: 0\nmodel name\t: ARM test processor\n",
            "/proc/meminfo": "MemTotal: 131072000 kB\nMemAvailable: 100000000 kB\n",
        }
        return {"status": "ok", "text": values[str(path)]}

    def run_command(argv, *, timeout=8, max_bytes=32768):
        calls.append(argv)
        if argv[0] == "nvidia-smi":
            output = "NVIDIA Test GPU, 999.1, 12.1\n"
        elif "info" in argv:
            output = '{"server_version":"29.0","architecture":"aarch64","os_type":"linux","default_runtime":"runc","runtime_names":["runc","nvidia",null]}'
        elif "image" in argv:
            output = (
                '{"repository":"nvcr.io/nvidia/pytorch","tag":"test-py3","id":"sha256:fixture","digest":"sha256:manifest"}\n'
                '{"repository":"private.example/secret","tag":"do-not-emit","id":"secret","digest":"secret"}'
            )
        elif "address" in argv:
            output = '[{"ifname":"enp1s0","operstate":"UP","flags":["UP"],"link_type":"ether","address":"must-not-emit-mac","addr_info":[{"family":"inet","local":"192.0.2.2","prefixlen":24,"scope":"global"}]},{"ifname":"wlan0","operstate":"UP","flags":["UP"],"link_type":"ether","addr_info":[{"family":"inet","local":"198.51.100.2","prefixlen":24}]}]'
        else:
            output = '[{"dst":"default","gateway":"192.0.2.1","dev":"enp1s0","metric":100}]'
        return {"status": "ok", "return_code": 0, "stdout": output}

    monkeypatch.setattr(inspection, "read_file", read_file)
    monkeypatch.setattr(inspection, "run_command", run_command)
    monkeypatch.setattr(
        inspection, "interface_kind", lambda name: "wifi" if name == "wlan0" else "ethernet"
    )
    return calls


def test_selected_facts_and_cached_pytorch_images_only(inspection, fake_host):
    report = inspection.collect()
    assert report["status"] == "complete"
    assert report["system"]["architecture"] == "aarch64"
    assert report["memory"]["total_bytes"] == 131072000 * 1024
    assert report["memory"]["available_bytes"] == 100000000 * 1024
    assert report["gpu"]["items"][0]["compute_capability"] == "12.1"
    assert report["docker"]["runtime_names"] == ["runc", "nvidia"]
    assert report["pytorch_images"]["items"] == [
        {
            "repository": "nvcr.io/nvidia/pytorch",
            "tag": "test-py3",
            "id": "sha256:fixture",
            "digest": "sha256:manifest",
        }
    ]
    assert [item["kind"] for item in report["network"]["interfaces"]["items"]] == [
        "ethernet",
        "wifi",
    ]
    assert report["read_only"] is True and report["model_executed"] is False
    text = json.dumps(report)
    assert (
        "must-not-appear" not in text
        and "private.example" not in text
        and "must-not-emit-mac" not in text
    )
    assert all(command[0] in {"nvidia-smi", "docker", "ip"} for command in fake_host)
    assert all(
        "--host" in command and "unix:///var/run/docker.sock" in command
        for command in fake_host
        if command[0] == "docker"
    )
    assert not any(
        word in command
        for command in fake_host
        for word in ("sudo", "pull", "run", "install", "exec")
    )


def test_missing_tools_and_docker_permissions_are_partial(inspection, fake_host, monkeypatch):
    def unavailable(argv, *, timeout=8, max_bytes=32768):
        return {
            "status": "permission_denied" if argv[0] == "docker" else "missing_tool",
            "return_code": None,
            "stdout": "private-token",
        }

    monkeypatch.setattr(inspection, "run_command", unavailable)
    report = inspection.collect()
    assert report["status"] == "partial"
    assert report["docker"]["status"] == "permission_denied"
    assert report["gpu"]["status"] == "missing_tool"
    assert "private-token" not in json.dumps(report)


def test_malformed_tool_output_is_explicit(inspection, fake_host, monkeypatch):
    def malformed(argv, *, timeout=8, max_bytes=32768):
        return {"status": "ok", "return_code": 0, "stdout": "not valid output"}

    monkeypatch.setattr(inspection, "run_command", malformed)
    report = inspection.collect()
    assert report["status"] == "partial"
    assert report["docker"]["status"] == "invalid_output"
    assert report["network"]["interfaces"]["status"] == "invalid_output"


def test_missing_proc_files_do_not_claim_memory_zero(inspection, fake_host, monkeypatch):
    monkeypatch.setattr(
        inspection, "read_file", lambda path, limit=262144: {"status": "missing_file"}
    )
    report = inspection.collect()
    assert report["memory"]["status"] == "missing_file"
    assert "total_bytes" not in report["memory"]
    assert report["status"] == "partial"


def test_source_can_be_invoked_through_standard_input(inspection):
    source = Path(inspection.__file__).read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-", "--help"],
        input=source,
        text=True,
        capture_output=True,
        timeout=5,
        check=True,
    )
    assert "read-only" in result.stdout.lower()
    assert "voiceup" not in result.stderr.lower()
