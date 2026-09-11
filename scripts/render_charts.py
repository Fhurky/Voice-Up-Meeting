"""Render every chart and enforce the egress-free namespace contract."""

from __future__ import annotations

import argparse
import copy
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHARTS = ROOT / "app" / "devops" / "charts"
ENVIRONMENTS = ROOT / "app" / "devops" / "environments"
FIXTURES = ROOT / "tests" / "fixtures" / "overlays"
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}
PUBLIC_REGISTRIES = (
    "docker.io",
    "ghcr.io",
    "quay.io",
    "gcr.io",
    "registry.k8s.io",
    "mcr.microsoft.com",
    "public.ecr.aws",
)
SUPPORTED_APIS = {
    "ConfigMap": "v1",
    "Service": "v1",
    "PersistentVolumeClaim": "v1",
    "Deployment": "apps/v1",
    "StatefulSet": "apps/v1",
    "DaemonSet": "apps/v1",
    "Job": "batch/v1",
    "CronJob": "batch/v1",
    "HorizontalPodAutoscaler": "autoscaling/v2",
    "Ingress": "networking.k8s.io/v1",
    "NetworkPolicy": "networking.k8s.io/v1",
    "PodDisruptionBudget": "policy/v1",
}
CLUSTER_SCOPED = {
    "ClusterRole",
    "ClusterRoleBinding",
    "CustomResourceDefinition",
    "Namespace",
    "Node",
    "PersistentVolume",
    "StorageClass",
}
IMAGE_PATHS = {
    "backend": "app/backend",
    "frontend": "app/frontend",
    "migrate": "app/migrate",
    "worker": "app/backend",
    "inference": "app/inference",
    "postgres": "platform/postgres",
    "redis": "platform/redis",
    "collector": "platform/otel-collector",
    "tempo": "platform/tempo",
    "prometheus": "platform/prometheus",
    "loki": "platform/loki",
    "grafana": "platform/grafana",
}
URL_HOST = re.compile(r"https?://([^/\s:'\",}]+)", re.IGNORECASE)
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
KUBERNETES_VERSION = re.compile(r"1\.(?:2[9-9]|[3-9][0-9])(?:\.[0-9]+)?\Z")
SOURCE_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
PART_OF_LABEL = "app.kubernetes.io/part-of"
SECRET_MATERIAL = re.compile(
    r"(password|passwd|token|private[_-]?key|api[_-]?key|client[_-]?secret)\Z",
    re.IGNORECASE,
)


class PolicyError(RuntimeError):
    """A rendered release or overlay violates the deployment contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def revision_identity(revision: str) -> str:
    """Return the DNS-safe identity derived from every bit of a source revision."""

    return sha256(revision.encode("ascii")).hexdigest()[:12]


def pod_spec(document: dict[str, Any]) -> dict[str, Any]:
    spec = document.get("spec", {})
    if document["kind"] == "CronJob":
        return spec.get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})
    return spec.get("template", {}).get("spec", {})


def pod_labels(document: dict[str, Any]) -> dict[str, str]:
    spec = document.get("spec", {})
    if document["kind"] == "CronJob":
        return (
            spec.get("jobTemplate", {})
            .get("spec", {})
            .get("template", {})
            .get("metadata", {})
            .get("labels", {})
        )
    return spec.get("template", {}).get("metadata", {}).get("labels", {})


def containers(spec: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield from spec.get("initContainers", [])
    yield from spec.get("containers", [])


def nested(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for segment in path.split("."):
        require(isinstance(current, dict) and segment in current, f"overlay missing {path}")
        current = current[segment]
    return current


def unresolved(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if "__REQUIRED_" in value else []
    if isinstance(value, dict):
        return [item for child in value.values() for item in unresolved(child)]
    if isinstance(value, list):
        return [item for child in value for item in unresolved(child)]
    return []


def reject_secret_material(value: Any, location: str = "overlay") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).replace("SecretName", "").replace("secretName", "")
            require(
                not SECRET_MATERIAL.search(normalized),
                f"{location}: secret material key {key}",
            )
            reject_secret_material(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secret_material(child, f"{location}[{index}]")


def load_overlay(root: Path, name: str) -> dict[str, Any]:
    path = root / name / "platform.yaml"
    require(path.is_file(), f"unknown environment: {name}")
    source = re.sub(r"@@[A-Z0-9_]+@@", "generated", path.read_text(encoding="utf-8"))
    data = yaml.safe_load(source)
    require(isinstance(data, dict), f"{name}: overlay must be a mapping")
    return data


def validate_overlay(name: str, overlay: dict[str, Any]) -> None:
    missing = unresolved(overlay)
    require(not missing, f"{name}: unresolved environment facts: {', '.join(missing)}")
    reject_secret_material(overlay, name)
    required = (
        "global.registry",
        "global.host",
        "global.storageClass",
        "global.kubernetesVersion",
        "global.sourceRevision",
        "global.appSecretName",
        "global.inferenceSecretName",
        "global.migrationSecretName",
        "global.databaseSecretName",
        "global.cacheSecretName",
        "global.grafanaSecretName",
        "global.tlsSecretName",
        "ingressController.namespace",
        "ingressController.component",
        "replicas.backend",
        "replicas.frontend",
    )
    for path in required:
        require(bool(nested(overlay, path)), f"{name}: empty {path}")

    runtime_profile = nested(overlay, "inference.runtimeProfile")
    meeting_enabled = nested(overlay, "inference.meetingEnabled")
    require(
        isinstance(runtime_profile, str) and runtime_profile in {"x86_64-cu128", "aarch64-cu129"},
        f"{name}: unsupported inference runtime profile",
    )
    require(isinstance(meeting_enabled, bool), f"{name}: meeting selection must be boolean")
    require(
        not meeting_enabled or runtime_profile == "x86_64-cu128",
        f"{name}: meeting inference requires the admitted x86_64 runtime",
    )

    registry = str(nested(overlay, "global.registry")).rstrip("/")
    registry_host = registry.split("/", 1)[0].split(":", 1)[0].lower()
    require("://" not in registry and "@" not in registry, f"{name}: malformed registry")
    require(
        registry_host not in PUBLIC_REGISTRIES,
        f"{name}: public registry {registry_host}",
    )
    require(
        "." in registry_host,
        f"{name}: registry must be a reviewed fully qualified host",
    )
    version = str(nested(overlay, "global.kubernetesVersion"))
    require(
        bool(KUBERNETES_VERSION.fullmatch(version)),
        f"{name}: invalid Kubernetes version",
    )
    source_revision = str(nested(overlay, "global.sourceRevision"))
    require(
        bool(SOURCE_REVISION.fullmatch(source_revision)),
        f"{name}: source revision must be a full lowercase 40- or 64-character hash",
    )
    require(
        set(source_revision) != {"0"},
        f"{name}: source revision must not be all zeroes",
    )

    for image_name in IMAGE_PATHS:
        digest = str(nested(overlay, f"images.{image_name}.digest"))
        require(bool(DIGEST.fullmatch(digest)), f"{name}/{image_name}: invalid image digest")
        require(digest != f"sha256:{'0' * 64}", f"{name}/{image_name}: zero image digest")


def image_value(overlay: dict[str, Any], name: str) -> dict[str, str]:
    registry = str(nested(overlay, "global.registry")).rstrip("/")
    return {
        "repository": f"{registry}/{IMAGE_PATHS[name]}",
        "digest": str(nested(overlay, f"images.{name}.digest")),
    }


def chart_values(chart: str, overlay: dict[str, Any]) -> dict[str, Any]:
    global_values = overlay["global"]
    ingress = overlay["ingressController"]
    dns = {"namespace": "kube-system", "component": "kube-dns"}
    if chart == "app-backend":
        return {
            "replicaCount": overlay["replicas"]["backend"],
            "audioStorage": {"className": global_values["storageClass"]},
            "image": image_value(overlay, "backend"),
            "existingSecret": global_values["appSecretName"],
            "ingress": {
                "enabled": True,
                "host": global_values["host"],
                "tlsSecretName": global_values["tlsSecretName"],
                "controllerNamespace": ingress["namespace"],
                "controllerComponent": ingress["component"],
            },
            "dns": dns,
        }
    if chart == "app-inference":
        return {
            "image": image_value(overlay, "inference"),
            "existingSecret": global_values["inferenceSecretName"],
            "modelStorage": {"className": global_values["storageClass"]},
            "runtimeProfile": nested(overlay, "inference.runtimeProfile"),
            "meeting": {
                "enabled": nested(overlay, "inference.meetingEnabled"),
                "modelStorage": {"className": global_values["storageClass"]},
            },
        }
    if chart == "app-frontend":
        return {
            "replicaCount": overlay["replicas"]["frontend"],
            "image": image_value(overlay, "frontend"),
            "ingress": {
                "enabled": True,
                "host": global_values["host"],
                "tlsSecretName": global_values["tlsSecretName"],
                "controllerNamespace": ingress["namespace"],
                "controllerComponent": ingress["component"],
            },
        }
    if chart == "app-migrate":
        return {
            "revision": global_values["sourceRevision"],
            "image": image_value(overlay, "migrate"),
            "existingSecret": global_values["migrationSecretName"],
            "dns": dns,
        }
    if chart == "app-worker":
        return {
            "image": image_value(overlay, "worker"),
            "existingSecret": global_values["appSecretName"],
            "dns": dns,
        }
    if chart == "app-postgres":
        return {
            "image": image_value(overlay, "postgres"),
            "existingSecret": global_values["databaseSecretName"],
            "storage": {"className": global_values["storageClass"]},
            "dns": dns,
        }
    if chart == "app-redis":
        return {
            "image": image_value(overlay, "redis"),
            "existingSecret": global_values["cacheSecretName"],
        }
    if chart == "app-observability":
        return {
            "collector": {"image": image_value(overlay, "collector")},
            "tempo": {"image": image_value(overlay, "tempo")},
            "prometheus": {"image": image_value(overlay, "prometheus")},
            "loki": {"image": image_value(overlay, "loki")},
            "grafana": {
                "image": image_value(overlay, "grafana"),
                "existingSecret": global_values["grafanaSecretName"],
            },
            "ingressController": ingress,
            "dns": dns,
        }
    raise PolicyError(f"unmapped chart: {chart}")


def helm(command: list[str]) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode:
        detail = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        raise PolicyError(f"{' '.join(command[:3])} failed: {detail}")
    return completed.stdout


def render_chart(chart: Path, overlay: dict[str, Any], values_dir: Path) -> list[dict[str, Any]]:
    kube_version = str(nested(overlay, "global.kubernetesVersion"))
    values_path = values_dir / f"{chart.name}.yaml"
    values_path.write_text(
        yaml.safe_dump(chart_values(chart.name, overlay), sort_keys=True),
        encoding="utf-8",
    )
    common = ["--kube-version", kube_version, "--values", str(values_path)]
    helm(["helm", "lint", str(chart), *common])
    rendered = helm(["helm", "template", chart.name, str(chart), *common])
    return [document for document in yaml.safe_load_all(rendered) if isinstance(document, dict)]


def render(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="chart-values-") as directory:
        values_dir = Path(directory)
        for chart in sorted(CHARTS.iterdir()):
            if not (chart / "Chart.yaml").is_file():
                continue
            documents.extend(render_chart(chart, overlay, values_dir))
    return documents


def validate_claims(document: dict[str, Any], name: str) -> None:
    claims: list[dict[str, Any]] = []
    if document.get("kind") == "PersistentVolumeClaim":
        claims.append(document)
    if document.get("kind") == "StatefulSet":
        claims.extend(document.get("spec", {}).get("volumeClaimTemplates", []))
    for claim in claims:
        storage = claim.get("spec", {}).get("resources", {}).get("requests", {}).get("storage")
        require(bool(storage), f"{name}: claim has no requested storage size")


def validate_runtime_hosts(documents: list[dict[str, Any]]) -> None:
    services = {
        str(document.get("metadata", {}).get("name"))
        for document in documents
        if document.get("kind") == "Service"
    }
    allowed = services | {"localhost", "127.0.0.1"}
    serialized = yaml.safe_dump_all(documents, sort_keys=True)
    for host in URL_HOST.findall(serialized):
        host = host.lower().rstrip(".")
        require(
            host in allowed or host.endswith(".svc") or host.endswith(".svc.cluster.local"),
            f"runtime URL host has no rendered Service: {host}",
        )


def validate_inference_runtime(document: dict[str, Any], documents: list[dict[str, Any]]) -> None:
    name = str(document.get("metadata", {}).get("name"))
    annotations = (
        document.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
    )
    runtime_profile = annotations.get("voiceup.internal/runtime-profile")
    meeting_value = annotations.get("voiceup.internal/meeting-enabled")
    require(
        isinstance(runtime_profile, str) and runtime_profile in {"x86_64-cu128", "aarch64-cu129"},
        f"{name}: runtime profile missing",
    )
    require(
        isinstance(meeting_value, str) and meeting_value in {"true", "false"},
        f"{name}: explicit meeting selection missing",
    )
    enabled = meeting_value == "true"
    require(
        not enabled or runtime_profile == "x86_64-cu128", f"{name}: meeting runtime not admitted"
    )
    spec = pod_spec(document)
    main = [item for item in spec.get("containers", []) if item.get("name") == "inference"]
    require(len(main) == 1, f"{name}: one inference container is required")
    container = main[0]
    environment = {item.get("name"): item.get("value") for item in container.get("env", [])}
    require(
        environment.get("VOICEUP_INFERENCE_RUNTIME_PROFILE") == runtime_profile,
        f"{name}: runtime profile environment mismatch",
    )
    require(
        environment.get("VOICEUP_INFERENCE_MEETING_ENABLED") == meeting_value,
        f"{name}: meeting environment mismatch",
    )
    for probe, path in (
        ("startupProbe", "/meeting-ready" if enabled else "/live"),
        ("readinessProbe", "/meeting-ready" if enabled else "/ready"),
        ("livenessProbe", "/live"),
    ):
        http = container.get(probe, {}).get("httpGet", {})
        require(
            http.get("path") == path and http.get("port") == "http",
            f"{name}: {probe} does not check the selected runtime",
        )
        require(
            not http.get("httpHeaders"), f"{name}: runtime health probes must not embed headers"
        )
    mounts = {item.get("mountPath"): item for item in container.get("volumeMounts", [])}
    require(
        mounts.get("/models/speaker", {}).get("readOnly") is True,
        f"{name}: pilot models must stay read-only",
    )
    if not enabled:
        return
    selector = spec.get("nodeSelector", {})
    require(
        selector.get("kubernetes.io/os") == "linux"
        and selector.get("kubernetes.io/arch") == "amd64",
        f"{name}: meeting inference requires Linux amd64 nodes",
    )
    for kind in ("requests", "limits"):
        require(
            str(container.get("resources", {}).get(kind, {}).get("nvidia.com/gpu")) == "1",
            f"{name}: meeting inference requires one GPU",
        )
    expected_environment = {
        "VOICEUP_INFERENCE_MEETING_DIARIZATION_DIR": "/models/diarization",
        "VOICEUP_INFERENCE_MEETING_ASR_DIR": "/models/asr",
        "VOICEUP_INFERENCE_MEETING_DIARIZATION_MANIFEST": "/srv/inference/diarization-model-manifest.json",
        "VOICEUP_INFERENCE_MEETING_ASR_MANIFEST": "/srv/inference/asr-model-manifest.json",
        "HF_HUB_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "PYANNOTE_METRICS_ENABLED": "0",
    }
    for key, value in expected_environment.items():
        require(environment.get(key) == value, f"{name}: meeting environment missing {key}")
    selected_volumes = set()
    for component in ("diarization", "asr"):
        mount = mounts.get(f"/models/{component}", {})
        require(
            mount.get("readOnly") is True and mount.get("subPath") == component,
            f"{name}: {component} model mount must use its read-only source subdirectory",
        )
        selected_volumes.add(mount.get("name"))
    require(
        len(selected_volumes) == 1 and None not in selected_volumes,
        f"{name}: meeting models must share the dedicated volume",
    )
    volume_name = next(iter(selected_volumes))
    volumes = {item.get("name"): item for item in spec.get("volumes", [])}
    claim = volumes.get(volume_name, {}).get("persistentVolumeClaim", {}).get("claimName")
    require(isinstance(claim, str) and bool(claim), f"{name}: meeting model PVC missing")
    claims = [
        item
        for item in documents
        if item.get("kind") == "PersistentVolumeClaim"
        and item.get("metadata", {}).get("name") == claim
    ]
    require(len(claims) == 1, f"{name}: meeting model PVC must be rendered")
    require(
        claims[0].get("spec", {}).get("resources", {}).get("requests", {}).get("storage") == "4Gi",
        f"{name}: meeting model PVC must reserve 4Gi",
    )
    require(not spec.get("initContainers"), f"{name}: runtime model preparation is forbidden")
    for item in containers(spec):
        for mount in item.get("volumeMounts", []):
            if mount.get("name") == volume_name:
                require(mount.get("readOnly") is True, f"{name}: meeting model volume is writable")


def validate_documents(documents: list[dict[str, Any]], allowed_registry: str) -> None:
    require(bool(documents), "no manifests rendered")
    workload_products = {
        str(pod_labels(document).get(PART_OF_LABEL, ""))
        for document in documents
        if document.get("kind") in WORKLOADS
    }
    require(
        "" not in workload_products and len(workload_products) == 1,
        "workloads must share one non-empty part-of product label",
    )
    product = next(iter(workload_products))
    policies: set[str] = set()
    workload_components: set[str] = set()
    names: set[tuple[str, str]] = set()
    registry = allowed_registry.rstrip("/") + "/"
    for document in documents:
        kind = str(document.get("kind", ""))
        name = str(document.get("metadata", {}).get("name", "<unnamed>"))
        require(kind != "Secret", f"{name}: charts may not author Secret resources")
        require(kind not in CLUSTER_SCOPED, f"{name}: cluster-scoped {kind} is forbidden")
        require(kind in SUPPORTED_APIS, f"{name}: unsupported kind {kind}")
        require(
            document.get("apiVersion") == SUPPORTED_APIS[kind],
            f"{name}: unsupported API {document.get('apiVersion')} for {kind}",
        )
        identity = (kind, name)
        require(identity not in names, f"duplicate rendered identity: {kind}/{name}")
        names.add(identity)
        require(not unresolved(document), f"{name}: unresolved value in rendered manifest")
        validate_claims(document, name)

        if kind == "NetworkPolicy":
            spec = document.get("spec", {})
            require(
                set(spec.get("policyTypes", [])) == {"Ingress", "Egress"},
                f"{name}: NetworkPolicy must declare both directions",
            )
            for rule in [*spec.get("ingress", []), *spec.get("egress", [])]:
                for peer in [*rule.get("from", []), *rule.get("to", [])]:
                    require(
                        "ipBlock" not in peer,
                        f"{name}: IP-block network peers are forbidden",
                    )
                    if "podSelector" in peer and "namespaceSelector" not in peer:
                        selector = peer.get("podSelector")
                        require(
                            isinstance(selector, dict)
                            and selector.get("matchLabels", {}).get(PART_OF_LABEL) == product,
                            f"{name}: intra-namespace pod peer must select part-of {product}",
                        )
            component = (
                spec.get("podSelector", {})
                .get("matchLabels", {})
                .get("app.kubernetes.io/component")
            )
            if component:
                policies.add(component)

        if kind == "Service":
            require(
                document.get("spec", {}).get("type", "ClusterIP") == "ClusterIP",
                f"{name}: only ClusterIP Services are allowed",
            )
            require(
                "externalName" not in document.get("spec", {}),
                f"{name}: ExternalName forbidden",
            )

        if kind not in WORKLOADS:
            continue
        spec = pod_spec(document)
        labels = pod_labels(document)
        component = labels.get("app.kubernetes.io/component")
        require(labels.get("app.kubernetes.io/part-of"), f"{name}: missing part-of label")
        require(component, f"{name}: missing component label")
        workload_components.add(component)
        if component == "inference":
            validate_inference_runtime(document, documents)
        require(
            spec.get("automountServiceAccountToken") is False,
            f"{name}: service token mounted",
        )
        pod_security = spec.get("securityContext", {})
        require(pod_security.get("runAsNonRoot") is True, f"{name}: runAsNonRoot missing")
        require(
            isinstance(pod_security.get("runAsUser"), int),
            f"{name}: explicit runAsUser missing",
        )
        require(
            isinstance(pod_security.get("runAsGroup"), int),
            f"{name}: explicit runAsGroup missing",
        )
        require(
            pod_security.get("seccompProfile", {}).get("type") == "RuntimeDefault",
            f"{name}: RuntimeDefault seccomp missing",
        )
        if kind in {"Job", "CronJob"}:
            require(spec.get("restartPolicy") == "Never", f"{name}: Job must restart Never")

        volumes = {volume.get("name"): volume for volume in spec.get("volumes", [])}
        for container in containers(spec):
            cname = container.get("name", "<unnamed>")
            image = str(container.get("image", ""))
            require("@" in image, f"{name}/{cname}: image is not digest-pinned")
            repository, digest = image.rsplit("@", 1)
            require(
                repository.startswith(registry),
                f"{name}/{cname}: image outside approved registry",
            )
            require(
                not any(repository.startswith(item) for item in PUBLIC_REGISTRIES),
                f"{name}/{cname}: public registry",
            )
            require(bool(DIGEST.fullmatch(digest)), f"{name}/{cname}: invalid image digest")
            require(digest != f"sha256:{'0' * 64}", f"{name}/{cname}: zero image digest")
            require(
                container.get("imagePullPolicy", "IfNotPresent") != "Always",
                f"{name}/{cname}: mutable pull policy",
            )
            security = container.get("securityContext", {})
            require(
                security.get("allowPrivilegeEscalation") is False,
                f"{name}/{cname}: privilege escalation allowed",
            )
            require(
                security.get("readOnlyRootFilesystem") is True,
                f"{name}/{cname}: root filesystem is writable",
            )
            require(
                security.get("capabilities", {}).get("drop") == ["ALL"],
                f"{name}/{cname}: capabilities are not dropped",
            )
            resources = container.get("resources", {})
            require(
                resources.get("requests") and resources.get("limits"),
                f"{name}/{cname}: resources missing",
            )
            for mount in container.get("volumeMounts", []):
                volume = volumes.get(mount.get("name"), {})
                if "emptyDir" in volume:
                    require(
                        volume["emptyDir"].get("sizeLimit"),
                        f"{name}/{cname}: unbounded emptyDir",
                    )
                    if mount.get("readOnly") is not True:
                        require(
                            isinstance(pod_security.get("fsGroup"), int),
                            f"{name}/{cname}: writable emptyDir requires fsGroup",
                        )
                        require(
                            pod_security["fsGroup"] == pod_security["runAsGroup"],
                            f"{name}/{cname}: fsGroup must match runAsGroup",
                        )
                        require(
                            pod_security.get("fsGroupChangePolicy") == "OnRootMismatch",
                            f"{name}/{cname}: fsGroupChangePolicy must be OnRootMismatch",
                        )
            if kind in {"Deployment", "StatefulSet"}:
                for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                    require(container.get(probe), f"{name}/{cname}: {probe} missing")

    missing = workload_components - policies
    require(not missing, f"workloads without NetworkPolicy: {', '.join(sorted(missing))}")
    validate_runtime_hosts(documents)


def validate_frontend_assets() -> None:
    frontend = ROOT / "app" / "frontend"
    if not frontend.is_dir():
        return
    for path in frontend.rglob("*"):
        if {"dist", "node_modules"}.intersection(path.relative_to(frontend).parts):
            # Bundled dependencies contain documentation URLs in diagnostic strings. Runtime
            # egress is enforced by the browser harness; this source check targets authored assets.
            continue
        if not path.is_file() or path.suffix not in {
            ".css",
            ".html",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        require(
            not re.search(r"https?://", text, re.IGNORECASE),
            f"{path}: remote frontend asset",
        )
        require(
            not re.search(r"(?:src|href)=[\"']//", text, re.IGNORECASE),
            f"{path}: protocol-relative frontend asset",
        )


def validate_compose_boundary() -> None:
    infra = ROOT / "app" / "infra"
    compose_files = [
        infra / "docker-compose.local.yml",
        infra / "docker-compose.observability.yml",
    ]
    documents = []
    for path in compose_files:
        if not path.is_file():
            continue
        # The policy script also runs in this template repository before init has substituted
        # generator tokens. Their values do not affect the compose boundary being checked here.
        source = re.sub(r"@@[A-Z0-9_]+@@", "generated", path.read_text(encoding="utf-8"))

        def interpolate(match: re.Match[str]) -> str:
            variable, operator, fallback = match.groups()
            if not re.search(r"PASSWORD|TOKEN|SECRET", variable):
                current = os.environ.get(variable)
                if current:
                    return current
            if operator == ":-":
                return fallback
            if operator == ":?":
                return "required-secret"
            return ""

        source = re.sub(r"\$\{([A-Z][A-Z0-9_]*)(?:(:-|:\?)([^}]*))?}", interpolate, source)
        documents.append(yaml.safe_load(source))
    require(bool(documents), "local compose definition missing")
    services: dict[str, Any] = {}
    for document in documents:
        require(isinstance(document, dict), "compose file must be a mapping")
        services.update(document.get("services", {}))
    for name, service in services.items():
        image = service.get("image")
        if image:
            require(
                bool(re.search(r"@sha256:[0-9a-f]{64}\Z", str(image))),
                f"compose/{name}: image is not digest-pinned",
            )
            repository = str(image).split("@", 1)[0]
            registry_host = repository.split("/", 1)[0]
            public_identity = (
                "/" not in repository
                or registry_host in PUBLIC_REGISTRIES
                or "." not in registry_host
                and ":" not in registry_host
            )
            if public_identity:
                require(
                    service.get("pull_policy") == "never",
                    f"compose/{name}: public identity may contact a registry",
                )
        for port in service.get("ports", []):
            require(
                str(port).startswith("127.0.0.1:"),
                f"compose/{name}: host port is not loopback-only",
            )
    networks = documents[0].get("networks", {})
    require(
        networks.get("default", {}).get("internal") is True,
        "compose default network is not internal",
    )
    require("edge" in networks, "compose host-facing edge network is missing")
    edge_services = {
        name for name, service in services.items() if "edge" in (service.get("networks") or [])
    }
    require(
        edge_services <= {"nginx", "grafana"},
        "compose edge network contains an application or data service",
    )
    require("nginx" in edge_services, "compose reverse proxy cannot publish its local port")

    serialized = yaml.safe_dump_all(documents, sort_keys=True)
    allowed_hosts = set(services) | {"localhost", "127.0.0.1"}
    for host in URL_HOST.findall(serialized):
        require(
            host in allowed_hosts,
            f"compose runtime URL points outside local services: {host}",
        )


def signature(documents: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    return sorted(
        (
            str(document.get("apiVersion")),
            str(document.get("kind")),
            str(document.get("metadata", {}).get("name")),
        )
        for document in documents
    )


def expect_rejected(
    label: str,
    documents: list[dict[str, Any]],
    registry: str,
    mutation: Callable[[list[dict[str, Any]]], None],
) -> None:
    changed = copy.deepcopy(documents)
    mutation(changed)
    try:
        validate_documents(changed, registry)
    except PolicyError:
        return
    raise PolicyError(f"self-test failed: {label} mutation was accepted")


def self_test_inference(documents: list[dict[str, Any]], overlay: dict[str, Any]) -> None:
    registry = str(nested(overlay, "global.registry"))

    def deployment(items: list[dict[str, Any]]) -> dict[str, Any]:
        return next(
            item
            for item in items
            if item.get("kind") == "Deployment"
            and pod_labels(item).get("app.kubernetes.io/component") == "inference"
        )

    def main_container(items: list[dict[str, Any]]) -> dict[str, Any]:
        return next(
            item
            for item in pod_spec(deployment(items))["containers"]
            if item["name"] == "inference"
        )

    def asr_mount(items: list[dict[str, Any]]) -> dict[str, Any]:
        return next(
            item
            for item in main_container(items)["volumeMounts"]
            if item["mountPath"] == "/models/asr"
        )

    def remove_mount(items: list[dict[str, Any]]) -> None:
        main_container(items)["volumeMounts"].remove(asr_mount(items))

    def remove_model_claim(items: list[dict[str, Any]]) -> None:
        volume_name = asr_mount(items)["name"]
        volume = next(
            item for item in pod_spec(deployment(items))["volumes"] if item["name"] == volume_name
        )
        claim_name = volume["persistentVolumeClaim"]["claimName"]
        items.remove(
            next(
                item
                for item in items
                if item["kind"] == "PersistentVolumeClaim"
                and item["metadata"]["name"] == claim_name
            )
        )

    def mismatched_enable(items: list[dict[str, Any]]) -> None:
        next(
            item
            for item in main_container(items)["env"]
            if item["name"] == "VOICEUP_INFERENCE_MEETING_ENABLED"
        )["value"] = "false"

    mutations: list[tuple[str, Callable[[list[dict[str, Any]]], None]]] = [
        (
            "meeting pilot readiness",
            lambda items: main_container(items)["readinessProbe"]["httpGet"].__setitem__(
                "path", "/ready"
            ),
        ),
        (
            "meeting pilot startup",
            lambda items: main_container(items)["startupProbe"]["httpGet"].__setitem__(
                "path", "/live"
            ),
        ),
        ("meeting model mount missing", remove_mount),
        ("meeting model writable", lambda items: asr_mount(items).__setitem__("readOnly", False)),
        (
            "meeting model subdirectory",
            lambda items: asr_mount(items).__setitem__("subPath", "diarization"),
        ),
        (
            "meeting wrong architecture",
            lambda items: pod_spec(deployment(items))["nodeSelector"].__setitem__(
                "kubernetes.io/arch", "arm64"
            ),
        ),
        (
            "meeting runtime profile",
            lambda items: deployment(items)["spec"]["template"]["metadata"][
                "annotations"
            ].__setitem__("voiceup.internal/runtime-profile", "aarch64-cu129"),
        ),
        ("meeting model claim missing", remove_model_claim),
        ("meeting environment mismatch", mismatched_enable),
    ]
    for label, mutation in mutations:
        expect_rejected(label, documents, registry, mutation)

    for selection in (
        {"runtimeProfile": "aarch64-cu129", "meetingEnabled": True},
        {"runtimeProfile": "unknown", "meetingEnabled": False},
        {"runtimeProfile": "x86_64-cu128", "meetingEnabled": "false"},
        {"runtimeProfile": "x86_64-cu128"},
    ):
        changed = copy.deepcopy(overlay)
        changed["inference"] = selection
        try:
            validate_overlay("self-test", changed)
        except PolicyError:
            continue
        raise PolicyError("self-test failed: invalid inference selection was accepted")


def self_test(documents: list[dict[str, Any]], overlay: dict[str, Any]) -> None:
    registry = str(nested(overlay, "global.registry"))

    def first_workload(items: list[dict[str, Any]]) -> dict[str, Any]:
        return next(item for item in items if item.get("kind") in WORKLOADS)

    def first_container(items: list[dict[str, Any]]) -> dict[str, Any]:
        return next(iter(containers(pod_spec(first_workload(items)))))

    def first_intra_namespace_peer(items: list[dict[str, Any]]) -> dict[str, Any]:
        for item in items:
            if item.get("kind") != "NetworkPolicy":
                continue
            spec = item.get("spec", {})
            for rule in [*spec.get("ingress", []), *spec.get("egress", [])]:
                for peer in [*rule.get("from", []), *rule.get("to", [])]:
                    if "podSelector" in peer and "namespaceSelector" not in peer:
                        return peer
        raise PolicyError("self-test fixture has no intra-namespace pod peer")

    mutations: list[tuple[str, Callable[[list[dict[str, Any]]], None]]] = [
        (
            "tag-only image",
            lambda items: first_container(items).__setitem__(
                "image", f"{registry}/app/backend:latest"
            ),
        ),
        (
            "public image",
            lambda items: first_container(items).__setitem__(
                "image", f"docker.io/app/backend@sha256:{'1' * 64}"
            ),
        ),
        (
            "zero digest",
            lambda items: first_container(items).__setitem__(
                "image", f"{registry}/app/backend@sha256:{'0' * 64}"
            ),
        ),
        (
            "root pod",
            lambda items: pod_spec(first_workload(items))["securityContext"].__setitem__(
                "runAsNonRoot", False
            ),
        ),
        (
            "missing user",
            lambda items: pod_spec(first_workload(items))["securityContext"].pop("runAsUser"),
        ),
        (
            "missing group",
            lambda items: pod_spec(first_workload(items))["securityContext"].pop("runAsGroup"),
        ),
        (
            "missing filesystem group",
            lambda items: pod_spec(first_workload(items))["securityContext"].pop("fsGroup"),
        ),
        (
            "mismatched filesystem group",
            lambda items: pod_spec(first_workload(items))["securityContext"].__setitem__(
                "fsGroup", 4242
            ),
        ),
        (
            "missing filesystem group policy",
            lambda items: pod_spec(first_workload(items))["securityContext"].pop(
                "fsGroupChangePolicy"
            ),
        ),
        (
            "service token",
            lambda items: pod_spec(first_workload(items)).__setitem__(
                "automountServiceAccountToken", True
            ),
        ),
        (
            "missing seccomp",
            lambda items: pod_spec(first_workload(items))["securityContext"].pop("seccompProfile"),
        ),
        (
            "privilege escalation",
            lambda items: first_container(items)["securityContext"].__setitem__(
                "allowPrivilegeEscalation", True
            ),
        ),
        (
            "writable root",
            lambda items: first_container(items)["securityContext"].__setitem__(
                "readOnlyRootFilesystem", False
            ),
        ),
        (
            "capabilities",
            lambda items: first_container(items)["securityContext"]["capabilities"].__setitem__(
                "drop", []
            ),
        ),
        (
            "resources",
            lambda items: first_container(items).__setitem__("resources", {}),
        ),
        (
            "mutable pull",
            lambda items: first_container(items).__setitem__("imagePullPolicy", "Always"),
        ),
        ("probe", lambda items: first_container(items).pop("readinessProbe")),
        (
            "identity label",
            lambda items: pod_labels(first_workload(items)).pop("app.kubernetes.io/part-of"),
        ),
        (
            "network direction",
            lambda items: next(item for item in items if item.get("kind") == "NetworkPolicy")[
                "spec"
            ].__setitem__("policyTypes", ["Ingress"]),
        ),
        (
            "cross-product network peer",
            lambda items: first_intra_namespace_peer(items)["podSelector"]["matchLabels"].pop(
                PART_OF_LABEL
            ),
        ),
        (
            "node port",
            lambda items: next(item for item in items if item.get("kind") == "Service")[
                "spec"
            ].__setitem__("type", "NodePort"),
        ),
        (
            "deprecated API",
            lambda items: first_workload(items).__setitem__("apiVersion", "extensions/v1beta1"),
        ),
    ]
    for label, mutation in mutations:
        expect_rejected(label, documents, registry, mutation)

    def remove_policy(items: list[dict[str, Any]]) -> None:
        items.remove(next(item for item in items if item.get("kind") == "NetworkPolicy"))

    def add_secret(items: list[dict[str, Any]]) -> None:
        items.append({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "forbidden"}})

    def add_cluster_role(items: list[dict[str, Any]]) -> None:
        items.append(
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRole",
                "metadata": {"name": "forbidden"},
            }
        )

    def job_restarts(items: list[dict[str, Any]]) -> None:
        job = next(item for item in items if item.get("kind") in {"Job", "CronJob"})
        pod_spec(job)["restartPolicy"] = "Always"

    def unbounded_empty_dir(items: list[dict[str, Any]]) -> None:
        workload = first_workload(items)
        volume = next(volume for volume in pod_spec(workload)["volumes"] if "emptyDir" in volume)
        volume["emptyDir"].pop("sizeLimit")

    def claim_without_size(items: list[dict[str, Any]]) -> None:
        stateful = next(item for item in items if item.get("kind") == "StatefulSet")
        stateful["spec"]["volumeClaimTemplates"][0]["spec"]["resources"]["requests"].pop("storage")

    def external_name(items: list[dict[str, Any]]) -> None:
        service = next(item for item in items if item.get("kind") == "Service")
        service["spec"]["externalName"] = "external.example.com"

    def ip_block(items: list[dict[str, Any]]) -> None:
        policy = next(item for item in items if item.get("kind") == "NetworkPolicy")
        policy["spec"]["egress"][0]["to"] = [{"ipBlock": {"cidr": "0.0.0.0/0"}}]

    def add_endpoint(items: list[dict[str, Any]], endpoint: str) -> None:
        items.append(
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": f"endpoint-{len(items)}"},
                "data": {"collector.yaml": f"endpoint: {endpoint}"},
            }
        )

    expect_rejected("missing NetworkPolicy", documents, registry, remove_policy)
    expect_rejected("chart-authored Secret", documents, registry, add_secret)
    expect_rejected("cluster scope", documents, registry, add_cluster_role)
    expect_rejected("Job restart", documents, registry, job_restarts)
    expect_rejected("unbounded emptyDir", documents, registry, unbounded_empty_dir)
    expect_rejected("claim size", documents, registry, claim_without_size)
    expect_rejected("ExternalName", documents, registry, external_name)
    expect_rejected("IP block", documents, registry, ip_block)
    expect_rejected(
        "external telemetry",
        documents,
        registry,
        lambda items: add_endpoint(items, "https://telemetry.example.com/v1"),
    )
    expect_rejected(
        "missing in-cluster Service",
        documents,
        registry,
        lambda items: add_endpoint(items, "http://missing-service:4317"),
    )

    unsafe_overlay = copy.deepcopy(overlay)
    unsafe_overlay["grafanaPassword"] = "forbidden"
    try:
        validate_overlay("self-test", unsafe_overlay)
    except PolicyError:
        pass
    else:
        raise PolicyError("self-test failed: overlay secret material was accepted")

    for label, revision in (
        ("abbreviated source revision", "deadbeef"),
        ("uppercase source revision", "A" * 40),
        ("zero source revision", "0" * 40),
        ("unresolved source revision", "__REQUIRED_SOURCE_REVISION__"),
    ):
        changed_overlay = copy.deepcopy(overlay)
        changed_overlay["global"]["sourceRevision"] = revision
        try:
            validate_overlay("self-test", changed_overlay)
        except PolicyError:
            pass
        else:
            raise PolicyError(f"self-test failed: {label} was accepted")

    current_revision = str(nested(overlay, "global.sourceRevision"))
    current_job = next(
        item
        for item in documents
        if item.get("kind") == "Job"
        and item.get("metadata", {}).get("labels", {}).get("app.kubernetes.io/component")
        == "migrate"
    )
    current_name = str(current_job.get("metadata", {}).get("name", ""))
    require(
        current_name.endswith(f"-{revision_identity(current_revision)}"),
        "migration Job name does not carry the source revision",
    )
    require(
        current_job.get("metadata", {})
        .get("annotations", {})
        .get("scaffold.kt.internal/source-revision")
        == current_revision,
        "migration Job annotation does not carry the full source revision",
    )
    changed_overlay = copy.deepcopy(overlay)
    changed_revision = f"{current_revision[:-1]}0"
    if changed_revision == current_revision:
        changed_revision = f"{current_revision[:-1]}1"
    changed_overlay["global"]["sourceRevision"] = changed_revision
    with tempfile.TemporaryDirectory(prefix="chart-values-") as directory:
        changed_documents = render_chart(CHARTS / "app-migrate", changed_overlay, Path(directory))
    changed_job = next(item for item in changed_documents if item.get("kind") == "Job")
    changed_name = str(changed_job.get("metadata", {}).get("name", ""))
    require(
        changed_name != current_name
        and changed_name.endswith(f"-{revision_identity(changed_revision)}"),
        "migration Job name did not change with the source revision",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-ready", choices=["lab", "cluster"])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        validate_frontend_assets()
        validate_compose_boundary()
        if args.environment_ready:
            overlay = load_overlay(ENVIRONMENTS, args.environment_ready)
            validate_overlay(args.environment_ready, overlay)
            documents = render(overlay)
            validate_documents(documents, str(nested(overlay, "global.registry")))
            print(f"environment ready: {args.environment_ready} ({len(documents)} resources)")
            return 0

        rendered: dict[str, list[dict[str, Any]]] = {}
        meeting_rendered: dict[str, list[dict[str, Any]]] = {}
        overlays: dict[str, dict[str, Any]] = {}
        for name in ("lab", "cluster"):
            overlay = load_overlay(FIXTURES, name)
            validate_overlay(f"fixture/{name}", overlay)
            documents = render(overlay)
            validate_documents(documents, str(nested(overlay, "global.registry")))
            rendered[name] = documents
            overlays[name] = overlay
            meeting_overlay = copy.deepcopy(overlay)
            meeting_overlay["inference"] = {
                "runtimeProfile": "x86_64-cu128",
                "meetingEnabled": True,
            }
            validate_overlay(f"fixture/{name}/meeting", meeting_overlay)
            meeting_documents = render(meeting_overlay)
            validate_documents(meeting_documents, str(nested(meeting_overlay, "global.registry")))
            meeting_rendered[name] = meeting_documents
        require(
            signature(rendered["lab"]) == signature(rendered["cluster"]),
            "overlay release shapes differ",
        )
        require(
            signature(meeting_rendered["lab"]) == signature(meeting_rendered["cluster"]),
            "meeting overlay release shapes differ",
        )
        if args.self_test:
            self_test(rendered["lab"], overlays["lab"])
            self_test_inference(meeting_rendered["lab"], overlays["lab"])
        print(
            "chart contract passed: "
            f"{len(rendered['lab'])} resources x {len(rendered)} fixture overlays"
        )
        print(
            "meeting chart contract passed: "
            f"{len(meeting_rendered['lab'])} resources x {len(meeting_rendered)} fixture overlays"
        )
        return 0
    except PolicyError as exc:
        print(f"chart contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
