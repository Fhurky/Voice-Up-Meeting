"""Contract tests for the local Rancher Streamable HTTP MCP release."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHART = REPOSITORY_ROOT / "helm/kt-scaffold-mcp"
DIGEST_ONE = "sha256:" + "1" * 64
DIGEST_TWO = "sha256:" + "2" * 64


def _helm() -> str:
    executable = shutil.which("helm")
    if executable is None:
        pytest.skip("helm is required for chart rendering tests")
    return executable


def _render(*extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _helm(),
            "template",
            "kt-scaffold-mcp",
            str(CHART),
            "--kube-version",
            "1.33.13",
            "--namespace",
            "kt-scaffold-mcp",
            "--set-string",
            f"mcp.image.digest={DIGEST_ONE}",
            "--set-string",
            f"proxy.image.digest={DIGEST_TWO}",
            *extra,
        ],
        text=True,
        capture_output=True,
        check=check,
    )


def _documents(*extra: str) -> list[dict[str, Any]]:
    rendered = _render(*extra).stdout
    return [document for document in yaml.safe_load_all(rendered) if document]


def test_chart_keeps_every_resource_in_one_template() -> None:
    assert sorted(path.name for path in (CHART / "templates").iterdir()) == ["all.yaml"]
    assert (CHART / "Chart.yaml").is_file()
    assert (CHART / "values.yaml").is_file()


def test_default_release_is_digest_gated() -> None:
    completed = subprocess.run(
        [_helm(), "template", "kt-scaffold-mcp", str(CHART), "--kube-version", "1.33.13"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "mcp.image.digest is required" in completed.stderr


def test_release_is_loopback_proxied_and_hardened() -> None:
    documents = _documents()
    by_kind = {document["kind"]: document for document in documents}

    assert set(by_kind) == {
        "ConfigMap",
        "Deployment",
        "NetworkPolicy",
        "Service",
        "ServiceAccount",
    }
    assert by_kind["ServiceAccount"]["automountServiceAccountToken"] is False

    deployment = by_kind["Deployment"]
    pod = deployment["spec"]["template"]["spec"]
    assert pod["automountServiceAccountToken"] is False
    assert pod["securityContext"] == {
        "runAsNonRoot": True,
        "seccompProfile": {"type": "RuntimeDefault"},
    }

    containers = {container["name"]: container for container in pod["containers"]}
    assert set(containers) == {"mcp", "proxy"}
    assert containers["mcp"]["image"].endswith(f"@{DIGEST_ONE}")
    assert containers["proxy"]["image"].endswith(f"@{DIGEST_TWO}")
    assert containers["mcp"]["args"][3:5] == ["--host", "127.0.0.1"]
    assert containers["proxy"]["command"] == ["nginx"]
    assert containers["proxy"]["args"] == ["-g", "daemon off;"]

    for container in containers.values():
        security = container["securityContext"]
        assert security["allowPrivilegeEscalation"] is False
        assert security["readOnlyRootFilesystem"] is True
        assert security["capabilities"]["drop"] == ["ALL"]
        assert set(container["resources"]) == {"limits", "requests"}
        assert {"startupProbe", "readinessProbe", "livenessProbe"} <= set(container)

    writable_volumes = [volume for volume in pod["volumes"] if "emptyDir" in volume]
    assert all(volume["emptyDir"]["sizeLimit"] == "32Mi" for volume in writable_volumes)
    assert by_kind["Service"]["spec"]["type"] == "ClusterIP"
    assert by_kind["Service"]["spec"]["ports"][0]["targetPort"] == "http"

    proxy_config = by_kind["ConfigMap"]["data"]["default.conf"]
    assert "proxy_pass http://127.0.0.1:8000;" in proxy_config
    assert "proxy_set_header Host 127.0.0.1:8000;" in proxy_config
    assert "proxy_buffering off;" in proxy_config
    assert "client_max_body_size 1m;" in proxy_config
    assert "/scaffold-bundles/" not in proxy_config
    assert "/scaffold-applicator/" not in proxy_config
    assert "add_header Content-Type" not in proxy_config
    assert "default_type text/plain;" in proxy_config

    policy = by_kind["NetworkPolicy"]["spec"]
    assert policy["policyTypes"] == ["Ingress", "Egress"]
    assert policy["egress"] == []


def test_ingress_is_explicit_and_streaming_safe() -> None:
    documents = _documents(
        "--set",
        "ingress.enabled=true",
        "--set-string",
        "ingress.host=mcp.lab.internal",
        "--set",
        "ingress.tls.enabled=true",
        "--set-string",
        "ingress.tls.secretName=kt-scaffold-mcp-tls",
    )
    ingress = next(document for document in documents if document["kind"] == "Ingress")

    assert ingress["spec"]["ingressClassName"] == "nginx"
    assert ingress["spec"]["rules"][0]["host"] == "mcp.lab.internal"
    assert [path["path"] for path in ingress["spec"]["rules"][0]["http"]["paths"]] == ["/mcp"]
    assert ingress["spec"]["tls"][0]["secretName"] == "kt-scaffold-mcp-tls"
    annotations = ingress["metadata"]["annotations"]
    assert annotations["nginx.ingress.kubernetes.io/proxy-buffering"] == "off"
    assert annotations["nginx.ingress.kubernetes.io/proxy-body-size"] == "1m"


def test_http_mcp_container_has_no_delivery_origin_or_workspace_authority() -> None:
    documents = _documents()
    deployment = next(document for document in documents if document["kind"] == "Deployment")
    mcp_container = next(
        container
        for container in deployment["spec"]["template"]["spec"]["containers"]
        if container["name"] == "mcp"
    )
    assert "env" not in mcp_container
    assert "--workspace-root" not in mcp_container["args"]


def test_malformed_digest_is_rejected() -> None:
    completed = _render("--set-string", "mcp.image.digest=latest", check=False)

    assert completed.returncode != 0
    assert "mcp.image.digest must be an immutable sha256 digest" in completed.stderr


def test_workspace_blind_governance_plane_can_scale_without_pod_local_artifacts() -> None:
    documents = _documents("--set", "replicaCount=2")
    deployment = next(document for document in documents if document["kind"] == "Deployment")
    assert deployment["spec"]["replicas"] == 2
