"""Regressions for immutable migration releases and namespace-local peer isolation."""

from __future__ import annotations

import copy
import runpy
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPOSITORY_ROOT / "src/kt_scaffold/templates/common/scripts/render_charts.py"
CONTRACT: dict[str, Any] = runpy.run_path(str(CONTRACT_PATH))


def _fixture_overlay() -> dict[str, Any]:
    return CONTRACT["load_overlay"](CONTRACT["FIXTURES"], "lab")


@pytest.mark.parametrize("environment", ["lab", "cluster"])
def test_real_environment_overlay_requires_a_source_revision(environment: str) -> None:
    overlay = CONTRACT["load_overlay"](CONTRACT["ENVIRONMENTS"], environment)

    assert overlay["global"]["sourceRevision"] == "__REQUIRED_SOURCE_REVISION__"
    with pytest.raises(CONTRACT["PolicyError"], match="unresolved environment facts"):
        CONTRACT["validate_overlay"](environment, overlay)


@pytest.mark.parametrize(
    "revision",
    ["", "deadbeef", "A" * 40, "0" * 40, "__REQUIRED_SOURCE_REVISION__"],
)
def test_source_revision_is_required_full_lowercase_and_nonzero(revision: str) -> None:
    overlay = _fixture_overlay()
    overlay["global"]["sourceRevision"] = revision

    with pytest.raises(CONTRACT["PolicyError"]):
        CONTRACT["validate_overlay"]("fixture", overlay)


@pytest.mark.parametrize("length", [40, 64])
def test_source_revision_is_propagated_to_migration_chart_values(length: int) -> None:
    overlay = _fixture_overlay()
    revision = "c" * length
    overlay["global"]["sourceRevision"] = revision

    CONTRACT["validate_overlay"]("fixture", overlay)

    assert CONTRACT["chart_values"]("app-migrate", overlay)["revision"] == revision
    job = (
        REPOSITORY_ROOT
        / "src/kt_scaffold/templates/common/app/devops/charts/app-migrate/templates/job.yaml"
    ).read_text(encoding="utf-8")
    assert "sha256sum $revision | trunc 12" in job
    assert "scaffold.kt.internal/source-revision" in job
    assert "revision must not be the all-zero source hash" in job


def _minimal_release() -> list[dict[str, Any]]:
    product = "ledger"
    digest = "1" * 64
    return [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "backend"},
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {
                            "app.kubernetes.io/part-of": product,
                            "app.kubernetes.io/component": "backend",
                        }
                    },
                    "spec": {
                        "automountServiceAccountToken": False,
                        "securityContext": {
                            "runAsNonRoot": True,
                            "runAsUser": 10001,
                            "runAsGroup": 10001,
                            "fsGroup": 10001,
                            "fsGroupChangePolicy": "OnRootMismatch",
                            "seccompProfile": {"type": "RuntimeDefault"},
                        },
                        "containers": [
                            {
                                "name": "backend",
                                "image": (
                                    f"registry.internal.invalid/ledger/app/backend@sha256:{digest}"
                                ),
                                "imagePullPolicy": "IfNotPresent",
                                "securityContext": {
                                    "allowPrivilegeEscalation": False,
                                    "readOnlyRootFilesystem": True,
                                    "capabilities": {"drop": ["ALL"]},
                                },
                                "volumeMounts": [
                                    {"name": "scratch", "mountPath": "/workspace-cache"}
                                ],
                                "resources": {
                                    "requests": {"cpu": "10m", "memory": "16Mi"},
                                    "limits": {"cpu": "100m", "memory": "64Mi"},
                                },
                                "startupProbe": {"httpGet": {"path": "/", "port": 8000}},
                                "readinessProbe": {"httpGet": {"path": "/", "port": 8000}},
                                "livenessProbe": {"httpGet": {"path": "/", "port": 8000}},
                            }
                        ],
                        "volumes": [{"name": "scratch", "emptyDir": {"sizeLimit": "16Mi"}}],
                    },
                }
            },
        },
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "backend"},
            "spec": {
                "podSelector": {
                    "matchLabels": {
                        "app.kubernetes.io/part-of": product,
                        "app.kubernetes.io/component": "backend",
                    }
                },
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [],
                "egress": [
                    {
                        "to": [
                            {
                                "podSelector": {
                                    "matchLabels": {
                                        "app.kubernetes.io/part-of": product,
                                        "app.kubernetes.io/component": "backend",
                                    }
                                }
                            }
                        ]
                    }
                ],
            },
        },
    ]


def test_intra_namespace_peer_requires_the_same_product_label() -> None:
    documents = _minimal_release()
    CONTRACT["validate_documents"](documents, "registry.internal.invalid/ledger")

    changed = copy.deepcopy(documents)
    peer_labels = changed[1]["spec"]["egress"][0]["to"][0]["podSelector"]["matchLabels"]
    peer_labels.pop("app.kubernetes.io/part-of")

    with pytest.raises(CONTRACT["PolicyError"], match="intra-namespace pod peer"):
        CONTRACT["validate_documents"](
            changed,
            "registry.internal.invalid/ledger",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("fsGroup", None, "writable emptyDir requires fsGroup"),
        ("fsGroup", 4242, "fsGroup must match runAsGroup"),
        (
            "fsGroupChangePolicy",
            None,
            "fsGroupChangePolicy must be OnRootMismatch",
        ),
    ],
)
def test_writable_emptydir_requires_a_matching_filesystem_group(
    field: str,
    value: object,
    message: str,
) -> None:
    documents = _minimal_release()
    security = documents[0]["spec"]["template"]["spec"]["securityContext"]
    if value is None:
        security.pop(field)
    else:
        security[field] = value

    with pytest.raises(CONTRACT["PolicyError"], match=message):
        CONTRACT["validate_documents"](
            documents,
            "registry.internal.invalid/ledger",
        )


def test_namespace_scoped_external_peer_does_not_require_product_label() -> None:
    documents = _minimal_release()
    documents[1]["spec"]["ingress"] = [
        {
            "from": [
                {
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": "ingress-nginx"}
                    },
                    "podSelector": {"matchLabels": {"app.kubernetes.io/name": "ingress-nginx"}},
                }
            ]
        }
    ]

    CONTRACT["validate_documents"](documents, "registry.internal.invalid/ledger")
