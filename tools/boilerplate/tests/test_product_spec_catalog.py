from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"

EXPECTED_DOMAINS = {
    "agent-platform": "Agent Platform",
    "application-foundation": "Application Foundation",
    "capability-delivery": "Capability Delivery",
    "delivery-assurance": "Delivery Assurance",
    "engineering-governance": "Engineering Governance",
    "project-factory": "Project Factory",
    "technology-governance": "Technology Governance",
}

REQUIRED_PRD_SECTIONS = {
    "## Intent",
    "## Actors and outcomes",
    "## Verified baseline and gap",
    "## Acceptance criteria",
    "## Delivery flow",
}

ROADMAP_ROW = re.compile(
    r"^\| (?P<number>[0-9]{3}) \| (?P<capability>[^|]+) "
    r"\| \[PRD\]\((?P<link>PRDs/[^)]+/PRD\.md)\) "
    r"\| (?P<status>Draft|Accepted) \|$",
    flags=re.MULTILINE,
)


def _document_status(body: str) -> str:
    matches = re.findall(r"^Status: (Draft|Accepted)$", body, flags=re.MULTILINE)
    assert len(matches) == 1
    return matches[0]


def test_product_spec_catalog_lists_every_bounded_context() -> None:
    catalog = (SPECS / "README.md").read_text(encoding="utf-8")

    assert "Status: Draft catalog" in catalog
    assert "Domain context -> Draft PRD -> Human review -> Accepted PRD" in catalog
    for domain, title in EXPECTED_DOMAINS.items():
        assert f"[{title}]({domain}/DOMAIN.md)" in catalog
        assert f"[Roadmap]({domain}/roadmap.md)" in catalog


def test_domain_roadmaps_resolve_to_structurally_complete_prds() -> None:
    for domain, title in EXPECTED_DOMAINS.items():
        domain_root = SPECS / domain
        domain_text = (domain_root / "DOMAIN.md").read_text(encoding="utf-8")
        roadmap_text = (domain_root / "roadmap.md").read_text(encoding="utf-8")

        assert domain_text.startswith(f"# {title} domain\n\nStatus: Draft\n")
        rows = list(ROADMAP_ROW.finditer(roadmap_text))
        assert rows, f"{domain}/roadmap.md has no capability PRD"

        numbers = [row.group("number") for row in rows]
        assert numbers == sorted(numbers)
        assert len(numbers) == len(set(numbers))

        for row in rows:
            prd_path = domain_root / row.group("link")
            prd_text = prd_path.read_text(encoding="utf-8")

            assert _document_status(prd_text) == row.group("status")
            assert f"Domain: [{title}](../../DOMAIN.md)" in prd_text
            assert f"Roadmap: [Capability {row.group('number')}](../../roadmap.md)" in prd_text
            headings = set(re.findall(r"^## .+$", prd_text, flags=re.MULTILINE))
            assert headings >= REQUIRED_PRD_SECTIONS
