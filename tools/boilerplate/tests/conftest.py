"""Shared fixtures for generator contract tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from kt_scaffold.models import Answers


@pytest.fixture
def answers_factory() -> Callable[..., Answers]:
    """Return complete, non-secret answers with a collision-resistant test prefix."""

    def build(**overrides: object) -> Answers:
        payload: dict[str, object] = {
            "project_intent": (
                "Build an offline internal banking control surface with auditable workflows."
            ),
            "primary_domain": "payments",
            "product_name": "Internal Control Surface",
            "product_slug": "ledger",
            "backend_profile": "python-fastapi",
            "persistence_profile": "sqlalchemy-alembic",
            "env_prefix": "ZZSCF_",
            "api_prefix": "/api/ledger/v1",
            "locales": ["en", "tr"],
        }
        payload.update(overrides)
        return Answers.model_validate(payload)

    return build
