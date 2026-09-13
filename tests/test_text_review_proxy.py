"""Real isolated nginx startup exercises local and composed Spark private listeners."""

import re
import secrets
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "app/infra"


@pytest.mark.parametrize("spark", [False, True])
def test_real_proxy_limits_methods_paths_headers_and_preserves_spark(tmp_path, spark):
    source = (INFRA / "docker-compose.local.yml").read_text(encoding="utf-8")
    image = re.search(r"NGINX_IMAGE:-([^}]+)", source)[1]
    name = "voiceup-text-proxy-" + secrets.token_hex(6)
    fixture = tmp_path / "public.conf"
    fixture.write_text(
        'server { listen 8080; location / { return 200 "public-ok"; } }\nserver { listen 11434; location /api/tags { return 200 "tags:$http_authorization:$http_cookie:$http_origin"; } location /api/chat { return 200 "chat-ok"; } location /api/show { return 200 "show-ok"; } }\nserver { listen 18090; location /ready { return 200 "spark-ok"; } }\n',
        encoding="utf-8",
    )
    arguments = [
        "run",
        "-d",
        "--rm",
        "--pull",
        "never",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--user",
        "101:101",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--tmpfs",
        "/tmp:size=16777216,mode=1777",
        "--tmpfs",
        "/var/cache/nginx:size=16777216,mode=1777",
        "--tmpfs",
        "/var/run:size=1048576,mode=1777",
        "--add-host",
        "voiceup-text-host:127.0.0.1",
        "--add-host",
        "voiceup-spark-host:127.0.0.1",
    ]
    mounts = [
        (fixture, "/etc/nginx/conf.d/default.conf"),
        (INFRA / "nginx/nginx.text-review.conf", "/etc/nginx/text-review.conf.template"),
        (INFRA / "nginx/start-text-review-proxy.sh", "/opt/voiceup/start-text-review-proxy.sh"),
    ]
    if spark:
        mounts.extend(
            [
                (INFRA / "nginx/nginx.spark.conf", "/etc/nginx/spark.conf.template"),
                (INFRA / "nginx/start-spark-proxy.sh", "/opt/voiceup/start-spark-proxy.sh"),
            ]
        )
    for path, target in mounts:
        arguments.extend(["--mount", f"type=bind,source={path.resolve()},target={target},readonly"])
    arguments.extend(["--entrypoint", "/bin/sh", image, "/opt/voiceup/start-text-review-proxy.sh"])

    def docker(*values):
        return subprocess.run(["docker", *values], capture_output=True, timeout=20)

    started = False
    try:
        result = docker(*arguments)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        started = True
        for _ in range(30):
            response = docker("exec", name, "wget", "-qO-", "-T", "1", "http://127.0.0.1:8080/")
            if response.returncode == 0:
                break
            time.sleep(0.1)
        assert response.stdout == b"public-ok", docker("logs", name).stdout
        response = docker(
            "exec",
            name,
            "wget",
            "-qO-",
            "-T",
            "2",
            "--header",
            "Authorization: secret-fixture",
            "--header",
            "Cookie: secret-fixture",
            "--header",
            "Origin: secret-fixture",
            "http://127.0.0.1:9081/api/tags",
        )
        assert response.returncode == 0 and response.stdout == b"tags:::"
        for endpoint in ("chat", "show"):
            response = docker(
                "exec",
                name,
                "wget",
                "-qO-",
                "-T",
                "2",
                "--post-data={}",
                f"http://127.0.0.1:9081/api/{endpoint}",
            )
            assert response.returncode == 0 and response.stdout == f"{endpoint}-ok".encode()
        for path in (
            "/api/pull",
            "/api/delete",
            "/api/create",
            "/api/tags/",
            "/api/chat/",
            "/anything",
        ):
            response = docker(
                "exec",
                name,
                "wget",
                "-S",
                "-O",
                "/dev/null",
                "-T",
                "2",
                "http://127.0.0.1:9081" + path,
            )
            assert response.returncode != 0 and b"404" in response.stderr
        response = docker(
            "exec",
            name,
            "wget",
            "-S",
            "-O",
            "/dev/null",
            "-T",
            "2",
            "http://127.0.0.1:9081/api/chat",
        )
        assert response.returncode != 0 and b"405" in response.stderr
        response = docker(
            "exec",
            name,
            "wget",
            "-S",
            "-O",
            "/dev/null",
            "-T",
            "2",
            "--post-data={}",
            "http://127.0.0.1:9081/api/tags",
        )
        assert response.returncode != 0 and b"405" in response.stderr
        if spark:
            response = docker(
                "exec", name, "wget", "-qO-", "-T", "2", "http://127.0.0.1:9080/ready"
            )
            assert response.returncode == 0 and response.stdout == b"spark-ok"
        reload = (
            "set -eu; set -- /tmp/voiceup-"
            + ("spark" if spark else "text")
            + '.*/nginx.conf; [ "$#" -eq 1 ]; nginx -t -c "$1"; nginx -s reload -c "$1"'
        )
        assert docker("exec", name, "sh", "-c", reload).returncode == 0
    finally:
        if started:
            assert docker("rm", "-f", name).returncode == 0
