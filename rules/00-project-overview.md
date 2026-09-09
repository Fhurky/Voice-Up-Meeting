---
id: "00-project-overview"
title: "Treat resolved project intent and profiles as repository context"
scope: governance
priority: 0
trigger: always
applies_to: []
gate: "governance-drift.yml"
---

# Project context

This repository is a generated, domain-first monorepo. Read `technology-profile.yml` first: it is the
machine-readable authority for the fixed React/Vite frontend, Python/FastAPI backend,
SQLAlchemy/Alembic persistence stack, permitted chat-only Streamlit exception, and forbidden
alternatives. Read `.kt-scaffold/answers.yml` for project intent, primary domain, product slug, API
prefix, tenant header, locales, and optional capabilities. Read `schema/profile.yml` before changing
persistence. Do not replace the fixed stack with a preferred framework.

The fresh scaffold contains a platform baseline only: health, login, JWT access-token issuance,
`/me`, tenant context, role-based access control, an application-level `super_admin`, OpenAPI export,
generated client types, localized login/home surfaces, tests, and an authentication browser scenario.
It deliberately contains no placeholder business entity.

Business behavior begins in `specs/<domain>/`:

- `DOMAIN.md` defines the bounded context, actors, language, invariants, and boundaries.
- `roadmap.md` decomposes the domain into independently deliverable capabilities.
- `PRDs/<nnn>-<capability>/PRD.md` is the accepted source for a business vertical.

The monorepo keeps schema authority, backend, OpenAPI contract, frontend, browser scenarios,
infrastructure, and deployment definitions together because cross-layer completion is the unit of
work. Keep product-specific vocabulary in the accepted domain specifications and code they
authorize; never add it to the generic platform baseline or this corpus.

Verify context-sensitive work by naming the fixed technology profile in the change notes and by
running its quality gate.
