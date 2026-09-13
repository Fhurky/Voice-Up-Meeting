"""Real delayed HTTP responses must survive the public preview proxy in both modes."""

import http.server
import re
import secrets
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "app/infra"
PREVIEW_PATH = "/api/voiceup/v1/meetings/11111111-1111-4111-8111-111111111111/transcript/22222222-2222-4222-8222-222222222222/correction-preview"
REVIEW_PATHS = (PREVIEW_PATH, PREVIEW_PATH.replace("correction-preview", "correction-suggestion"))


def test_slow_preview_survives_public_proxy_while_other_api_keeps_timeout(tmp_path):
    class DelayedBackend(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            time.sleep(65)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"fixture":"delayed-preview"}')
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"fixture-ready")

        def log_message(self, *_):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DelayedBackend)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    image = re.search(
        r"NGINX_IMAGE:-([^}]+)", (INFRA / "docker-compose.local.yml").read_text(encoding="utf-8")
    )[1]
    public = tmp_path / "public.conf"
    public.write_text(
        (INFRA / "nginx/nginx.local.conf")
        .read_text(encoding="utf-8")
        .replace("backend:8000", f"backend:{server.server_port}")
        .replace("frontend:3000", f"frontend:{server.server_port}"),
        encoding="utf-8",
    )
    created = []

    def docker(*arguments, timeout=20):
        return subprocess.run(["docker", *arguments], capture_output=True, timeout=timeout)

    def request(name, path):
        start = time.monotonic()
        response = docker(
            "exec",
            name,
            "wget",
            "-S",
            "-O",
            "-",
            "-T",
            "75",
            "--post-data={}",
            "http://127.0.0.1:8080" + path,
            timeout=80,
        )
        return response, time.monotonic() - start

    try:
        for mode in ("local", "spark"):
            name = "voiceup-text-timeout-" + mode + "-" + secrets.token_hex(6)
            arguments = [
                "run",
                "-d",
                "--rm",
                "--pull",
                "never",
                "--name",
                name,
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
            ]
            for alias in ("backend", "frontend", "voiceup-text-host", "voiceup-spark-host"):
                arguments.extend(["--add-host", f"{alias}:host-gateway"])
            mounts = [
                (public, "/etc/nginx/conf.d/default.conf"),
                (INFRA / "nginx/nginx.text-review.conf", "/etc/nginx/text-review.conf.template"),
                (
                    INFRA / "nginx/start-text-review-proxy.sh",
                    "/opt/voiceup/start-text-review-proxy.sh",
                ),
            ]
            if mode == "spark":
                mounts.extend(
                    [
                        (INFRA / "nginx/nginx.spark.conf", "/etc/nginx/spark.conf.template"),
                        (INFRA / "nginx/start-spark-proxy.sh", "/opt/voiceup/start-spark-proxy.sh"),
                    ]
                )
            for source, target in mounts:
                arguments.extend(
                    ["--mount", f"type=bind,source={source.resolve()},target={target},readonly"]
                )
            arguments.extend(
                ["--entrypoint", "/bin/sh", image, "/opt/voiceup/start-text-review-proxy.sh"]
            )
            started = docker(*arguments)
            assert started.returncode == 0, started.stderr.decode(errors="replace")
            created.append(name)
            for _ in range(30):
                probe = docker(
                    "exec", name, "wget", "-qO-", "-T", "2", "http://127.0.0.1:8080/api/ready"
                )
                if probe.returncode == 0:
                    break
                time.sleep(0.1)
            assert probe.stdout == b"fixture-ready", docker("logs", name).stderr.decode(
                errors="replace"
            )
        with ThreadPoolExecutor(max_workers=6) as pool:
            pending = [
                (mode, path, pool.submit(request, name, path))
                for mode, name in zip(("local", "spark"), created, strict=True)
                for path in (*REVIEW_PATHS, "/api/fixture-slow")
            ]
            results = [(mode, path, *future.result()) for mode, path, future in pending]
        for mode, path, response, elapsed in results:
            if path in REVIEW_PATHS:
                assert response.returncode == 0 and b"200 OK" in response.stderr, (
                    f"{mode}: delayed preview returned a proxy error at {elapsed:.1f}s: {response.stderr.decode(errors='replace')}"
                )
                assert response.stdout == b'{"fixture":"delayed-preview"}'
                assert 64 <= elapsed < 80
            else:
                assert response.returncode != 0 and b"504" in response.stderr
                assert 59 <= elapsed < 65
    finally:
        for name in created:
            assert docker("rm", "-f", name).returncode == 0
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
