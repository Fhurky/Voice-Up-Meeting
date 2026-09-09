# Product specifications

Status: Draft catalog

This directory is the product-requirement authority for independently deliverable capabilities in
the `kt-scaffold` product. Architecture plans, implementation initiatives, source code, tests, and
runbooks are evidence and delivery material; they do not replace an accepted capability PRD.

The authority chain is:

`Domain context -> Draft PRD -> Human review -> Accepted PRD -> Plan -> Tasks -> Implementation -> Evidence`

Most PRDs in this catalog are retrospective Drafts. They describe an implemented or partially
implemented baseline that predates the domain catalog. Existing code is recorded as observed
baseline, not treated as proof that the requirement has been accepted. A human owner must resolve
open decisions, reconcile implementation drift, and explicitly change the PRD status before new
implementation authority exists.

## Domain catalog

| Domain | Purpose | Roadmap |
| --- | --- | --- |
| [Agent Platform](agent-platform/DOMAIN.md) | Portable governed custom-agent contracts and conformance semantics | [Roadmap](agent-platform/roadmap.md) |
| [Project Factory](project-factory/DOMAIN.md) | Deterministic creation and safe managed evolution of scaffolded repositories | [Roadmap](project-factory/roadmap.md) |
| [Capability Delivery](capability-delivery/DOMAIN.md) | Accepted-PRD traceability into an executable full-stack vertical | [Roadmap](capability-delivery/roadmap.md) |
| [Engineering Governance](engineering-governance/DOMAIN.md) | Canonical engineering rules, client projections, and authority-aware reconciliation | [Roadmap](engineering-governance/roadmap.md) |
| [Application Foundation](application-foundation/DOMAIN.md) | Secure generated application, runtime, deployment, and observability baseline | [Roadmap](application-foundation/roadmap.md) |
| [Technology Governance](technology-governance/DOMAIN.md) | Fixed technology authority and reviewed capability extensions | [Roadmap](technology-governance/roadmap.md) |
| [Delivery Assurance](delivery-assurance/DOMAIN.md) | Observed quality evidence and offline software-supply-chain admission | [Roadmap](delivery-assurance/roadmap.md) |

CLI commands, MCP tools, HTTP routes, Helm charts, scripts, and client-specific files are delivery
adapters or implementation surfaces. They belong to the capability whose actor outcome they serve;
they are not standalone domains merely because they have separate directories.
