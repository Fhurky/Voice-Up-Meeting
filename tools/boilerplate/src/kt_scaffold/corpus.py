"""Load and validate the single rule corpus."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from kt_scaffold.models import Rule


class CorpusError(ValueError):
    """The canonical corpus is malformed or internally inconsistent."""


def find_project_root(start: str | Path | None = None) -> Path | None:
    current = Path(start or Path.cwd()).expanduser().resolve(strict=False)
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".kt-scaffold" / "answers.yml").is_file():
            return candidate
    return None


def generator_corpus_dir() -> Path:
    explicit = os.environ.get("KT_SCAFFOLD_CORPUS_DIR")
    candidates = [
        Path(explicit).expanduser() if explicit else None,
        Path(__file__).resolve().parents[2] / "rules",
        Path(sys.prefix) / "share" / "kt-scaffold" / "rules",
    ]
    for candidate in candidates:
        if candidate and (candidate / "corpus.schema.json").is_file():
            return candidate.resolve()
    raise CorpusError(
        "canonical corpus not found; set KT_SCAFFOLD_CORPUS_DIR or install the offline bundle"
    )


def _parse_rule(path: Path) -> Rule:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise CorpusError(f"{path}: missing YAML front matter")
    try:
        _, raw_front_matter, body = text.split("---\n", 2)
    except ValueError as exc:
        raise CorpusError(f"{path}: unterminated YAML front matter") from exc
    metadata = yaml.safe_load(raw_front_matter)
    if not isinstance(metadata, dict):
        raise CorpusError(f"{path}: front matter must be an object")
    try:
        rule = Rule.model_validate({**metadata, "body": body.strip() + "\n", "source": path})
    except ValidationError as exc:
        raise CorpusError(f"{path}: {exc}") from exc
    if rule.id != path.stem:
        raise CorpusError(f"{path}: rule id must equal its filename")
    return rule


def load_rules(corpus_dir: str | Path) -> list[Rule]:
    root = Path(corpus_dir).resolve(strict=True)
    rules = [_parse_rule(path) for path in sorted(root.glob("[0-9][0-9]-*.md"))]
    if not rules:
        raise CorpusError(f"{root}: no numbered corpus rules")

    ids: set[str] = set()
    bodies: dict[str, str] = {}
    for rule in rules:
        if rule.authority == "project-owned":
            raise CorpusError(
                f"{rule.source}: canonical corpus cannot own project-owned governance"
            )
        if rule.id in ids:
            raise CorpusError(f"duplicate rule id: {rule.id}")
        ids.add(rule.id)
        normalized = " ".join(rule.body.split()).casefold()
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        if digest in bodies:
            raise CorpusError(f"duplicate normalized body: {bodies[digest]} and {rule.id}")
        bodies[digest] = rule.id

    return sorted(rules, key=lambda item: (item.priority, item.id))


def validate_corpus(corpus_dir: str | Path) -> dict[str, Any]:
    root = Path(corpus_dir).resolve(strict=True)
    schema_path = root / "corpus.schema.json"
    if not schema_path.is_file():
        raise CorpusError(f"{root}: corpus.schema.json is missing")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise CorpusError("corpus.schema.json must describe an object")
    rules = load_rules(root)
    return {
        "ok": True,
        "count": len(rules),
        "digest": corpus_digest(root),
        "ids": [rule.id for rule in rules],
    }


def corpus_digest(corpus_dir: str | Path) -> str:
    root = Path(corpus_dir)
    digest = hashlib.sha256()
    for path in sorted(root.glob("*")):
        if path.is_file() and path.name != "GENERATED.lock":
            digest.update(path.name.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def public_rule(rule: Rule, *, include_body: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": rule.id,
        "title": rule.title,
        "scope": rule.scope,
        "authority": rule.authority,
        "trigger": rule.trigger,
        "applies_to": rule.applies_to,
        "priority": rule.priority,
        "clients": ["agents", "claude", "codex", "cursor"],
        "gate": rule.gate,
    }
    if include_body:
        result["body"] = rule.body
    return result
