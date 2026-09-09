"""Structural checks for the versioned information-note document."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MOCKUPS = REPOSITORY_ROOT / "mockups"
INFORMATION_NOTE = MOCKUPS / "bilgi-notu.html"
INFORMATION_NOTE_PDF = MOCKUPS / "bilgi-notu.pdf"
NOTE_CSS = MOCKUPS / "_note.css"
REPORT_CSS = MOCKUPS / "_report.css"
REPORT = MOCKUPS / "03-kapali-devre-agentic-kodlama-raporu.html"
TOKENS_CSS = MOCKUPS / "_tokens.css"


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.append(element_id)
        for name in ("href", "src"):
            if reference := attributes.get(name):
                self.references.append(reference)


def _parsed_note() -> tuple[str, _DocumentParser]:
    source = INFORMATION_NOTE.read_text(encoding="utf-8")
    parser = _DocumentParser()
    parser.feed(source)
    parser.close()
    return source, parser


def test_information_note_internal_links_and_local_assets_resolve() -> None:
    _, parser = _parsed_note()

    assert len(parser.ids) == len(set(parser.ids))
    ids = set(parser.ids)
    assert {reference[1:] for reference in parser.references if reference.startswith("#")} <= ids

    for reference in parser.references:
        parsed = urlparse(reference)
        if reference.startswith("#") or parsed.scheme in {"data", "http", "https"}:
            continue
        assert (INFORMATION_NOTE.parent / parsed.path).resolve().is_file(), reference


def test_information_note_uses_direct_titles_and_neutral_organization_language() -> None:
    source, _ = _parsed_note()
    rejected_phrases = (
        "Ajan Neyi Kendi Başına Değiştiremez",
        "Uygulama Esası ile birebir karşılık",
        "Kural dosyası ne der, ne sağlar",
        "iki düzlem, tek sözleşme",
    )

    assert not any(phrase in source for phrase in rejected_phrases)
    assert re.search(r"\bbanka\b", source, flags=re.IGNORECASE) is None
    assert "Veri ve Analitik Grup Müdürlüğü" in source


def test_documents_keep_a4_layout_out_of_mobile_breakpoints() -> None:
    note_css = NOTE_CSS.read_text(encoding="utf-8")
    report_css = REPORT_CSS.read_text(encoding="utf-8")
    tokens_css = TOKENS_CSS.read_text(encoding="utf-8")

    assert re.search(r"\.wrap\s*\{[^}]*max-width:\s*760px", tokens_css)
    assert "@page { size: A4; margin: 12mm 11mm; }" in note_css
    assert ".card { break-inside: auto;" in note_css
    assert ".wrap { max-width: 760px; }" in report_css
    assert "@media (max-width: 640px)" in report_css
    assert "@media (max-width: 780px)" not in report_css


def test_information_note_has_versioned_pdf() -> None:
    assert INFORMATION_NOTE_PDF.read_bytes().startswith(b"%PDF-")


def test_documents_use_long_turkish_date_format() -> None:
    numeric_date = re.compile(r"\b(?:0?[1-9]|[12]\d|3[01])\.(?:0?[1-9]|1[0-2])\.\d{4}\b")

    for document in (INFORMATION_NOTE, REPORT):
        source = document.read_text(encoding="utf-8")
        assert numeric_date.search(source) is None
        assert "7 Ağustos 2026" in source
