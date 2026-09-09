"""Focused regressions for generated migration, schema, browser, and network contracts."""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from kt_scaffold.models import Answers
from kt_scaffold.operations import (
    backend_domain_new_operation,
    browser_scenario_new_operation,
    frontend_page_new_operation,
    init_operation,
    spec_new_operation,
)


def _accepted_spec(target: Path, capability: str) -> str:
    created = spec_new_operation(
        domain="payments",
        capability=capability,
        intent=f"Deliver accepted {capability} behavior inside the active tenant.",
        target_dir=str(target),
    )
    relative = str(created["spec_path"])
    path = target / relative
    path.write_text(
        path.read_text(encoding="utf-8").replace("Status: Draft", "Status: Accepted", 1),
        encoding="utf-8",
    )
    return relative


def test_long_python_domain_names_are_generated_formatter_ready(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    answers = answers_factory(
        backend_profile="python-fastapi",
        persistence_profile="sqlalchemy-alembic",
    )
    init_operation(str(target), **answers.model_dump(mode="json"))

    capabilities = (
        "exceptionally-long-high-value-payment-review",
        "another-extraordinarily-long-financial-investigation-review",
    )
    for capability in capabilities:
        spec_path = _accepted_spec(target, capability)
        first = backend_domain_new_operation(spec_path, target_dir=str(target))
        second = backend_domain_new_operation(spec_path, target_dir=str(target))
        assert first["ok"] is True
        assert all(change["action"] == "skip" for change in second["changes"])

    backend = target / "app/backend"
    for path in (*backend.joinpath("app").rglob("*.py"), *backend.joinpath("tests").rglob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    first_router = backend.joinpath(
        "app/api/exceptionally_long_high_value_payment_review/router.py"
    ).read_text(encoding="utf-8")
    second_router = backend.joinpath(
        "app/api/another_extraordinarily_long_financial_investigation_review/router.py"
    ).read_text(encoding="utf-8")
    second_service = backend.joinpath(
        "app/services/another_extraordinarily_long_financial_investigation_review_service.py"
    ).read_text(encoding="utf-8")
    assert (
        "        ExceptionallyLongHighValuePaymentReviewResponse.model_validate(record) "
        "for record in records"
    ) in first_router
    assert "    dependencies=[\n        Depends(\n" in second_router
    assert (
        "        self.repository = (\n"
        "            repository or "
        "AnotherExtraordinarilyLongFinancialInvestigationReviewRepository()\n"
        "        )" in second_service
    )


def test_generated_backend_is_a_tenant_safe_database_backed_vertical(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    answers = answers_factory()
    init_operation(str(target), **answers.model_dump(mode="json"))
    spec_path = _accepted_spec(target, "payment-review")

    result = backend_domain_new_operation(spec_path, target_dir=str(target))

    assert result["ok"] is True
    repository = (
        target / "app/backend/app/infrastructure/repositories/payment_review_repository.py"
    ).read_text(encoding="utf-8")
    service = (target / "app/backend/app/services/payment_review_service.py").read_text(
        encoding="utf-8"
    )
    router = (target / "app/backend/app/api/payment_review/router.py").read_text(encoding="utf-8")
    generated_test = (target / "app/backend/tests/domain/test_payment_review.py").read_text(
        encoding="utf-8"
    )

    assert "select(PaymentReview)" in repository
    assert "PaymentReview.is_deleted.is_(False)" in repository
    assert "Tenant.public_id == tenant_public_id" in repository
    assert "Tenant.is_deleted.is_(False)" in repository
    assert "Tenant.is_active.is_(True)" in repository
    assert "if tenant_public_id is None" in repository
    assert "return await self.repository.list_active" in service
    assert 'Depends(require_permission("payment_review:read"))' in router
    assert "response_model=list[PaymentReviewResponse]" in router
    assert "session.scalars.assert_not_awaited()" in generated_test
    assert 'assert "JOIN tenant" in sql' in generated_test
    assert "test_service_returns_repository_records_for_active_tenant" in generated_test


def test_generated_frontend_loads_and_renders_the_capability_vertical(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    init_operation(str(target), **answers_factory().model_dump(mode="json"))
    spec_path = _accepted_spec(target, "payment-review")

    first = frontend_page_new_operation(
        spec_path,
        page="payment-review",
        route="/payment-review",
        target_dir=str(target),
    )
    second = frontend_page_new_operation(
        spec_path,
        page="payment-review",
        route="/payment-review",
        target_dir=str(target),
    )
    service = (target / "app/frontend/src/services/payment-review.ts").read_text(encoding="utf-8")
    page = (target / "app/frontend/src/pages/PaymentReviewPage.tsx").read_text(encoding="utf-8")
    page_test = (target / "app/frontend/src/pages/PaymentReviewPage.test.tsx").read_text(
        encoding="utf-8"
    )
    service_test = (target / "app/frontend/src/services/payment-review.test.ts").read_text(
        encoding="utf-8"
    )
    routes = (target / "app/frontend/src/generated/routes.tsx").read_text(encoding="utf-8")

    assert first["ok"] is True
    assert first["endpoint"] == "/payment-review"
    assert first["permission"] == "payment_review:read"
    assert all(change["action"] == "skip" for change in second["changes"])
    assert "apiRequest<PaymentReviewRecord[]>(PAYMENT_REVIEW_ENDPOINT)" in service
    assert "endpoint = undefined" not in service
    assert "PaymentReviewService.listActive()" in page
    states = ('status: "loading"', 'status: "ready"', 'status: "error"')
    assert all(state in page for state in states)
    assert "state.records.map" in page
    assert "render(" in page_test
    assert 'vi.spyOn(PaymentReviewService, "listActive")' in page_test
    assert "fetchMock" in service_test
    assert '<PermissionRoute permission="payment_review:read">' in routes
    assert len(first["locale_keys_added"]) == 8


def test_generated_browser_scenario_fails_closed_until_assertions_exist(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    init_operation(str(target), **answers_factory().model_dump(mode="json"))
    spec_path = _accepted_spec(target, "manual-payment-approval")
    acceptance_points = [
        "An authorized reviewer sees the pending payment.",
        "An unauthorized reviewer cannot approve the payment.",
    ]

    result = browser_scenario_new_operation(
        spec_path,
        suite="payments",
        scenario_title="Review pending payment",
        acceptance_points=acceptance_points,
        target_dir=str(target),
    )
    scenario = (target / str(result["scenario_path"])).read_text(encoding="utf-8")
    pending = "Implement executable assertions for: " + "; ".join(acceptance_points)

    assert result["ok"] is True
    assert result["executable_assertions_required"] is True
    assert all(f"// Acceptance: {point}" in scenario for point in acceptance_points)
    assert f"throw new Error({json.dumps(pending)});" in scenario
    assert "await page." not in scenario
    assert re.search(r"\bexpect\s*\(", scenario) is None
    assert scenario.index("// Acceptance:") < scenario.index("throw new Error")


@pytest.mark.parametrize("observability", [False, True])
def test_runtime_network_boundary_only_publishes_edge_services(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    observability: bool,
) -> None:
    target = tmp_path / "project"
    answers = answers_factory(observability=observability)
    init_operation(str(target), **answers.model_dump(mode="json"))

    infra = target / "app/infra"
    base = yaml.safe_load((infra / "docker-compose.local.yml").read_text(encoding="utf-8"))
    services: dict[str, dict[str, Any]] = dict(base["services"])
    overlay_path = infra / "docker-compose.observability.yml"
    if observability:
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        services.update(overlay["services"])
    else:
        assert not overlay_path.exists()

    edge_services = {
        name for name, service in services.items() if "edge" in service.get("networks", [])
    }
    published_services = {name for name, service in services.items() if service.get("ports")}
    expected_edge = {"nginx", "grafana"} if observability else {"nginx"}

    assert base["networks"]["default"]["internal"] is True
    assert base["networks"]["edge"] == {"driver": "bridge"}
    assert edge_services == expected_edge
    assert published_services == expected_edge
    assert {"backend", "frontend", "postgres", "redis"}.isdisjoint(edge_services)
    for name in published_services:
        assert all(str(port).startswith("127.0.0.1:") for port in services[name]["ports"])
        assert services[name]["dns"] == ["127.0.0.1"]


def test_observability_persistent_state_uses_image_owned_non_root_paths(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    init_operation(
        str(target),
        **answers_factory(observability=True).model_dump(mode="json"),
    )

    compose = yaml.safe_load(
        (target / "app/infra/docker-compose.observability.yml").read_text(encoding="utf-8")
    )
    services = compose["services"]
    assert "observability-volume-init" not in services
    assert "loki_data:/loki" in services["loki"]["volumes"]
    assert "tempo_data:/var/tempo" in services["tempo"]["volumes"]

    for service_name in ("loki", "tempo"):
        service = services[service_name]
        assert service["user"] == "10001:10001"
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]

    observability = target / "app/infra/observability"
    loki_config = (observability / "loki.yaml").read_text(encoding="utf-8")
    tempo_config = (observability / "tempo.yaml").read_text(encoding="utf-8")
    assert "path_prefix: /loki" in loki_config
    assert "chunks_directory: /loki/chunks" in loki_config
    assert "rules_directory: /loki/rules" in loki_config
    assert "path: /var/tempo/traces" in tempo_config

    chart = target / "app/devops/charts/app-observability/templates"
    deployment = (chart / "deployment.yaml").read_text(encoding="utf-8")
    configmap = (chart / "configmap.yaml").read_text(encoding="utf-8")
    assert deployment.count("fsGroupChangePolicy: OnRootMismatch") == 5
    assert "{name: data, mountPath: /loki}" in deployment
    assert "{name: data, mountPath: /var/tempo}" in deployment
    assert "path_prefix: /loki" in configmap
    assert "local: {path: /var/tempo/traces}" in configmap
