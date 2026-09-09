---
id: "10-spec-first"
title: "Require an accepted domain PRD before business implementation"
scope: process
authority: mandatory
priority: 10
trigger: always
applies_to: []
gate: "spec_required"
---

# Domain-first, spec-driven development

Every business capability belongs to one bounded context under `specs/<domain>/`. The required
layout is:

```text
specs/<domain>/
├── DOMAIN.md
├── roadmap.md
└── PRDs/<nnn>-<capability>/
    ├── PRD.md
    ├── plan.md
    └── tasks.md
```

`DOMAIN.md` owns the domain purpose, actors, ubiquitous language, invariants, owned data, upstream and
downstream boundaries, and explicit non-responsibilities. `roadmap.md` is the spec-of-specs: each row
links to one independently deliverable capability and its state. A PRD links back to exactly one
roadmap row, and that row links to the PRD.

The workflow is **Spec -> Plan -> Tasks -> Implement**. `/kt-spec` may create the workspace, but
`/kt-domain`, `/kt-schema`, `/kt-page`, and `/kt-scenario` must receive an accepted `spec_path` and
refuse any business generation without it. Acceptance is an explicit `Status: Accepted` in PRD
metadata; a draft or missing PRD is not authorization to code.

A PRD describes outcomes, actors, invariants, API/data/security behavior, validation, observability,
deployment impact, test strategy, and evidence-ticked acceptance criteria. Use `N/A — <reason>` for a
cross-cutting concern that does not apply; never omit it silently. Use spelled-out sequential labels
such as `Decision 1`, `Requirement 1`, and `Open Question 1`, not private shorthand codes.

Specs can lag code. Verify every cited path and every “new” claim against the repository before
planning work. If implementation and accepted requirements disagree, stop and surface the conflict;
do not silently make either one authoritative.
