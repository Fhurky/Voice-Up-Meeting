"""Start the already prepared Spark runtime; send this helper over authenticated SSH stdin.

This standard-library host utility never installs, downloads, rewrites configuration,
changes networking or invokes sudo. The model container keeps its own bundle verifier.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DOCKER = ["docker", "--host", "unix:///var/run/docker.sock"]
TEMPLATE_HASHES = {
    "compose.spark.yml": "d11d08cd927da330bdfe63a7ed15776da4d428ee4c9bc5504b9e8e32b7b9ce60",
    "nginx.spark.conf": "8eea1b3b3e560e1f286c3418832ea074a89fd74677e276cf0fa2790c936e3c93",
}
RELAY_IMAGE = "nginx:alpine@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752"
READY = {
    "ready": True,
    "model_id": "speechbrain/spkrec-ecapa-voxceleb",
    "model_revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
    "dimensions": 192,
    "device": "cuda:0",
}
MODEL_FILES = {
    "ecapa/classifier.ckpt",
    "ecapa/embedding_model.ckpt",
    "ecapa/hyperparams.yaml",
    "ecapa/label_encoder.txt",
    "ecapa/mean_var_norm_emb.ckpt",
    "silero/silero_vad.jit",
}


class RuntimeStartError(Exception):
    """A fixed public error code that contains no private subprocess output."""


def require(condition, code):
    if not condition:
        raise RuntimeStartError("spark_runtime_" + code)


def safe_path(path, *, directory=False):
    require(path.is_absolute(), "unsafe_path")
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink(), "unsafe_path")
    require(path.is_dir() if directory else path.is_file(), "missing_preparation")
    return path


def read_small(path, limit=16384):
    with safe_path(path).open("rb") as source:
        content = source.read(limit + 1)
    require(len(content) <= limit, "invalid_preparation")
    return content


def private_mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def validate_preparation(root):
    safe_path(root, directory=True)
    for name, expected in TEMPLATE_HASHES.items():
        require(hashlib.sha256(read_small(root / name)).hexdigest() == expected, "template_changed")
    env_path = safe_path(root / ".env.spark")
    require(private_mode(env_path) == 0o600, "env_permissions")
    values = {}
    for line in read_small(env_path).decode("utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        require(
            separator
            and name in {"SPARK_INFERENCE_IMAGE", "INFERENCE_INTERNAL_KEY"}
            and name not in values,
            "invalid_env",
        )
        value = value.strip()
        if value.startswith("'"):
            require(
                len(value) >= 2 and value.endswith("'") and "'" not in value[1:-1], "invalid_env"
            )
            value = value[1:-1]
        else:
            require(not any(character in value for character in "\"'\\$ "), "invalid_env")
        require(not any(ord(character) < 32 for character in value), "invalid_env")
        values[name] = value
    require(set(values) == {"SPARK_INFERENCE_IMAGE", "INFERENCE_INTERNAL_KEY"}, "invalid_env")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", values["SPARK_INFERENCE_IMAGE"]), "invalid_env")
    require(32 <= len(values["INFERENCE_INTERNAL_KEY"].encode("utf-8")) <= 512, "invalid_env")
    models = safe_path(root / "models/speaker-pilot", directory=True)
    manifest = json.loads(read_small(models / "manifest.json"))
    require(
        isinstance(manifest, dict)
        and all(
            manifest.get(key) == READY[key] for key in ("model_id", "model_revision", "dimensions")
        )
        and set(manifest.get("files", {})) == MODEL_FILES,
        "invalid_model_manifest",
    )
    for relative in MODEL_FILES:
        safe_path(models / relative)
    return values


def run_command(root, arguments, *, timeout):
    try:
        result = subprocess.run(
            [*DOCKER, *arguments],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env={
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "HOME": str(Path.home()),
                "LC_ALL": "C",
            },
        )
    except subprocess.TimeoutExpired:
        raise RuntimeStartError("spark_runtime_docker_timeout") from None
    except OSError:
        raise RuntimeStartError("spark_runtime_docker_unavailable") from None
    require(result.returncode == 0, "docker_command_failed")
    require(len(result.stdout) <= 131072, "docker_output_limit")
    return result.stdout


def validate_compose(document, root, values):
    """Check resolved values as well as the reviewed source hashes before any Docker write."""
    try:
        require(
            document["name"] == "voiceup-spark"
            and set(document["services"]) == {"inference", "relay"},
            "unsafe_compose",
        )
        inference, relay = (document["services"][name] for name in ("inference", "relay"))
        for service, user, image, networks, source, target in (
            (
                inference,
                "10001:10001",
                values["SPARK_INFERENCE_IMAGE"],
                {"inference"},
                root / "models/speaker-pilot",
                "/models/speaker",
            ),
            (
                relay,
                "101:101",
                RELAY_IMAGE,
                {"inference", "edge"},
                root / "nginx.spark.conf",
                "/etc/nginx/conf.d/default.conf",
            ),
        ):
            require(
                service["image"] == image
                and service["platform"] == "linux/arm64"
                and service["pull_policy"] == "never"
                and service["user"] == user
                and service["read_only"] is True
                and service["cap_drop"] == ["ALL"]
                and service["security_opt"] == ["no-new-privileges:true"]
                and set(service["networks"]) == networks
                and service["restart"] == "unless-stopped"
                and not any(
                    service.get(key)
                    for key in (
                        "profiles",
                        "build",
                        "privileged",
                        "cap_add",
                        "network_mode",
                        "pid",
                        "ipc",
                        "gpus",
                        "runtime",
                    )
                ),
                "unsafe_compose",
            )
            require(
                service["volumes"]
                == [
                    {
                        "type": "bind",
                        "source": str(source),
                        "target": target,
                        "read_only": True,
                        "bind": {"create_host_path": False},
                    }
                ],
                "unsafe_compose",
            )
        require(
            inference.get("ports", []) == []
            and inference["devices"]
            == [
                {
                    "source": "nvidia.com/gpu=0",
                    "target": "nvidia.com/gpu=0",
                    "permissions": "rwm",
                }
            ]
            and inference.get("command") is None
            and inference.get("entrypoint") is None,
            "unsafe_compose",
        )
        require(
            inference["environment"]
            == {
                "VOICEUP_INFERENCE_INTERNAL_KEY": values["INFERENCE_INTERNAL_KEY"],
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
            },
            "unsafe_compose",
        )
        require(
            relay["ports"]
            == [
                {
                    "mode": "ingress",
                    "host_ip": "127.0.0.1",
                    "target": 8090,
                    "published": "8090",
                    "protocol": "tcp",
                }
            ]
            and not relay.get("environment")
            and not relay.get("devices")
            and relay["dns"] == ["127.0.0.1"],
            "unsafe_compose",
        )
        require(set(document["networks"]) == {"inference", "edge"}, "unsafe_compose")
        for name, network in document["networks"].items():
            require(
                network["name"] == "voiceup-spark_" + name
                and network["driver"] == "bridge"
                and not network.get("external")
                and network.get("internal", False) == (name == "inference"),
                "unsafe_compose",
            )
    except (KeyError, TypeError, AttributeError):
        raise RuntimeStartError("spark_runtime_unsafe_compose") from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            "http://127.0.0.1:8090/ready", code, "redirect_rejected", {}, None
        )


def wait_ready():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request("http://127.0.0.1:8090/ready", method="GET")
            with opener.open(request, timeout=min(3, deadline - time.monotonic())) as response:
                content = response.read(4097)
            if len(content) <= 4096:
                ready = json.loads(content)
                if ready == READY and ready["ready"] is True:
                    return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    raise RuntimeStartError("spark_runtime_not_ready")


def ensure_runtime(root):
    require(
        platform.system() == "Linux" and platform.machine() == "aarch64", "requires_linux_arm64"
    )
    require(getattr(os, "geteuid", lambda: -1)() > 0, "requires_nonroot_user")
    values = validate_preparation(root)
    daemon = json.loads(run_command(root, ["info", "--format", "{{json .}}"], timeout=15))
    require(
        isinstance(daemon, dict)
        and daemon.get("OSType") == "linux"
        and daemon.get("Architecture") in {"aarch64", "arm64"},
        "requires_linux_arm64",
    )
    compose = [
        "compose",
        "--project-name",
        "voiceup-spark",
        "--env-file",
        str(root / ".env.spark"),
        "-f",
        str(root / "compose.spark.yml"),
    ]
    document = json.loads(run_command(root, [*compose, "config", "--format", "json"], timeout=30))
    validate_compose(document, root, values)
    run_command(root, [*compose, "up", "-d", "--no-build", "--pull", "never"], timeout=120)
    wait_ready()
    return {"status": "ready", "image_id": values["SPARK_INFERENCE_IMAGE"]}


def main():
    try:
        result = ensure_runtime(Path.home() / "voiceup-runtime")
    except RuntimeStartError as exc:
        print(json.dumps({"status": "error", "code": str(exc)}), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError):
        print(
            json.dumps({"status": "error", "code": "spark_runtime_invalid_preparation"}),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
