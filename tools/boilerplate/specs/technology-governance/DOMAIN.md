# Technology Governance domain

Status: Draft

## Purpose

Technology Governance owns the machine-readable application technology authority, controlled
exceptions, compatibility floors, and capability-specific contracts that constrain what the Project
Factory may emit and what application teams may adopt.

## Actors

- Architecture owner — approves the baseline and resolves technology exceptions.
- Platform maintainer — validates the profile and keeps templates aligned with it.
- Application team — consumes fixed defaults and requests capability activation through accepted PRDs.
- Security and data reviewer — reviews lifecycle, data handling, provider, and migration consequences.

## Ubiquitous language

- **Mandatory profile** — schema-validated set of required, conditional, and forbidden technologies.
- **Controlled exception** — narrow eligibility rule requiring an accepted PRD rather than caller choice.
- **Capability activation** — reviewed migration and adapter work that enables an allowed optional
  technology.
- **Profile drift** — mismatch among profile authority, templates, manifests, generated code, or tests.

## Invariants

1. The caller and coding agent do not select an alternative backend, persistence engine, or SSR stack.
2. Profile exceptions are explicit, narrowly eligible, and declared by an accepted capability PRD.
3. Root and generated profiles remain schema-valid and semantically synchronized.
4. A permitted technology is not automatically active, production-ready, or admitted.
5. Version changes require dependency admission and compatibility evidence.

## Owned data and artifacts

- Root and generated `technology-profile.yml` schemas and semantic validation.
- Fixed application-mode, frontend, backend, persistence, security, observability, delivery, and
  maintenance choices.
- Optional vector and embedding activation contract.

## Upstream boundaries

- Organization architecture standards, security policy, and compatibility evidence.
- Delivery Assurance dependency and artifact admission.

## Downstream boundaries

- Project Factory answer resolution and template selection.
- Application Foundation implementation and release shape.
- Capability Delivery PRD validation for optional capabilities.

## Explicit non-responsibilities

- Implementing business retrieval or AI features.
- Selecting providers, models, dimensions, or indexes for a product without its accepted PRD.
- Owning package download, image transport, or runtime deployment promotion.
