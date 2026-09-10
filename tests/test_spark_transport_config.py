"""Resolve the real Compose model without loading or printing local secrets."""

import hashlib
import http.client
import http.server
import ipaddress
import json
import os
import re
import secrets
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "app" / "infra"


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_TRANSPORT") != "1",
    reason="Explicit Docker transport verification uses a disposable internal network",
)
def test_nginx_reload_refreshes_replaced_backend_and_checks_active_private_config(
    compose_models, tmp_path
):
    """Exercise real cached upstream addresses without touching any application container."""
    image = compose_models["remote"]["services"]["nginx"]["image"]
    match = re.search(
        r"(?m)^\s+\$nginxReloadCommand = '([^'\r\n]+)'$",
        (ROOT / "scripts/start-local.ps1").read_text(encoding="utf-8-sig"),
    )
    assert match is not None, "The launcher must provide its bounded active-config reload"
    reload_command = match[1]
    suffix = secrets.token_hex(6)
    network, proxy = f"voiceup-reload-{suffix}", f"voiceup-reload-proxy-{suffix}"
    old_backend, new_backend = f"voiceup-reload-old-{suffix}", f"voiceup-reload-new-{suffix}"
    created = []
    network_created = False

    def docker(*args, check=True):
        result = subprocess.run(["docker", *args], capture_output=True, timeout=20, check=False)
        if check:
            assert result.returncode == 0, result.stderr.decode(errors="replace")[-2048:]
        return result

    def server_config(body):
        return (
            "worker_processes 1; pid /tmp/nginx.pid; error_log /dev/stderr; "
            "events {} http { access_log off; server { listen 8080; "
            f'location / {{ return 200 "{body}"; }}'
            "} }\n"
        )

    for filename, body in (("old.conf", "old-backend"), ("new.conf", "new-backend")):
        (tmp_path / filename).write_text(server_config(body), encoding="utf-8")
    private = tmp_path / "private.conf"
    private.write_text("server { listen 9080; return 204; }\n", encoding="utf-8")
    (tmp_path / "proxy.conf").write_text(
        "worker_processes 1; pid /tmp/nginx.pid; error_log /dev/stderr; "
        "events {} http { access_log off; include /fixture/private.conf; "
        "server { listen 8080; location / { proxy_connect_timeout 1s; "
        "proxy_next_upstream off; proxy_pass http://backend:8080; } } }\n",
        encoding="utf-8",
    )

    def start(name, config, *, address=None, alias=None):
        arguments = [
            "run",
            "-d",
            "--rm",
            "--pull",
            "never",
            "--name",
            name,
            "--network",
            network,
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
            "--mount",
            f"type=bind,source={tmp_path},target=/fixture,readonly",
        ]
        if address:
            arguments.extend(["--ip", address])
        if alias:
            arguments.extend(["--network-alias", alias])
        if name == proxy:
            arguments.extend(
                [
                    "--entrypoint",
                    "/bin/sh",
                    image,
                    "-c",
                    (
                        "mkdir /tmp/voiceup-spark.fixture; cp /fixture/proxy.conf /tmp/voiceup-spark.fixture/nginx.conf; "
                        "exec nginx -c /tmp/voiceup-spark.fixture/nginx.conf -g 'daemon off;'"
                    ),
                ]
            )
        else:
            arguments.extend(
                ["--entrypoint", "nginx", image, "-c", f"/fixture/{config}", "-g", "daemon off;"]
            )
        docker(*arguments)
        created.append(name)

    def probe(host="127.0.0.1"):
        return docker(
            "exec",
            proxy,
            "wget",
            "-qO-",
            "-T",
            "2",
            f"http://{host}:8080/api/voiceup/v1/readiness",
            check=False,
        )

    def wait_for(body, host="127.0.0.1"):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = probe(host)
            if result.returncode == 0 and result.stdout == body:
                return
            time.sleep(0.1)
        pytest.fail("Disposable nginx did not reach the expected fixture backend")

    try:
        docker("network", "create", "--internal", network)
        network_created = True
        config = json.loads(docker("network", "inspect", network).stdout)[0]
        subnet = ipaddress.ip_network(config["IPAM"]["Config"][0]["Subnet"])
        assert subnet.version == 4 and subnet.num_addresses > 16
        old_address, new_address = (
            str(subnet.network_address + 10),
            str(subnet.network_address + 11),
        )
        start(old_backend, "old.conf", address=old_address, alias="backend")
        start(proxy, "proxy.conf")
        wait_for(b"old-backend")

        private.write_text("invalid-private-directive;\n", encoding="utf-8")
        rejected = docker("exec", proxy, "sh", "-c", reload_command, check=False)
        assert rejected.returncode != 0
        assert b"private.conf" in rejected.stderr
        wait_for(b"old-backend")
        private.write_text("server { listen 9080; return 204; }\n", encoding="utf-8")

        docker("rm", "--force", old_backend)
        created.remove(old_backend)
        start(new_backend, "new.conf", address=new_address, alias="backend")
        wait_for(b"new-backend", host="backend")
        stale = probe()
        # The retired address can refuse the connection or silently time out.
        assert stale.returncode != 0 and any(code in stale.stderr for code in (b"502", b"504"))
        docker("exec", proxy, "sh", "-c", reload_command)
        wait_for(b"new-backend")
        docker(
            "exec", proxy, "mv", "/tmp/voiceup-spark.fixture/nginx.conf", "/tmp/active-nginx.saved"
        )
        assert docker("exec", proxy, "sh", "-c", reload_command, check=False).returncode != 0
        wait_for(b"new-backend")
        docker(
            "exec", proxy, "mv", "/tmp/active-nginx.saved", "/tmp/voiceup-spark.fixture/nginx.conf"
        )
        docker("exec", proxy, "mkdir", "/tmp/voiceup-spark.second")
        docker("exec", proxy, "touch", "/tmp/voiceup-spark.second/nginx.conf")
        assert docker("exec", proxy, "sh", "-c", reload_command, check=False).returncode != 0
        wait_for(b"new-backend")
        assert (
            docker("exec", proxy, "wget", "-qO-", "-T", "2", "http://127.0.0.1:9080/").returncode
            == 0
        )
    finally:
        for name in reversed(created):
            docker("rm", "--force", name)
        if network_created:
            docker("network", "rm", network)


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_TRANSPORT") != "1", reason="Explicit Docker transport verification"
)
def test_ipv4_proxy_reaches_all_workers_without_post_retries(compose_models, tmp_path):
    """A nonce server uses an ephemeral port; the real SSH tunnel is untouched."""
    image = compose_models["remote"]["services"]["nginx"]["image"]
    nonce = secrets.token_hex(16).encode()
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.send_header("Content-Length", str(len(nonce)))
            self.end_headers()
            self.wfile.write(nonce)

        def log_message(self, *_args):
            pass

    class FixtureServer(http.server.ThreadingHTTPServer):
        request_queue_size = 128

    server = FixtureServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    name = "voiceup-ipv4-test-" + secrets.token_hex(5)
    created = False
    main = tmp_path / "nginx.conf"
    main.write_text(
        "worker_processes 4;\npid /tmp/nginx.pid;\nerror_log /dev/stderr notice;\nevents { worker_connections 1024; }\nhttp {\n include /etc/nginx/conf.d/*.conf;\n}\n",
        encoding="utf-8",
        newline="\n",
    )
    public = tmp_path / "public.conf"
    public.write_text("server { listen 8080; return 204; }\n", encoding="utf-8", newline="\n")
    private = tmp_path / "spark.conf"
    private.write_text(
        (INFRA / "nginx/nginx.spark.conf")
        .read_text()
        .replace(":18090;", f":{server.server_port};")
        .replace("listen 9080;", "listen 9080;\n  add_header X-Proxy-Worker $pid always;"),
        encoding="utf-8",
        newline="\n",
    )

    def docker(*args):
        result = subprocess.run(["docker", *args], capture_output=True, timeout=20, check=False)
        assert result.returncode == 0, result.stderr.decode(errors="replace")[-2048:]
        return result.stdout.decode().strip()

    try:
        command = [
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "--pull",
            "never",
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
            "voiceup-spark-host:host-gateway",
            "-p",
            "127.0.0.1::9080",
        ]
        for source, target in [
            (main, "/etc/nginx/nginx.conf"),
            (public, "/etc/nginx/conf.d/default.conf"),
            (private, "/etc/nginx/spark.conf.template"),
            (INFRA / "nginx/start-spark-proxy.sh", "/opt/voiceup/start-spark-proxy.sh"),
        ]:
            command += ["--mount", f"type=bind,source={source},target={target},readonly"]
        command += ["--entrypoint", "/bin/sh", image, "/opt/voiceup/start-spark-proxy.sh"]
        docker(*command)
        created = True
        port = int(
            json.loads(docker("inspect", name))[0]["NetworkSettings"]["Ports"]["9080/tcp"][0][
                "HostPort"
            ]
        )
        mapping = docker("exec", name, "cat", "/etc/hosts")
        families = [
            ipaddress.ip_address(line.split()[0]).version
            for line in mapping.splitlines()
            if "voiceup-spark-host" in line.split()[1:]
        ]
        assert sorted(families) == [4, 6], "This regression must exercise dual-stack host-gateway"

        def post(index):
            client = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            try:
                client.request(
                    "POST",
                    "/v1/embeddings?purpose=identify",
                    body=f"fixture-{index}".encode(),
                    headers={"Connection": "close"},
                )
                response = client.getresponse()
                return response.status, response.read(2048), response.getheader("X-Proxy-Worker")
            finally:
                client.close()

        with ThreadPoolExecutor(max_workers=25) as pool:
            responses = list(pool.map(post, range(50)))
        statuses = [status for status, _body, _pid in responses]
        assert statuses == [200] * 50, f"POST statuses: {statuses}"
        assert all(body == nonce for _status, body, _pid in responses)
        assert len({pid for _status, _body, pid in responses}) == 4
        assert len(received) == 50 and len(set(received)) == 50
        rendered = docker(
            "exec",
            name,
            "sh",
            "-c",
            'cat /tmp/voiceup-spark.*/spark.conf; stat -c "%a" /tmp/voiceup-spark.*/spark.conf /tmp/voiceup-spark.*',
        )
        assert "http://voiceup-spark-host:" not in rendered
        assert rendered.splitlines()[-2:] == ["600", "700"]
        print("dual_stack_post_checks=50; nginx_workers=4; upstream_requests=50")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if created:
            docker("rm", "--force", name)


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_TRANSPORT") != "1", reason="Explicit Docker transport verification"
)
@pytest.mark.parametrize(
    "hosts",
    [
        "127.0.0.1 localhost\n",
        "fdc4:f303:9324::254 voiceup-spark-host\n",
        "256.1.1.1 voiceup-spark-host\n",
        "172.017.0.1 voiceup-spark-host\n",
        "172.17.0.1 voiceup-spark-host\n172.18.0.1 voiceup-spark-host\n",
        "172.17.0.1;echo voiceup-spark-host\n172.17.0.1 voiceup-spark-host\n",
    ],
)
def test_private_proxy_rejects_missing_invalid_or_ambiguous_ipv4(compose_models, tmp_path, hosts):
    fixture = tmp_path / "hosts"
    fixture.write_text(hosts, encoding="utf-8", newline="\n")
    image = compose_models["remote"]["services"]["nginx"]["image"]
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--user",
            "101:101",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--mount",
            f"type=bind,source={fixture},target=/etc/hosts,readonly",
            "--mount",
            f"type=bind,source={INFRA / 'nginx/start-spark-proxy.sh'},target=/opt/voiceup/start-spark-proxy.sh,readonly",
            "--entrypoint",
            "/bin/sh",
            image,
            "/opt/voiceup/start-spark-proxy.sh",
        ],
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == b"" and result.stderr.strip() == b"spark_proxy_start_failed"


@pytest.fixture(scope="module")
def compose_models(tmp_path_factory):
    fixture_env = tmp_path_factory.mktemp("spark-compose") / ".env"
    fixture_env.write_text("# No local secrets are loaded by these configuration tests.\n")
    env = {
        **os.environ,
        "COMPOSE_PROFILES": "",
        "POSTGRES_PASSWORD": "fixture-only-postgres",
        "JWT_SECRET": "fixture-only-jwt-" + "x" * 32,
        "RUNTIME_DATABASE_PASSWORD": "fixture-only-runtime-" + "x" * 32,
        "INFERENCE_INTERNAL_KEY": "fixture-only-inference-" + "x" * 32,
        "GRAFANA_ADMIN_PASSWORD": "fixture-only-grafana",
    }

    def resolve(*, remote=False, all_profiles=False):
        command = [
            "docker",
            "compose",
            "--project-directory",
            str(INFRA),
            "-p",
            "voiceup-transport-test",
            "--env-file",
            str(fixture_env),
            "-f",
            str(INFRA / "docker-compose.local.yml"),
            "-f",
            str(INFRA / "docker-compose.observability.yml"),
        ]
        if remote:
            command.extend(["-f", str(INFRA / "docker-compose.spark.yml")])
        if all_profiles:
            command.extend(["--profile", "*"])
        result = subprocess.run(
            [*command, "config", "--format", "json"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        assert result.returncode == 0, "Compose model resolution failed; output withheld"
        return json.loads(result.stdout)

    return {
        "local": resolve(),
        "remote": resolve(remote=True),
        "all": resolve(remote=True, all_profiles=True),
    }


def test_remote_consumers_use_private_origin_and_preserve_environment(compose_models):
    local = compose_models["local"]["services"]
    remote = compose_models["all"]["services"]
    for name in ("backend", "worker", "migrate"):
        assert remote[name]["environment"]["VOICEUP_INFERENCE_URL"] == "http://nginx:9080"
    for name in ("backend", "worker"):
        expected = {**local[name]["environment"], "VOICEUP_INFERENCE_URL": "http://nginx:9080"}
        assert remote[name]["environment"] == expected
        assert remote[name]["volumes"] == local[name]["volumes"]


def test_worker_and_backend_remain_internal_with_no_published_ports(compose_models):
    remote = compose_models["remote"]
    assert remote["networks"]["default"]["internal"] is True
    for name in ("backend", "worker", "postgres", "redis"):
        service = remote["services"][name]
        assert set(service["networks"]) == {"default"}
        assert service.get("ports", []) == []
    assert set(remote["services"]["nginx"]["networks"]) == {"default", "edge"}


def test_local_inference_is_excluded_from_remote_autostart_only(compose_models):
    assert "inference" in compose_models["local"]["services"]
    assert "inference" not in compose_models["remote"]["services"]
    gated = compose_models["all"]["services"]["inference"]
    assert gated["profiles"] == ["local-inference"]
    assert gated["deploy"]["resources"]["reservations"]["devices"][0]["capabilities"] == ["gpu"]


def test_nginx_private_listener_is_not_published_and_public_mount_is_preserved(compose_models):
    local = compose_models["local"]["services"]["nginx"]
    remote = compose_models["remote"]["services"]["nginx"]
    assert remote["ports"] == local["ports"]
    assert [port["target"] for port in remote["ports"]] == [8080]
    assert all(port["host_ip"] == "127.0.0.1" for port in remote["ports"])
    mounts = {entry["target"]: entry for entry in remote["volumes"]}
    assert mounts["/etc/nginx/conf.d/default.conf"] == local["volumes"][0]
    assert mounts["/etc/nginx/spark.conf.template"]["read_only"] is True
    assert Path(mounts["/etc/nginx/spark.conf.template"]["source"]).name == "nginx.spark.conf"
    assert mounts["/opt/voiceup/start-spark-proxy.sh"]["read_only"] is True
    assert remote["entrypoint"] == ["/bin/sh", "/opt/voiceup/start-spark-proxy.sh"]
    assert remote["command"] == []
    assert remote["user"] == "101:101" and remote["read_only"] is True
    assert remote["cap_drop"] == ["ALL"]
    assert remote["security_opt"] == ["no-new-privileges:true"]
    assert remote["tmpfs"] == [
        "/var/cache/nginx:rw,nosuid,nodev,size=16777216,mode=1777",
        "/var/run:rw,nosuid,nodev,size=1048576,mode=1777",
        "/tmp:rw,nosuid,nodev,size=16777216,mode=1777",
    ]
    assert remote["extra_hosts"] == ["voiceup-spark-host=host-gateway"]


def test_overlay_adds_no_dependency_or_application_setting(compose_models):
    local = compose_models["local"]["services"]
    remote = compose_models["remote"]["services"]
    assert set(remote) == set(local) - {"inference"}
    for name in remote:
        assert remote[name].get("image") == local[name].get("image")
        assert remote[name].get("build") == local[name].get("build")


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_TRANSPORT") != "1",
    reason="Explicit RUN_DOCKER_TRANSPORT=1 enables the disposable Docker Desktop loopback test",
)
def test_nginx_live_transport_contract(compose_models, tmp_path):
    """Only a task-owned proxy and in-memory HTTP fixture are started; no model runs."""
    image = compose_models["remote"]["services"]["nginx"]["image"]
    assert "@sha256:" in image
    nonce = secrets.token_hex(24)
    fixture_key = "fixture-only-" + secrets.token_hex(24)
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def respond(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            seen.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "headers": dict(self.headers),
                    "body": body,
                }
            )
            payload = json.dumps({"transport_fixture": nonce}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = respond

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    private = tmp_path / "spark.conf"
    template = (INFRA / "nginx/nginx.spark.conf").read_text()
    assert template.count("http://voiceup-spark-host:18090;") == 2
    private.write_text(
        template.replace(":18090;", f":{server.server_port};"), encoding="utf-8", newline="\n"
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    name = "voiceup-spark-transport-test-" + secrets.token_hex(5)
    created = False
    proxy_address = None
    worker_id = None

    def docker(*args, input=None):
        result = subprocess.run(
            ["docker", *args], input=input, capture_output=True, timeout=15, check=False
        )
        if result.returncode:
            raise AssertionError("Disposable Docker probe failed; diagnostic output withheld")
        return result.stdout

    def request(method, path, *, body=b"", headers=None):
        fields = {
            "Host": "private-transport-test",
            "Connection": "close",
            "Content-Length": str(len(body)),
            **(headers or {}),
        }
        code = "import http.client,json,sys; q=json.load(sys.stdin); c=http.client.HTTPConnection(q['host'],9080,timeout=5); c.request(q['method'],q['path'],body=bytes.fromhex(q['body']),headers=q['headers']); r=c.getresponse(); print(json.dumps({'status':r.status,'body':r.read(2048).hex()})); c.close()"
        payload = json.dumps(
            {
                "host": proxy_address,
                "method": method,
                "path": path,
                "headers": fields,
                "body": body.hex(),
            }
        ).encode()
        response = json.loads(docker("exec", "-i", worker_id, "python", "-c", code, input=payload))
        return response["status"], bytes.fromhex(response["body"])

    try:
        docker(
            "run",
            "--detach",
            "--rm",
            "--name",
            name,
            "--pull",
            "never",
            "--network",
            "voiceup_default",
            "--add-host",
            "voiceup-spark-host:host-gateway",
            "--user",
            "101:101",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/var/cache/nginx:size=16777216,mode=1777",
            "--tmpfs",
            "/var/run:size=1048576,mode=1777",
            "--tmpfs",
            "/tmp:size=16777216,mode=1777",
            "--mount",
            f"type=bind,source={INFRA / 'nginx/nginx.local.conf'},target=/etc/nginx/conf.d/default.conf,readonly",
            "--mount",
            f"type=bind,source={private},target=/etc/nginx/spark.conf.template,readonly",
            "--mount",
            f"type=bind,source={INFRA / 'nginx/start-spark-proxy.sh'},target=/opt/voiceup/start-spark-proxy.sh,readonly",
            "--entrypoint",
            "/bin/sh",
            image,
            "/opt/voiceup/start-spark-proxy.sh",
        )
        created = True
        # Only the disposable proxy joins the edge network; the existing worker is unchanged.
        docker("network", "connect", "voiceup_edge", name)
        proxy_address = (
            docker(
                "inspect",
                name,
                "--format",
                '{{(index .NetworkSettings.Networks "voiceup_default").IPAddress}}',
            )
            .decode()
            .strip()
        )
        ipaddress.IPv4Address(proxy_address)
        workers = (
            docker(
                "ps",
                "--filter",
                "label=com.docker.compose.project=voiceup",
                "--filter",
                "label=com.docker.compose.service=worker",
                "--format",
                "{{.ID}}",
            )
            .decode()
            .splitlines()
        )
        assert len(workers) == 1, "The live test requires exactly one running VoiceUp worker"
        worker_id = workers[0]
        docker("exec", name, "sh", "-c", "nginx -t -c /tmp/voiceup-spark.*/nginx.conf")
        mapping = docker("exec", name, "cat", "/etc/hosts").decode()
        addresses = [
            ipaddress.ip_address(line.split()[0])
            for line in mapping.splitlines()
            if "voiceup-spark-host" in line.split()[1:]
        ]
        assert len([value for value in addresses if value.version == 4]) == 1
        print("host_gateway_families=" + json.dumps([value.version for value in addresses]))

        # Repeated requests also expose an unusable IPv6 address in an upstream hostname pool.
        for _ in range(12):
            status, body = request("GET", "/ready")
            assert status == 200, "Mapped loopback upstream did not return HTTP 200"
            assert nonce.encode() in body
        payload = b"VoiceUp transport fixture; this is not audio or a model result."
        status, _ = request(
            "POST",
            "/v1/embeddings?purpose=identify",
            body=payload,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Inference-Key": fixture_key,
                "X-Job-Id": "fixture-job",
                "X-Tenant-Id": "fixture-tenant",
            },
        )
        assert status == 200
        captured = seen[-1]
        assert (
            captured["method"] == "POST" and captured["path"] == "/v1/embeddings?purpose=identify"
        )
        assert captured["body"] == payload
        assert captured["headers"]["X-Inference-Key"] == fixture_key
        assert captured["headers"]["X-Job-Id"] == "fixture-job"
        assert captured["headers"]["X-Tenant-Id"] == "fixture-tenant"
        count = len(seen)
        for method, path, expected in [
            ("HEAD", "/ready", 405),
            ("POST", "/ready", 405),
            ("GET", "/v1/embeddings", 405),
            ("PUT", "/v1/embeddings", 405),
            ("GET", "/api/voiceup/v1/speaker-jobs", 404),
            ("GET", "/ready/extra", 404),
        ]:
            assert request(method, path)[0] == expected
        assert (
            request(
                "POST", "/v1/embeddings", headers={"Content-Length": str(51 * 1024 * 1024 + 1)}
            )[0]
            == 413
        )
        assert len(seen) == count, (
            "Rejected routes/methods/body lengths must never reach the upstream"
        )
        logs = docker("logs", name)
        assert fixture_key.encode() not in logs and payload not in logs
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        started = time.monotonic()
        assert request("GET", "/ready")[0] == 502
        assert time.monotonic() - started < 6
        print("transport_checks=21; upstream_body_sha256=" + hashlib.sha256(payload).hexdigest())
    except BaseException:
        if created:
            diagnostic = subprocess.run(
                ["docker", "logs", "--tail", "20", name],
                capture_output=True,
                timeout=15,
                check=False,
            )
            text = (diagnostic.stdout + diagnostic.stderr).decode(errors="replace")
            print(
                text.replace(fixture_key, "[redacted-fixture]").replace(nonce, "[redacted-nonce]")[
                    -4096:
                ]
            )
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if created:
            cleanup = subprocess.run(
                ["docker", "rm", "--force", name], capture_output=True, timeout=15, check=False
            )
            assert cleanup.returncode == 0 or b"No such container" in cleanup.stderr
