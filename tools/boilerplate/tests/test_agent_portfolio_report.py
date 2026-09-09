"""Structural and claim-level checks for the four-client decision report."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT = REPOSITORY_ROOT / "mockups/03-kapali-devre-agentic-kodlama-raporu.html"
REPORT_CSS = REPOSITORY_ROOT / "mockups/_report.css"


class _ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.append(element_id)
        for name in ("href", "src"):
            reference = attributes.get(name)
            if reference:
                self.references.append(reference)


def _parsed_report() -> tuple[str, _ReportParser]:
    source = REPORT.read_text(encoding="utf-8")
    parser = _ReportParser()
    parser.feed(source)
    parser.close()
    return source, parser


def test_report_internal_links_and_local_assets_resolve() -> None:
    _, parser = _parsed_report()

    assert len(parser.ids) == len(set(parser.ids))
    ids = set(parser.ids)
    assert {reference[1:] for reference in parser.references if reference.startswith("#")} <= ids

    for reference in parser.references:
        parsed = urlparse(reference)
        if reference.startswith("#") or parsed.scheme in {"data", "http", "https"}:
            continue
        local_path = (REPORT.parent / parsed.path).resolve()
        assert local_path.is_file(), f"missing local report asset: {reference}"


def test_report_has_one_fixed_portfolio_and_acceptance_contract() -> None:
    source, parser = _parsed_report()

    for client in ("Claude Code", "Codex", "Cursor", "Local Agent"):
        assert client in source
    assert re.findall(r'<div class="id">(C\d{2})</div>', source) == [
        f"C{number:02d}" for number in range(1, 10)
    ]
    assert {f"r{number}" for number in range(1, 20)} <= set(parser.ids)


def test_report_does_not_overstate_unfinished_validation() -> None:
    source, _ = _parsed_report()

    assert "Local Agent kontrollü pilot adayıdır" in source
    assert "aynı kabul sözleşmesiyle değerlendirilir" in source
    assert "Local Agent’ın PoC ve MCP → CLI uçtan uca yürüyen iskelet akışı doğrulanmış" in source
    assert "Codex’in CLI/Qwen yolu kısmen test edilmiştir" in source
    assert (
        "Claude Code ve Cursor için ortak regresyon koşumları henüz planlama aşamasındadır"
        in source
    )
    assert "C01–C09 bugün yürütülebilir bir test paketi değil" in source
    assert "bu belge bunlar için “geçti” iddiasında bulunmaz" in source
    assert "Geçici dizin saklanmadı" in source
    assert "VS Code arayüz koşumu tekrar edilmedi" in source
    assert "116 kural / 342 hedefte sıfır bulgu ve sıfır ayrıştırma hatası" in source
    assert "migrate chart ayrıca oluşturularak sıfır bulguyla kapatıldı" in source
    assert "gömülü erişim anahtarı, token veya parola tespit etmedi" in source


def test_report_uses_direct_section_titles_and_neutral_organization_language() -> None:
    source, _ = _parsed_report()
    rejected_phrases = (
        "Aynı iş, farklı işletim sınırı",
        "Tek kural kaynağı, istemciye uygun dosyalar",
        "İstemci değişir, kontrol düzlemi değişmez",
        "Her sürümde aynı görevler",
        "Dört istemciyi sabitle, yükseltmeyi ölç",
        "Resmî belge + katmanlı yerel doğrulama",
        "Dört ortam desteklenir; kapalı ağ hattı tektir",
        "Local Agent yalnız sohbet etmedi",
        "Seçim değil, destek portföyü",
        "Agent yetkisi, model kalitesinden bağımsızdır",
        "Agentic kodlama çalışma standardı",
        "Dört istemci, tek proje sözleşmesi",
        "01 · Yönetici kararı",
        "Destek portföyü",
        "araçtan bağımsız proje",
        "Sürüm 2.1",
        "Dört ortam · tek yönetişim · ölçülebilir test",
    )

    assert not any(phrase in source for phrase in rejected_phrases)
    assert '<h1 id="report-title">Vibe Coding Çalışma Ortamı Standardı</h1>' in source
    assert "Vibe Coding Ortam Araçları" in source
    assert "<h2>İstemci dosyaları</h2>" not in source
    assert 'class="toc"' not in source
    assert "İçindekiler" not in source
    assert re.search(r"\bagentic\b", source, flags=re.IGNORECASE) is None
    assert re.search(r"\bbanka\b", source, flags=re.IGNORECASE) is None


def test_report_and_docs_describe_vscode_projection_and_bootstrap_boundary() -> None:
    source, _ = _parsed_report()
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    global_mcp = (REPOSITORY_ROOT / "docs/global-mcp.md").read_text(encoding="utf-8")

    for content in (source, readme, global_mcp):
        assert "AGENTS.md" in content
        assert ".claude/rules" in content
        assert ".claude/skills" in content
    assert "There is no universal MCP client configuration file" in global_mcp
    assert '"mcpServers"' in global_mcp
    assert '"servers"' in global_mcp
    assert "Deterministic bootstrap" in global_mcp
    assert "Intent bootstrap" in global_mcp


def test_report_visual_language_has_no_gradient() -> None:
    assert "gradient(" not in REPORT_CSS.read_text(encoding="utf-8")
