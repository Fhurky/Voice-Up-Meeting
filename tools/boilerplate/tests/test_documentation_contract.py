from __future__ import annotations

import re
from pathlib import Path

from kt_scaffold.cli import CLI_ALIASES
from kt_scaffold.models import DEFAULT_AGENT_CLIENTS
from kt_scaffold.server import (
    MCP_PROMPT_ALIASES,
    MCP_RECOMMENDED_REGISTRATION_NAME,
    MCP_TOOL_ALIASES,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

NUMBERED_DOCS = {
    "01": ("tr/01-genel-bakis.md", "en/01-overview.md"),
    "02": ("tr/02-hizli-baslangic.md", "en/02-quick-start.md"),
    "03": (
        "tr/03-mimari-ve-sorumluluklar.md",
        "en/03-architecture-and-responsibilities.md",
    ),
    "04": ("tr/04-spec-prd-plan-task.md", "en/04-spec-prd-plan-task.md"),
    "05": ("tr/05-ajan-istemcileri.md", "en/05-coding-clients.md"),
    "06": ("tr/06-cli-kullanim-rehberi.md", "en/06-cli-guide.md"),
    "07": ("tr/07-mcp-kullanim-rehberi.md", "en/07-mcp-guide.md"),
    "08": (
        "tr/08-guncelleme-ve-uyumlastirma.md",
        "en/08-updates-and-reconciliation.md",
    ),
    "09": (
        "tr/09-kalite-kanit-ve-e2e.md",
        "en/09-quality-evidence-and-e2e.md",
    ),
    "10": ("tr/10-kapali-devre-operasyon.md", "en/10-closed-network-operation.md"),
    "11": ("tr/11-sorun-giderme.md", "en/11-troubleshooting.md"),
}

REFERENCE_DOCS = {
    "tr/referans/komutlar.md",
    "tr/referans/mcp-araclari.md",
    "tr/referans/dizin-ve-dosyalar.md",
    "tr/referans/manifestler.md",
    "tr/referans/kanit-seviyeleri.md",
    "tr/referans/sozluk.md",
    "en/reference/commands.md",
    "en/reference/mcp-tools.md",
    "en/reference/directories-and-files.md",
    "en/reference/manifests.md",
    "en/reference/evidence-levels.md",
    "en/reference/glossary.md",
}


def _read(relative: str) -> str:
    return (DOCS / relative).read_text(encoding="utf-8")


def test_numbered_user_guides_have_tr_en_pairs() -> None:
    for number, pair in NUMBERED_DOCS.items():
        for relative in pair:
            path = DOCS / relative
            assert path.is_file(), f"missing documentation pair {number}: {relative}"
            assert path.read_text(encoding="utf-8").startswith("# ")

    actual_tr = {path.name[:2] for path in (DOCS / "tr").glob("[0-9][0-9]-*.md")}
    actual_en = {path.name[:2] for path in (DOCS / "en").glob("[0-9][0-9]-*.md")}
    assert actual_tr == set(NUMBERED_DOCS)
    assert actual_en == set(NUMBERED_DOCS)


def test_reference_guides_cover_every_cli_and_mcp_alias() -> None:
    command_reference = _read("tr/referans/komutlar.md") + _read("en/reference/commands.md")
    for turkish, english in CLI_ALIASES.items():
        assert f"`{english}`" in command_reference
        assert f"`{turkish}`" in command_reference

    mcp_reference = _read("tr/referans/mcp-araclari.md") + _read("en/reference/mcp-tools.md")
    for english, turkish in MCP_TOOL_ALIASES.items():
        assert f"`{english}`" in mcp_reference
        assert f"`{turkish}`" in mcp_reference
    for english, turkish in MCP_PROMPT_ALIASES.items():
        assert f"`{english}`" in mcp_reference
        assert f"`{turkish}`" in mcp_reference


def test_mcp_guides_use_the_short_client_registration_name() -> None:
    global_guide = (DOCS / "global-mcp.md").read_text(encoding="utf-8")
    turkish = _read("tr/07-mcp-kullanim-rehberi.md")
    english = _read("en/07-mcp-guide.md")
    assert MCP_RECOMMENDED_REGISTRATION_NAME == "kt"
    assert "/mcp.kt.proje_baslat" in global_guide
    assert "/mcp.kt.proje_baslat" in turkish
    assert "/mcp.kt.project_start" in english
    assert "kt-scaffold-rancher" not in global_guide + turkish + english


def test_reference_documents_exist() -> None:
    assert all((DOCS / relative).is_file() for relative in REFERENCE_DOCS)


def test_local_documentation_links_resolve() -> None:
    markdown_files = sorted(DOCS.rglob("*.md")) + [ROOT / "README.md"]
    failures: list[str] = []
    for path in markdown_files:
        body = path.read_text(encoding="utf-8")
        for match in re.finditer(r"(?<!!)\[[^]]+\]\(([^)]+)\)", body):
            target = match.group(1).split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                failures.append(f"{path.relative_to(ROOT)} -> {target}")
    assert failures == []


def test_generated_project_documentation_has_bilingual_guidance() -> None:
    template_root = ROOT / "src/kt_scaffold/templates/common/docs"
    english = (template_root / "en/README.md").read_text(encoding="utf-8")
    turkish = (template_root / "tr/README.md").read_text(encoding="utf-8")
    assert "accepted PRD" in english
    assert "kabul edilmiş PRD" in turkish
    assert "../../specs/README.md" in english
    assert "../../specs/README.md" in turkish


def test_root_readme_is_a_turkish_user_and_developer_onboarding() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for heading in (
        "## Bir bakışta ürün",
        "## 1. Kullanıcı onboardingi",
        "## 2. Geliştirici onboardingi",
        "## 3. Spec-first teslim akışı",
        "## 4. CLI ve MCP yetki sınırları",
        "## 5. Kodlama istemcileri ve Agent Platform",
        "## 8. Kalite ve kanıt modeli",
        "## 10. Sık yapılan hatalar",
        "## 11. Dokümantasyon haritası",
    ):
        assert heading in readme

    assert readme.count("```mermaid") == 2
    assert "kt-scaffold init" in readme
    assert "--workspace-root" in readme
    assert ".venv/bin/pytest -q" in readme
    assert "## Development" not in readme
    assert "## Scaffold" not in readme
    assert "## Documentation" not in readme
    assert "kt-scaffold creates an offline-first" not in readme


def test_product_docs_separate_governance_projection_and_agent_platform_clients() -> None:
    client_labels = {
        "claude-code": "Claude Code",
        "codex": "Codex",
        "cursor": "Cursor",
        "github-copilot-vscode": "GitHub Copilot",
    }
    assert set(DEFAULT_AGENT_CLIENTS) == set(client_labels)

    high_level_docs = [
        ROOT / "README.md",
        DOCS / "en/README.md",
        DOCS / "tr/README.md",
        DOCS / "en/01-overview.md",
        DOCS / "tr/01-genel-bakis.md",
        DOCS / "en/05-coding-clients.md",
        DOCS / "tr/05-ajan-istemcileri.md",
    ]
    for path in high_level_docs:
        body = path.read_text(encoding="utf-8")
        normalized = " ".join(body.split())
        assert all(label in normalized for label in client_labels.values()), path
        assert ".kt-scaffold/agent-projections/" in body, path
        assert "inert" in body.lower(), path
        assert "conformance" in body.lower(), path
        assert "admission" in body.lower(), path


def test_product_docs_preserve_local_creation_and_remote_governance_boundary() -> None:
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    english_architecture = _read("en/03-architecture-and-responsibilities.md")
    turkish_architecture = _read("tr/03-mimari-ve-sorumluluklar.md")

    assert "local CLI and global MCP server produce the same" not in root_readme
    assert "canonical initial-project bytes" not in english_architecture
    assert "kanonik ilk-proje byte'ları" not in turkish_architecture
    assert "without receiving workspace content or initial-project bytes" in english_architecture
    assert "çalışma alanı içeriği veya ilk-proje byte'larını almaz" in turkish_architecture


def test_command_and_directory_references_cover_agent_platform_surfaces() -> None:
    commands = _read("en/reference/commands.md") + _read("tr/referans/komutlar.md")
    directories = _read("en/reference/directories-and-files.md") + _read(
        "tr/referans/dizin-ve-dosyalar.md"
    )

    assert "`--agent-client`" in commands
    assert "`--workspace-root`" in commands
    for client_id in DEFAULT_AGENT_CLIENTS:
        assert f"`{client_id}`" in commands

    for path in (
        "agent-platform/",
        ".kt-scaffold/agent-projections/",
        ".codex/agents/",
        ".claude/agents/",
        ".github/agents/",
        ".cursor/agents/",
    ):
        assert f"`{path}`" in directories


def test_evidence_reference_supports_domain_specific_real_boundaries() -> None:
    evidence = _read("en/reference/evidence-levels.md") + _read("tr/referans/kanit-seviyeleri.md")
    for concept in (
        "Real-boundary observed",
        "Project Factory",
        "Agent Platform",
        "HTTP/browser",
        "MCP session",
        "client/model/tool/policy/environment",
        "time-bound",
    ):
        assert concept in evidence
