"""Resolve the Spark-only deployment with fixture configuration, never real secrets."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "app/inference/compose.spark.yml"
IMAGE = "sha256:" + "1" * 64
KEY = "fixture-only-internal-key-" + "x" * 32


def resolve(tmp_path, **overrides):
    fixture_env = tmp_path / ".env"
    fixture_env.write_text("# This fixture loads no local secrets.\n", encoding="utf-8")
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("COMPOSE_")
    }
    environment.update(SPARK_INFERENCE_IMAGE=IMAGE, INFERENCE_INTERNAL_KEY=KEY)
    environment.update(overrides)
    return subprocess.run(
        [
            "docker",
            "compose",
            "--project-directory",
            str(tmp_path),
            "--env-file",
            str(fixture_env),
            "-f",
            str(COMPOSE),
            "config",
            "--format",
            "json",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.fixture
def model(tmp_path):
    result = resolve(tmp_path)
    assert result.returncode == 0, "Fixture Compose resolution failed; output withheld"
    return json.loads(result.stdout)


def test_service_requires_explicit_image_and_single_native_gpu(model):
    assert model["name"] == "voiceup-spark"
    assert set(model["services"]) == {"inference", "relay"}
    service = model["services"]["inference"]
    assert service["image"] == IMAGE
    assert service["pull_policy"] == "never"
    assert service["platform"] == "linux/arm64"
    assert service["devices"] == [
        {"source": "nvidia.com/gpu=0", "target": "nvidia.com/gpu=0", "permissions": "rwm"}
    ]
    assert "build" not in service and "runtime" not in service and "gpus" not in service
    assert service["restart"] == "unless-stopped"


def test_loopback_publication_and_internal_network_are_exclusive(model):
    service = model["services"]["inference"]
    assert service.get("ports", []) == []
    assert model["services"]["relay"]["ports"] == [
        {
            "mode": "ingress",
            "host_ip": "127.0.0.1",
            "target": 8090,
            "published": "8090",
            "protocol": "tcp",
        }
    ]
    assert set(service["networks"]) == {"inference"}
    assert set(model["services"]["relay"]["networks"]) == {"inference", "edge"}
    assert set(model["networks"]) == {"inference", "edge"}
    assert model["networks"]["inference"]["internal"] is True
    assert model["networks"]["inference"]["driver"] == "bridge"
    assert model["networks"]["edge"].get("internal", False) is False


def test_relay_reuses_pinned_arm_image_without_gpu_secrets_or_privileges(model, tmp_path):
    relay = model["services"]["relay"]
    assert relay["image"] == (
        "nginx:alpine@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752"
    )
    assert relay["platform"] == "linux/arm64" and relay["pull_policy"] == "never"
    assert relay["user"] == "101:101" and relay["read_only"] is True
    assert relay["cap_drop"] == ["ALL"]
    assert relay["security_opt"] == ["no-new-privileges:true"]
    assert relay["dns"] == ["127.0.0.1"]
    assert relay.get("environment", {}) == {}
    assert not any(key in relay for key in ("build", "devices", "gpus", "runtime"))
    assert relay["tmpfs"] == [
        "/var/cache/nginx:rw,nosuid,nodev,size=16777216,mode=1777",
        "/var/run:rw,nosuid,nodev,size=1048576,mode=1777",
        "/tmp:rw,nosuid,nodev,size=16777216,mode=1777",
    ]
    mount = relay["volumes"][0]
    assert len(relay["volumes"]) == 1
    assert Path(mount["source"]) == tmp_path / "nginx.spark.conf"
    assert mount["target"] == "/etc/nginx/conf.d/default.conf" and mount["read_only"] is True
    assert mount["bind"]["create_host_path"] is False
    assert relay["depends_on"]["inference"]["condition"] == "service_healthy"


def test_relay_has_fixed_authenticated_routes_and_bounded_forwarding():
    config = (COMPOSE.parent / "nginx.spark.conf").read_text(encoding="utf-8")
    for directive in (
        "listen 8090;",
        "access_log off;",
        "client_max_body_size 51m;",
        "resolver 127.0.0.11 valid=5s ipv6=off;",
        "resolver_timeout 2s;",
        "set $inference_origin http://inference:8090;",
        "proxy_connect_timeout 3s;",
        "proxy_send_timeout 300s;",
        "proxy_read_timeout 300s;",
        "proxy_request_buffering off;",
        "proxy_buffering off;",
        "proxy_next_upstream off;",
        "proxy_set_header X-Inference-Key $http_x_inference_key;",
        "proxy_set_header X-Job-Id $http_x_job_id;",
        "proxy_set_header X-Tenant-Id $http_x_tenant_id;",
        "location = /ready",
        "if ($request_method != GET) { return 405; }",
        "location = /v1/embeddings",
        "if ($request_method != POST) { return 405; }",
        "location / {",
        "return 404;",
    ):
        assert directive in config
    assert config.count("proxy_pass $inference_origin;") == 2


def test_readonly_nonroot_and_bounded_scratch(model, tmp_path):
    service = model["services"]["inference"]
    assert service["user"] == "10001:10001"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["tmpfs"] == ["/tmp:rw,nosuid,nodev,size=536870912"]
    assert len(service["volumes"]) == 1
    mount = service["volumes"][0]
    assert mount["type"] == "bind" and mount["read_only"] is True
    assert Path(mount["source"]) == tmp_path / "models/speaker-pilot"
    assert mount["target"] == "/models/speaker"
    assert mount["bind"]["create_host_path"] is False
    assert service.get("privileged", False) is False


def test_configuration_carries_only_inference_values_and_ready_healthcheck(model):
    service = model["services"]["inference"]
    assert service["environment"] == {
        "VOICEUP_INFERENCE_INTERNAL_KEY": KEY,
        "VOICEUP_INFERENCE_MODEL_DIR": "/models/speaker",
        "VOICEUP_INFERENCE_DEVICE": "cuda:0",
        "VOICEUP_INFERENCE_RUNTIME_PROFILE": "aarch64-cu129",
        "VOICEUP_INFERENCE_HOST": "0.0.0.0",
        "VOICEUP_INFERENCE_PORT": "8090",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HOME": "/tmp",
        "XDG_CACHE_HOME": "/tmp/cache",
        "CUDA_CACHE_PATH": "/tmp/cuda",
    }
    health = service["healthcheck"]
    assert health["test"][:3] == ["CMD", "python", "-c"]
    assert "http://127.0.0.1:8090/ready" in health["test"][3]
    assert health["timeout"] == "5s" and health["start_period"] == "1m0s"


@pytest.mark.parametrize("missing", ["SPARK_INFERENCE_IMAGE", "INFERENCE_INTERNAL_KEY"])
def test_missing_required_deployment_value_fails_closed(tmp_path, missing):
    result = resolve(tmp_path, **{missing: ""})
    assert result.returncode != 0
    assert missing in result.stderr


def test_template_has_no_usable_secret_or_mutable_image_default():
    template = (COMPOSE.parent / ".env.spark.example").read_text(encoding="utf-8")
    assignments = [line for line in template.splitlines() if line and not line.startswith("#")]
    assert assignments == ["SPARK_INFERENCE_IMAGE=", "INFERENCE_INTERNAL_KEY="]
