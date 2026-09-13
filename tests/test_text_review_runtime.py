"""Installed-model setup preserves local secrets and closed network boundaries."""

import importlib.util
import http.server
import json
import os
from pathlib import Path
import subprocess
import threading

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "text_review_setup", ROOT / "scripts/setup-local-text-review.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configuration_preserves_unrelated_bytes_and_retries(setup, tmp_path):
    path = tmp_path / "app/infra/.env"
    path.parent.mkdir(parents=True)
    source = (
        '# fixture\nexport JWT_SECRET = "keep-this-fixture" # exact\nTEXT_REVIEW_ENABLED=false\n'
    )
    path.write_text(source, encoding="utf-8")
    setup.configure(tmp_path, enabled=True, model="qwen3.5:27b", digest="a" * 64)
    first = path.read_bytes()
    assert source.splitlines()[1] in first.decode()
    assert b"TEXT_REVIEW_ENABLED=true" in first
    assert b"TEXT_REVIEW_MODEL_DIGEST=" + b"a" * 64 in first
    assert (tmp_path / "outputs/local-text-review-enabled.txt").read_text() == "enabled\n"
    setup.configure(tmp_path, enabled=True, model="qwen3.5:27b", digest="a" * 64)
    assert path.read_bytes() == first
    setup.configure(tmp_path, enabled=False, model="qwen3.5:27b", digest="")
    assert b"TEXT_REVIEW_ENABLED=false" in path.read_bytes()
    assert (tmp_path / "outputs/local-text-review-enabled.txt").read_text() == "disabled\n"


@pytest.mark.parametrize("fault", ["duplicate", "malformed", "missing"])
def test_setup_rejects_invalid_configuration_without_rewriting(setup, tmp_path, fault):
    path = tmp_path / "app/infra/.env"
    path.parent.mkdir(parents=True)
    if fault != "missing":
        source = (
            "JWT_SECRET=fixture\nJWT_SECRET=other\n"
            if fault == "duplicate"
            else "JWT_SECRET='unclosed\n"
        )
        path.write_text(source)
    before = path.read_bytes() if path.exists() else None
    with pytest.raises(ValueError):
        setup.configure(tmp_path, enabled=True, model="qwen3.5:27b", digest="a" * 64)
    assert (path.read_bytes() if path.exists() else None) == before
    assert not (tmp_path / "outputs/local-text-review-enabled.txt").exists()


@pytest.mark.parametrize("fault", ["remote_host", "remote_model", "digest", "duplicate", "missing"])
def test_installed_identity_rejects_remote_changed_or_ambiguous_models(setup, fault):
    item = {"name": "qwen3.5:27b", "digest": "a" * 64}
    tags = {"models": [item]}
    detail = {"capabilities": ["completion"]}
    if fault in {"remote_host", "remote_model"}:
        detail[fault] = "remote"
    elif fault == "digest":
        item["digest"] = "invalid"
    elif fault == "duplicate":
        tags["models"].append(dict(item))
    else:
        tags["models"] = []
    with pytest.raises(ValueError):
        setup.model_identity(tags, detail, "qwen3.5:27b")


def test_installed_identity_returns_only_selected_local_digest(setup):
    assert (
        setup.model_identity(
            {"models": [{"name": "qwen3.5:27b", "digest": "a" * 64}]},
            {"capabilities": ["completion"]},
            "qwen3.5:27b",
        )
        == "a" * 64
    )


def test_configuration_preserves_bom_without_duplicate_selection(setup, tmp_path):
    path = tmp_path / "app/infra/.env"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\ufeffTEXT_REVIEW_ENABLED=false\r\nJWT_SECRET=fixture\r\n", encoding="utf-8", newline=""
    )
    setup.configure(tmp_path, enabled=True, model="qwen3.5:27b", digest="a" * 64)
    result = path.read_bytes()
    assert result.startswith(b"\xef\xbb\xbfTEXT_REVIEW_ENABLED=true\r\n")
    assert result.count(b"TEXT_REVIEW_ENABLED") == 1


@pytest.mark.parametrize("fault", ["redirect", "oversized", "json", "valid"])
def test_real_loopback_http_rejects_redirects_and_unbounded_metadata(setup, fault):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302 if fault == "redirect" else 200)
            self.send_header("Location", "http://127.0.0.1:1/forbidden")
            self.end_headers()
            body = (
                b"x" * 1048577
                if fault == "oversized"
                else b"invalid"
                if fault == "json"
                else b'{"models":[]}'
            )
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        if fault == "valid":
            assert setup.request_json("GET", "/api/tags", port=server.server_port) == {"models": []}
        else:
            with pytest.raises(ValueError):
                setup.request_json("GET", "/api/tags", port=server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("mode", ["local", "spark", "x86_64", "aarch64"])
def test_real_compose_preserves_closed_networks_and_optional_model_identity(tmp_path, mode):
    fixture = tmp_path / "fixture.env"
    fixture.write_text(
        "INFERENCE_INTERNAL_KEY=fixture-"
        + "x" * 32
        + "\nRUNTIME_DATABASE_PASSWORD=fixture-"
        + "x" * 32
        + "\nGRAFANA_ADMIN_PASSWORD=fixture\nTEXT_REVIEW_ENABLED=true\nTEXT_REVIEW_MODEL_DIGEST="
        + "a" * 64
        + "\nCPU_ARCH="
        + (mode if mode in {"aarch64", "x86_64"} else "x86_64")
        + "\n"
    )
    command = [
        "docker",
        "compose",
        "--project-directory",
        str(ROOT / "app/infra"),
        "--env-file",
        str(fixture),
        "-p",
        "voiceup-text-fixture",
        "-f",
        str(ROOT / "app/infra/docker-compose.local.yml"),
    ]
    if mode != "local":
        overlay = "spark" if mode == "spark" else "cpu"
        command.extend(["-f", str(ROOT / f"app/infra/docker-compose.{overlay}.yml")])
    command.extend(
        [
            "-f",
            str(ROOT / "app/infra/docker-compose.text-review.yml"),
            "--profile",
            "*",
            "config",
            "--format",
            "json",
        ]
    )
    # Only non-secret fixture assignments participate in Compose interpolation.
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "USERPROFILE",
            "COMSPEC",
            "TEMP",
            "TMP",
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_CONFIG",
            "APPDATA",
            "LOCALAPPDATA",
            "PROGRAMDATA",
            "PROGRAMFILES",
            "HOMEDRIVE",
            "HOMEPATH",
            "HOME",
        }
    }
    result = subprocess.run(command, capture_output=True, timeout=30, env=environment)
    assert result.returncode == 0, "Compose fixture failed; resolved values withheld"
    model = json.loads(result.stdout)
    services = model["services"]
    for name in ("backend", "worker", "migrate"):
        service = services[name]
        assert service["environment"]["VOICEUP_TEXT_REVIEW_ENABLED"] == "true"
        assert service["environment"]["VOICEUP_TEXT_REVIEW_MODEL_DIGEST"] == "a" * 64
        assert service["environment"]["VOICEUP_TEXT_REVIEW_URL"] == "http://nginx:9081"
        assert set(service["networks"]) == {"default"}
        assert not service.get("ports")
    assert model["networks"]["default"]["internal"] is True
    proxy = services["nginx"]
    assert proxy["entrypoint"] == ["/bin/sh", "/opt/voiceup/start-text-review-proxy.sh"]
    assert "voiceup-text-host=host-gateway" in proxy["extra_hosts"]
    assert proxy["dns"] == ["127.0.0.1"]
    assert proxy["user"] == "101:101" and proxy["read_only"] is True
    assert all(item["target"] == 8080 and item["host_ip"] == "127.0.0.1" for item in proxy["ports"])
    if mode == "spark":
        assert "voiceup-spark-host=host-gateway" in proxy["extra_hosts"]
        assert services["inference"]["profiles"] == ["local-inference"]
