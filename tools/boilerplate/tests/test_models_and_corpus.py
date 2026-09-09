"""Canonical answer and rule-corpus contracts."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from kt_scaffold.corpus import CorpusError, generator_corpus_dir, load_rules, validate_corpus
from kt_scaffold.models import Answers
from kt_scaffold.technology import TechnologyProfile, load_technology_profile


def test_canonical_corpus_is_complete_unique_and_deterministic() -> None:
    root = generator_corpus_dir()
    report = validate_corpus(root)
    first = load_rules(root)
    second = load_rules(root)

    assert report["ok"] is True
    assert report["count"] == 33
    assert report["ids"] == [rule.id for rule in first]
    assert [rule.id for rule in first] == [rule.id for rule in second]
    assert len({rule.id for rule in first}) == len(first)
    assert {rule.trigger for rule in first} == {"always", "path-match", "on-demand"}
    assert all(rule.body.strip() for rule in first)
    assert all(rule.applies_to for rule in first if rule.trigger == "path-match")


def test_corpus_rejects_duplicate_normalized_bodies(tmp_path: Path) -> None:
    template = (
        "---\n"
        "id: {rule_id}\n"
        "title: {title}\n"
        "scope: governance\n"
        "priority: {priority}\n"
        "trigger: always\n"
        "applies_to: []\n"
        "gate: governance-drift.yml\n"
        "---\n"
        "The same canonical requirement.\n"
    )
    (tmp_path / "00-first.md").write_text(
        template.format(rule_id="00-first", title="First rule title", priority=0),
        encoding="utf-8",
    )
    (tmp_path / "01-second.md").write_text(
        template.format(rule_id="01-second", title="Second rule title", priority=1),
        encoding="utf-8",
    )

    with pytest.raises(CorpusError, match="duplicate normalized body"):
        load_rules(tmp_path)


def test_canonical_corpus_rejects_project_owned_authority(tmp_path: Path) -> None:
    (tmp_path / "00-local.md").write_text(
        """---
id: 00-local
title: Preserve locally owned policy
scope: governance
authority: project-owned
priority: 0
trigger: always
applies_to: []
gate: review
---
This content belongs to one project.
""",
        encoding="utf-8",
    )
    with pytest.raises(CorpusError, match="cannot own project-owned"):
        load_rules(tmp_path)


def test_answers_use_the_fixed_python_technology_profile() -> None:
    answers = Answers(
        project_intent="Create an internal and offline payment assurance application.",
        primary_domain="payment-assurance",
        product_slug="control-plane",
        backend_profile="python-fastapi",
        locales=["EN", "tr", "en"],
    )
    assert answers.backend_profile == "python-fastapi"
    assert answers.persistence_profile == "sqlalchemy-alembic"
    assert answers.env_prefix == "CONTROL_PLANE_"
    assert answers.api_prefix == "/api/control-plane/v1"
    assert answers.locales == ["en", "tr"]


def test_technology_profile_rejects_unknown_or_misspelled_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    profile = load_technology_profile(root / "technology-profile.yml")
    payload = profile.model_dump(by_alias=True)
    payload["frontend"]["type_checkr"] = payload["frontend"].pop("type_checker")
    with pytest.raises(ValidationError, match="type_checker|type_checkr"):
        TechnologyProfile.model_validate(payload)


def test_technology_profile_rejects_vector_policy_drift() -> None:
    root = Path(__file__).resolve().parents[1]
    profile = load_technology_profile(root / "technology-profile.yml")
    payload = profile.model_dump(by_alias=True)
    payload["persistence"]["vector"]["search_modes"] = ["hnsw", "exact", "ivfflat"]

    with pytest.raises(ValidationError, match="fixed ordered set"):
        TechnologyProfile.model_validate(payload)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"primary_domain": "Payment Domain"}, "lowercase hyphenated slug"),
        ({"tenant_header": "X Tenant"}, "lowercase HTTP header"),
        ({"env_prefix": "lower_"}, "uppercase alphanumeric"),
        ({"api_prefix": "/api/../escape"}, "parent segments"),
        (
            {"generator_version": '0.1.0"; touch /tmp/not-allowed; #'},
            "valid semantic version",
        ),
        (
            {"persistence_profile": "prisma"},
            "Input should be 'sqlalchemy-alembic'",
        ),
        (
            {"backend_profile": "node-nestjs"},
            "Input should be 'python-fastapi'",
        ),
        ({"locales": ["english"]}, "unsupported locale shape"),
    ],
)
def test_answers_reject_unsafe_or_incoherent_values(
    answers_factory: Callable[..., Answers],
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        answers_factory(**overrides)


@pytest.mark.parametrize("secret_key", ["password", "token", "api_key", "jwt_secret"])
def test_answers_never_accept_persisted_secrets(secret_key: str) -> None:
    payload = {
        "project_intent": "Create an internal and offline payment assurance application.",
        "primary_domain": "payments",
        secret_key: "must-not-be-stored",
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Answers.model_validate(payload)
