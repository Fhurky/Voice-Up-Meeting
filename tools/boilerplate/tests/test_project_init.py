"""End-to-end project initialization contracts for the fixed technology profile."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from kt_scaffold.models import Answers
from kt_scaffold.project import _template_files, project_init

PROFILES = [
    ("python-fastapi", "sqlalchemy-alembic"),
]


def test_template_file_discovery_rejects_installer_and_tool_residue(tmp_path: Path) -> None:
    template = tmp_path / "template"
    wanted = template / "scripts/render_charts.py"
    wanted.parent.mkdir(parents=True)
    wanted.write_text("print('render')\n", encoding="utf-8")
    residue = [
        template / "scripts/__pycache__/render_charts.cpython-313.pyc",
        template / "app/backend/.mypy_cache/3.13/cache.db",
        template / "app/backend/node_modules/example/index.js",
        template / "app/frontend/dist/assets/index.js",
        template / "e2e/playwright-report/index.html",
    ]
    for path in residue:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"transient")

    assert list(_template_files(template)) == [wanted]


def test_init_refuses_to_impersonate_another_generator_release(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    with pytest.raises(ValueError, match="owned by the installed"):
        project_init(
            tmp_path / "project",
            answers_factory(generator_version="0.0.9"),
        )


def test_init_rejects_an_invalid_packaged_technology_profile_before_publish(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"

    def reject_profile(_path: str | Path) -> None:
        raise ValueError("invalid packaged technology profile")

    monkeypatch.setattr("kt_scaffold.project.load_technology_profile", reject_profile)
    with pytest.raises(ValueError, match="invalid packaged technology profile"):
        project_init(target, answers_factory())
    assert not target.exists()


def _contains_mapping_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_mapping_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_mapping_key(item, key) for item in value)
    return False


@pytest.mark.parametrize(("backend", "persistence"), PROFILES)
def test_profile_initialization_is_complete_and_manifest_verified(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> None:
    target = tmp_path / backend
    answers = answers_factory(
        backend_profile=backend,
        persistence_profile=persistence,
    )

    result = project_init(target, answers)

    assert result["ok"] is True
    assert result["profiles_resolved"] == {
        "backend": backend,
        "persistence": persistence,
    }
    assert result["quality_gate_command"] == "scripts/quality-gate.sh all"
    assert result["e2e_command"] == (
        "KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> "
        "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth"
    )
    assert result["e2e_command"] in result["next_steps"]

    required = [
        ".kt-scaffold/answers.yml",
        ".kt-scaffold/manifest.json",
        "agent-evals/policy-pressure.yml",
        ".codex/config.toml",
        ".claude/settings.json",
        "AGENTS.md",
        "CLAUDE.md",
        "technology-profile.yml",
        "app/backend",
        "app/frontend/package-lock.json",
        "app/infra/docker-compose.local.yml",
        "e2e/auth/01-super-admin-login.mjs",
        "rules/corpus.schema.json",
        "scripts/e2e.sh",
        "scripts/quality-gate.sh",
        "specs/payments/DOMAIN.md",
        "specs/payments/roadmap.md",
    ]
    assert all((target / relative).exists() for relative in required)
    assert not (target / ".mcp.json").exists()
    assert not (target / ".cursor/mcp.json").exists()
    assert json.loads((target / ".claude/settings.json").read_text(encoding="utf-8")) == {
        "enableAllProjectMcpServers": False
    }
    codex_config = (target / ".codex/config.toml").read_text(encoding="utf-8")
    assert "mcp_servers" not in codex_config
    assert "bank manages the global stdio or Streamable HTTP MCP registration" in codex_config
    for json_path in target.rglob("*.json"):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert not _contains_mapping_key(payload, "mcpServers")

    assert (target / "schema/alembic/env.py").is_file()

    persisted_answers = yaml.safe_load(
        (target / ".kt-scaffold/answers.yml").read_text(encoding="utf-8")
    )
    assert persisted_answers["backend_profile"] == backend
    assert persisted_answers["persistence_profile"] == persistence
    assert not {"password", "token", "api_key", "jwt_secret"} & set(persisted_answers)

    manifest = json.loads((target / ".kt-scaffold/manifest.json").read_text(encoding="utf-8"))
    managed = manifest["managed"]
    disk_files = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file() and path.relative_to(target) != Path(".kt-scaffold/manifest.json")
    }
    assert set(managed) == disk_files
    for relative, expected_digest in managed.items():
        actual = hashlib.sha256((target / relative).read_bytes()).hexdigest()
        assert actual == expected_digest

    for path in target.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and (path.suffix == ".sh" or path.name.startswith("entrypoint.")):
            assert path.stat().st_mode & stat.S_IXUSR


@pytest.mark.parametrize(("backend", "persistence"), PROFILES)
def test_generated_tree_has_no_placeholders_plugins_or_build_residue(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> None:
    target = tmp_path / backend
    project_init(
        target,
        answers_factory(backend_profile=backend, persistence_profile=persistence),
    )

    forbidden_parts = {
        ".codex-plugin",
        ".claude-plugin",
        "plugin.json",
        "marketplace.json",
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "dist",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "htmlcov",
    }
    for path in target.rglob("*"):
        relative = path.relative_to(target)
        assert not forbidden_parts.intersection(relative.parts)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert re.search(r"@@[A-Z][A-Z0-9_]+@@", text) is None

    assert not (target / "specs/item").exists()
    assert not (target / "app/backend/app/domain/models/item.py").exists()


def test_init_does_not_mutate_enclosing_vcs_metadata(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    repository = tmp_path / "repository"
    git_dir = repository / ".git"
    git_dir.mkdir(parents=True)
    sentinel = git_dir / "index"
    sentinel.write_bytes(b"immutable-vcs-sentinel")
    before = sentinel.read_bytes()

    project_init(repository / "generated", answers_factory())

    assert sentinel.read_bytes() == before
    assert sorted(path.relative_to(git_dir).as_posix() for path in git_dir.rglob("*")) == ["index"]


def test_natural_language_answers_are_escaped_for_generated_code_and_markup(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "escaped"
    product_name = 'Bank\'s <Controls> "Desk"'
    project_intent = 'Review the bank\'s "high-risk" flow.\nKeep evidence local.'
    project_init(
        target,
        answers_factory(product_name=product_name, project_intent=project_intent),
    )

    json_name = json.dumps(product_name)
    json_intent = json.dumps(project_intent)
    config = (target / "app/frontend/src/lib/config.ts").read_text(encoding="utf-8")
    login = (target / "app/frontend/src/pages/LoginPage.tsx").read_text(encoding="utf-8")
    scenario = (target / "e2e/auth/01-super-admin-login.mjs").read_text(encoding="utf-8")
    html = (target / "app/frontend/index.html").read_text(encoding="utf-8")
    contract_path = next((target / "specs/openapi").glob("*-api.yaml"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    compose = yaml.safe_load(
        (target / "app/infra/docker-compose.local.yml").read_text(encoding="utf-8")
    )

    assert f"productName: {json_name}" in config
    assert f"projectIntent: {json_intent}" in config
    assert f"<h1>{{{json_name}}}</h1>" in login
    assert f"name: {json_name}" in scenario
    assert "Bank&#x27;s &lt;Controls&gt; &quot;Desk&quot;" in html
    assert contract["info"]["title"] == product_name
    assert compose["services"]["backend"]["environment"]["ZZSCF_PROJECT_NAME"] == product_name


def test_init_materializes_exactly_the_configured_offline_locale_catalogues(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "locales"

    project_init(target, answers_factory(locales=["de", "pt-br"]))

    locale_root = target / "app/frontend/src/locales"
    assert {path.name for path in locale_root.glob("*.json")} == {"de.json", "pt-br.json"}
    context = (target / "app/frontend/src/contexts/IntlContext.tsx").read_text(encoding="utf-8")
    assert 'import catalogue0 from "@/locales/de.json";' in context
    assert 'import catalogue1 from "@/locales/pt-br.json";' in context
    assert 'const primaryLocale = "de";' in context
    assert "@/locales/en.json" not in context
    assert "@/locales/tr.json" not in context
