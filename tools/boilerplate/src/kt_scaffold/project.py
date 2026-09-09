"""Project template rendering and transactional initialization."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

import yaml

from kt_scaffold import __version__
from kt_scaffold.agent_platform import production_asset_paths
from kt_scaffold.agent_platform.compiler import compile_agent_projections
from kt_scaffold.agent_platform.projection_store import render_inert_projections
from kt_scaffold.corpus import generator_corpus_dir, validate_corpus
from kt_scaffold.knowledge import project_metadata
from kt_scaffold.models import Answers, Change, ToolResult
from kt_scaffold.render import render_clients
from kt_scaffold.safety import SafetyError, atomic_write, make_stage, publish_staged_tree
from kt_scaffold.technology import load_technology_profile

PLACEHOLDER_RE = re.compile(r"@@[A-Z][A-Z0-9_]+@@")
TRANSIENT_TEMPLATE_PARTS = frozenset(
    {
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "node_modules",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        "playwright-report",
        "test-results",
    }
)
TRANSIENT_TEMPLATE_FILES = frozenset({".DS_Store"})
TRANSIENT_TEMPLATE_SUFFIXES = frozenset({".pyc", ".pyo"})


class ManagedManifest(TypedDict):
    format: int
    generator_version: str
    managed: dict[str, str]


def template_root() -> Path:
    root = Path(__file__).resolve().parent / "templates"
    if not root.is_dir():
        raise RuntimeError("template bundle is missing from the installed package")
    return root


def _template_files(directory: Path) -> Iterator[Path]:
    if not directory.is_dir():
        raise RuntimeError(f"template profile is missing: {directory.name}")
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if (
            TRANSIENT_TEMPLATE_PARTS.intersection(relative.parts)
            or path.name in TRANSIENT_TEMPLATE_FILES
            or path.suffix in TRANSIENT_TEMPLATE_SUFFIXES
        ):
            continue
        if path.is_symlink():
            raise SafetyError(f"template symbolic link rejected: {path}")
        if path.is_file():
            yield path


def _replacements(answers: Answers) -> dict[str, str]:
    database_url = (
        f"postgresql+asyncpg://app:app-local-password@postgres:5432/{answers.target_package}_db"
    )
    return {
        "@@PRODUCT_NAME_JSON@@": json.dumps(answers.product_name),
        "@@PRODUCT_NAME_HTML@@": html.escape(answers.product_name),
        "@@PROJECT_INTENT_JSON@@": json.dumps(answers.project_intent),
        "@@PRODUCT_NAME@@": answers.product_name,
        "@@PRODUCT_SLUG@@": answers.product_slug,
        "@@PRODUCT_PACKAGE@@": answers.target_package,
        "@@PROJECT_INTENT@@": answers.project_intent,
        "@@PRIMARY_DOMAIN@@": answers.primary_domain,
        "@@BACKEND_PROFILE@@": answers.backend_profile,
        "@@PERSISTENCE_PROFILE@@": str(answers.persistence_profile),
        "@@ENV_PREFIX@@": str(answers.env_prefix),
        "@@API_PREFIX@@": str(answers.api_prefix),
        "@@TENANT_HEADER@@": answers.tenant_header,
        "@@GENERATOR_VERSION@@": answers.generator_version,
        "@@DATABASE_URL@@": database_url,
        "@@LOCALES_JSON@@": json.dumps(answers.locales),
        "@@PRIMARY_LOCALE@@": answers.locales[0],
    }


def _render_bytes(path: Path, replacements: dict[str, str]) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode("utf-8")


def _copy_bundle(stage: Path, source: Path, replacements: dict[str, str]) -> None:
    for path in _template_files(source):
        relative = path.relative_to(source)
        rendered_path = str(relative)
        for token, value in replacements.items():
            rendered_path = rendered_path.replace(token, value)
        atomic_write(stage, rendered_path, _render_bytes(path, replacements))


def _copy_corpus(stage: Path) -> None:
    source = generator_corpus_dir()
    validate_corpus(source)
    for path in sorted(source.iterdir()):
        if path.is_file() and path.name != "GENERATED.lock":
            atomic_write(stage, Path("rules") / path.name, path.read_bytes())


def _copy_agent_platform(stage: Path) -> None:
    """Copy only the allowlisted canonical compiler inputs into an inert project bundle."""

    for relative, source in sorted(production_asset_paths().items()):
        atomic_write(stage, Path("agent-platform") / relative, source.read_bytes())


def _write_domain_context(stage: Path, answers: Answers) -> None:
    domain_root = Path("specs") / answers.primary_domain
    domain = (
        f"# {answers.primary_domain} domain\n\n"
        "Status: context only; no business implementation exists yet.\n\n"
        f"## Project intent\n\n{answers.project_intent}\n\n"
        "## Boundary\n\n"
        "Define actors, ubiquitous language, invariants, owned data and external boundaries before "
        "accepting the first capability PRD.\n"
    )
    roadmap = (
        f"# {answers.primary_domain} roadmap\n\n"
        "Each row links one independently deliverable capability to its accepted PRD.\n\n"
        "| Order | Capability | PRD | Status |\n"
        "|---:|---|---|---|\n"
    )
    atomic_write(stage, domain_root / "DOMAIN.md", domain.encode())
    atomic_write(stage, domain_root / "roadmap.md", roadmap.encode())
    (stage / domain_root / "PRDs").mkdir(parents=True, exist_ok=True)


def _write_answers(stage: Path, answers: Answers) -> None:
    payload = answers.model_dump(mode="json")
    atomic_write(
        stage,
        ".kt-scaffold/answers.yml",
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).encode(),
    )


def _write_project_manifest(stage: Path, answers: Answers) -> None:
    """Persist only bounded metadata intended for knowledge-plane MCP calls."""
    payload = project_metadata(answers).model_dump(mode="json")
    atomic_write(
        stage,
        ".kt-scaffold/project-manifest.json",
        (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode(),
    )


def _configure_frontend_locales(stage: Path, answers: Answers) -> None:
    """Materialize exactly the configured catalogues and their static offline imports."""

    locale_root = stage / "app/frontend/src/locales"
    english = locale_root / "en.json"
    if not english.is_file():
        raise RuntimeError("frontend English source catalogue is missing")
    english_seed = english.read_bytes()
    configured = set(answers.locales)
    for locale in answers.locales:
        destination = locale_root / f"{locale}.json"
        if not destination.exists():
            atomic_write(stage, destination.relative_to(stage), english_seed)
    for path in locale_root.glob("*.json"):
        if path.stem not in configured:
            path.unlink()

    imports = "\n".join(
        f'import catalogue{index} from "@/locales/{locale}.json";'
        for index, locale in enumerate(answers.locales)
    )
    entries = ", ".join(
        f"{json.dumps(locale)}: catalogue{index}" for index, locale in enumerate(answers.locales)
    )
    primary = json.dumps(answers.locales[0])
    source = f"""import {{
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
}} from "react";
{imports}

type MessageTree = {{ [key: string]: string | MessageTree }};
const catalogues: Record<string, MessageTree> = {{ {entries} }};
const primaryLocale = {primary};

function lookup(catalogue: MessageTree, key: string): string | undefined {{
  const direct = catalogue[key];
  if (typeof direct === "string") return direct;
  let current: string | MessageTree | undefined = catalogue;
  for (const part of key.split(".")) {{
    if (typeof current === "string" || current === undefined) return undefined;
    const entry: [string, string | MessageTree] | undefined = Object.entries(current).find(
      ([candidate]) => candidate === part,
    );
    if (entry === undefined) return undefined;
    current = entry[1];
  }}
  return typeof current === "string" ? current : undefined;
}}

interface IntlValue {{
  locale: string;
  setLocale: (value: string) => void;
  t: (key: string) => string;
}}

const Context = createContext<IntlValue | null>(null);

export function IntlProvider({{ children }}: {{ children: ReactNode }}) {{
  const [locale, setLocale] = useState(primaryLocale);
  const value = useMemo(
    () => ({{
      locale,
      setLocale,
      t: (key: string) =>
        lookup(catalogues[locale] ?? catalogues[primaryLocale], key) ??
        lookup(catalogues[primaryLocale], key) ??
        key,
    }}),
    [locale],
  );
  return <Context.Provider value={{value}}>{{children}}</Context.Provider>;
}}

export function useIntl(): IntlValue {{
  const value = useContext(Context);
  if (!value) throw new Error("useIntl must be used inside IntlProvider");
  return value;
}}
"""
    atomic_write(
        stage,
        "app/frontend/src/contexts/IntlContext.tsx",
        source.encode("utf-8"),
    )


def _managed_manifest(stage: Path) -> ManagedManifest:
    managed: dict[str, str] = {}
    for path in sorted(stage.rglob("*")):
        if not path.is_file() or path.relative_to(stage) == Path(".kt-scaffold/manifest.json"):
            continue
        relative = path.relative_to(stage).as_posix()
        managed[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "format": 1,
        "generator_version": Answers.model_fields["generator_version"].default,
        "managed": managed,
    }


def render_project(stage: Path, answers: Answers) -> ManagedManifest:
    root = template_root()
    load_technology_profile(root / "common" / "technology-profile.yml")
    replacements = _replacements(answers)
    _copy_bundle(stage, root / "common", replacements)
    _copy_bundle(stage, root / "python-fastapi", replacements)
    _configure_frontend_locales(stage, answers)
    _copy_corpus(stage)
    _copy_agent_platform(stage)
    _write_domain_context(stage, answers)
    _write_answers(stage, answers)
    _write_project_manifest(stage, answers)
    render_clients(stage, mode="write", primary_locale=answers.locales[0])
    compilation = compile_agent_projections(
        assets_root=stage / "agent-platform",
        client_ids=tuple(answers.agent_clients),
    )
    render_inert_projections(stage, compilation, mode="write")

    if not answers.observability:
        optional_paths = [
            stage / "app/infra/observability",
            stage / "app/infra/docker-compose.observability.yml",
            stage / "app/devops/charts/app-observability",
        ]
        for path in optional_paths:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    for path in stage.rglob("*"):
        if path.is_file() and (path.suffix == ".sh" or path.name.startswith("entrypoint.")):
            path.chmod(0o755)

    leftovers: list[str] = []
    for path in stage.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PLACEHOLDER_RE.search(text):
            leftovers.append(path.relative_to(stage).as_posix())
    if leftovers:
        raise RuntimeError(f"unresolved template placeholders: {', '.join(leftovers)}")

    manifest = _managed_manifest(stage)
    atomic_write(
        stage,
        ".kt-scaffold/manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    return manifest


def project_init(
    target_dir: str | Path,
    answers: Answers,
    *,
    inject_publish_failure: bool = False,
) -> dict[str, object]:
    if answers.generator_version != __version__:
        raise ValueError("generator_version is owned by the installed kt-scaffold package")
    target = Path(target_dir).expanduser().absolute()
    collisions = sorted(key for key in os.environ if key.startswith(str(answers.env_prefix)))
    if collisions:
        raise ValueError(
            f"environment prefix {answers.env_prefix} collides with current process keys: "
            + ", ".join(collisions)
        )
    stage = make_stage(target)
    try:
        manifest = render_project(stage, answers)
        created = [
            Change(path=relative, action="create") for relative in sorted(manifest["managed"])
        ]
        created.append(Change(path=".kt-scaffold/manifest.json", action="create"))
        publish_staged_tree(stage, target, fail_after_swap=inject_publish_failure)
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise

    e2e_command = (
        "KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> "
        "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth"
    )
    result = ToolResult(
        ok=True,
        changes=created,
        next_steps=[
            "scripts/bootstrap.sh",
            "scripts/stack.sh up",
            "scripts/db.sh apply",
            "scripts/create-super-admin.sh",
            "scripts/quality-gate.sh all",
            e2e_command,
        ],
    ).as_dict()
    result.update(
        {
            "profiles_resolved": {
                "backend": answers.backend_profile,
                "persistence": answers.persistence_profile,
            },
            "recommendation_rationale": answers.recommendation_rationale,
            "quality_gate_command": "scripts/quality-gate.sh all",
            "e2e_command": e2e_command,
        }
    )
    return result
