"""Executable selectors named by the architecture plan's acceptance matrix."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import yaml

from kt_scaffold import __version__
from kt_scaffold.corpus import load_rules
from kt_scaffold.models import Answers
from kt_scaffold.operations import done_report_operation
from kt_scaffold.project import project_init
from kt_scaffold.render import COMMANDS, TURKISH_COMMANDS
from kt_scaffold.report import report_skeleton, validate_report
from kt_scaffold.technology import load_technology_profile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _project(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    **overrides: object,
) -> Path:
    target = tmp_path / "project"
    project_init(target, answers_factory(**overrides))
    return target


def test_machine_readable_technology_profile_is_fixed_and_template_identical() -> None:
    root_profile = REPOSITORY_ROOT / "technology-profile.yml"
    template_profile = REPOSITORY_ROOT / "src/kt_scaffold/templates/common/technology-profile.yml"

    assert root_profile.read_bytes() == template_profile.read_bytes()
    profile = yaml.safe_load(root_profile.read_text(encoding="utf-8"))
    validated = load_technology_profile(root_profile)
    assert validated.profile_id == "kt-vibecoding-python-web-v2"
    assert validated.schema_version == 2
    assert profile["architecture"]["server_side_rendering"] == "forbidden"
    assert profile["architecture"]["nextjs"] == "forbidden"
    assert profile["architecture"]["realtime"]["server_sent_events"] == "allowed"
    assert profile["backend"]["framework"] == "fastapi"
    assert profile["persistence"]["migrations"] == "alembic"
    assert profile["persistence"]["vector"] == {
        "status": "allowed-with-accepted-prd",
        "database": "same-postgresql-database",
        "extension": "pgvector",
        "sql_extension_name": "vector",
        "minimum_version": "0.8.5",
        "python_binding": "pgvector-python-sqlalchemy",
        "activation": "reviewed-alembic-migration",
        "alternative_vector_database": "forbidden",
        "data_type": "vector-with-fixed-dimensions",
        "distance_metrics": ["cosine", "inner-product", "l2"],
        "search_modes": ["exact", "hnsw", "ivfflat"],
    }
    assert profile["embeddings"]["provider"] == "approved-internal-or-on-premise"
    assert profile["embeddings"]["runtime_egress"] == "forbidden"
    assert profile["embeddings"]["storage"]["tenant_scope"] == ("required-in-similarity-query")
    assert profile["embeddings"]["lifecycle"]["mixed_model_search"] == "forbidden"
    assert profile["frontend"]["type_checker"] == "typescript-7-native"
    assert profile["frontend"]["api_contract_compiler_compatibility"] == "typescript-5.9"
    assert profile["maintenance"]["adoption_window"]["minimum_release_age_days"] == 30
    assert "dependency-admission-ledger" in profile["maintenance"]["evidence"]
    assert profile["application_modes"]["allowed"]["chat-only-fullstack"]["framework"] == (
        "streamlit"
    )


def test_path_scoped_rules_preserve_exact_claude_globs(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)

    for rule in load_rules(target / "rules"):
        if rule.trigger != "path-match":
            continue
        source = (target / f".claude/rules/{rule.id}.md").read_text(encoding="utf-8")
        match = re.search(r"\n---\n(paths:\n(?:  - .+\n)+)---\n", source)
        assert match is not None
        frontmatter = yaml.safe_load(match.group(1))
        assert frontmatter["paths"] == rule.applies_to


def test_skill_parity_is_byte_identical_between_claude_and_codex(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    claude = target / ".claude/skills"
    codex = target / ".codex/skills"
    claude_paths = {path.relative_to(claude) for path in claude.rglob("SKILL.md")}
    codex_paths = {path.relative_to(codex) for path in codex.rglob("SKILL.md")}

    assert claude_paths == codex_paths
    assert claude_paths
    for relative in claude_paths:
        assert (claude / relative).read_bytes() == (codex / relative).read_bytes()


def test_every_local_skill_has_a_turkish_equivalent(
    tmp_path: Path, answers_factory: Callable[..., Answers]
) -> None:
    target = _project(tmp_path, answers_factory)
    for command in COMMANDS:
        turkish_cli = TURKISH_COMMANDS[command.cli][0]
        english = target / f".codex/skills/kt-{command.cli}/SKILL.md"
        turkish = target / f".codex/skills/kt-{turkish_cli}/SKILL.md"
        assert english.is_file()
        assert turkish.is_file()
        english_text = english.read_text(encoding="utf-8")
        turkish_text = turkish.read_text(encoding="utf-8")
        assert f"Exact equivalent: /kt-{turkish_cli}." in english_text
        assert f"Birebir eşleniği: /kt-{command.cli}." in turkish_text
        assert "Argümanlar:" in turkish_text
        assert "Arguments:" not in turkish_text
        assert "Exact equivalent:" not in turkish_text
        assert "local-applicator" not in turkish_text


def test_reserved_names_are_avoided_by_the_kt_namespace() -> None:
    claude_reserved = {"clear", "compact", "config", "doctor", "help", "init", "mcp", "status"}
    codex_reserved = {"compact", "diff", "help", "init", "login", "logout", "review", "status"}
    generated = {f"kt-{command.cli}" for command in COMMANDS}

    assert all(name.startswith("kt-") for name in generated)
    assert not generated.intersection(claude_reserved)
    assert not generated.intersection(codex_reserved)
    assert len(generated) == 12


def test_pinned_generator_is_persisted_and_bootstrap_rejects_mismatch(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    answers = yaml.safe_load((target / ".kt-scaffold/answers.yml").read_text(encoding="utf-8"))
    assert answers["generator_version"] == __version__

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_cli = fake_bin / "kt-scaffold"
    fake_cli.write_text("#!/bin/sh\necho 9.9.9\n", encoding="utf-8")
    fake_cli.chmod(fake_cli.stat().st_mode | stat.S_IXUSR)
    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"

    completed = subprocess.run(
        [str(target / "scripts/bootstrap.sh")],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert f"expected {__version__}, found 9.9.9" in completed.stderr


def test_dependency_pinning_covers_python_npm_browser_images_and_compose() -> None:
    for lock_path in (
        REPOSITORY_ROOT / "packaging/locks/generator-linux-amd64-cp313-musllinux.requirements.lock",
        REPOSITORY_ROOT / "packaging/locks/build-system.requirements.lock",
    ):
        assert "--hash=sha256:" in lock_path.read_text(encoding="utf-8")
    for relative in (
        "src/kt_scaffold/templates/python-fastapi/app/backend/requirements.txt",
        "src/kt_scaffold/templates/python-fastapi/app/backend/requirements-dev.txt",
    ):
        assert "--hash=sha256:" in (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")

    for lock_path in (
        REPOSITORY_ROOT / "src/kt_scaffold/templates/common/app/frontend/package-lock.json",
        REPOSITORY_ROOT / "src/kt_scaffold/templates/common/e2e/package-lock.json",
    ):
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        resolved = [entry for entry in lock["packages"].values() if entry.get("resolved")]
        assert resolved
        assert all(str(entry.get("integrity", "")).startswith("sha512-") for entry in resolved)

    images = (REPOSITORY_ROOT / "packaging/images.lock").read_text(encoding="utf-8")
    identities = [line for line in images.splitlines() if line and not line.startswith("#")]
    assert identities and all(re.search(r"@sha256:[0-9a-f]{64}$", line) for line in identities)
    compose = (
        REPOSITORY_ROOT / "src/kt_scaffold/templates/common/app/infra/docker-compose.local.yml"
    ).read_text(encoding="utf-8")
    assert not re.search(r"(?m)^\s+image:\s+[^\n@}$]+:[^\n@}]+$", compose)


def test_report_skeleton_uses_observed_counts_and_all_fixed_groups() -> None:
    report = report_skeleton(
        locale="en",
        verdict="PASS",
        ran=["scripts/quality-gate.sh all"],
        counts={"unit": 17, "browser": 2, "skipped": 1},
    )

    assert "unit 17 passed / browser 2 passed / skipped 1" in report
    assert all(
        f"**{group}**" in report
        for group in (
            "DEFECT",
            "TRAP",
            "OBSERVATION",
            "OPEN",
            "SIDE-EFFECT",
        )
    )
    assert validate_report(report) == []


def test_report_decisions_and_done_report_advisory_preserve_unsupported_claim(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)

    result = done_report_operation("Walking skeleton", "L2", str(target))

    assert result["ok"] is True
    assert result["tier_supported"] == "L0"
    assert result["verdict"] == "unsupported claim reported"
    assert result["missing"] == ["claimed L2, but observed evidence supports L0"]
    report = str(result["report_skeleton"])
    assert "awaiting decision: 1 (M1)" in report
    assert "M1 claimed L2, but observed evidence supports L0 ← DECISION" in report
    assert "M2 claimed L2, but observed evidence supports L0" in report
    assert validate_report(report) == []


def test_report_labels_use_primary_locale_and_fallback_to_english() -> None:
    turkish = report_skeleton(locale="tr-TR", verdict="GEÇTİ", ran=[], counts={})
    fallback = report_skeleton(locale="de", verdict="PASS", ran=[], counts={})

    assert turkish.startswith("# Koşum raporu")
    assert "1. Sonuç:" in turkish and "**KUSUR**" in turkish
    assert "yerel · doğrulama" in turkish
    assert "birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0" in turkish
    assert "karar bekleyen: yok" in turkish
    assert "awaiting decision" not in turkish
    assert fallback.startswith("# Run report")
    assert "1. Result:" in fallback and "**DEFECT**" in fallback
    assert validate_report(turkish, locale="tr-TR") == []
    assert validate_report(fallback, locale="de") == []


def test_turkish_report_skill_is_not_partially_english(
    tmp_path: Path, answers_factory: Callable[..., Answers]
) -> None:
    target = _project(tmp_path, answers_factory, locales=["tr", "en"])
    skill = (target / ".codex/skills/kt-test-run-report/SKILL.md").read_text(encoding="utf-8")

    assert "# Sabit koşum raporu" in skill
    assert "Değişmeyen dokuz kural:" in skill
    assert "**KUSUR**" in skill and "**YAN-ETKİ**" in skill
    assert "# Fixed run report" not in skill
    assert "Nine constraints are invariant" not in skill


def test_domain_first_init_has_context_and_no_business_implementation(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory, primary_domain="booking")

    assert (target / "specs/booking/DOMAIN.md").is_file()
    assert (target / "specs/booking/roadmap.md").is_file()
    assert (target / "specs/booking/PRDs").is_dir()
    assert not list((target / "specs/booking/PRDs").iterdir())
    assert not (target / "app/backend/app/domain/models/booking.py").exists()
    assert not (target / "app/backend/src/domain/booking").exists()
