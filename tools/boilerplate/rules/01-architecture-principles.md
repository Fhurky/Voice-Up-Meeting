---
id: "01-architecture-principles"
title: "Preserve bounded contexts and inward dependency direction"
scope: governance
priority: 10
trigger: always
applies_to: []
gate: "review"
---

# Architecture principles

Organize business behavior by bounded context and deliver it as a vertical slice derived from an
accepted PRD. Dependencies point inward:

`api -> services -> infrastructure/repositories -> domain`

- `api` owns transport, authentication dependencies, validation, and response mapping.
- `services` owns business invariants, tenant scoping, authorization-aware orchestration, and
  transaction boundaries.
- `infrastructure/repositories` owns persistence queries and external adapters.
- `domain` owns models and domain types and imports nothing from transport or infrastructure.
- `core`, `db`, and middleware are cross-cutting; they must not import API or service modules.

Use dependency injection at the transport boundary. Do not instantiate repositories, settings,
sessions, or external clients inside endpoint handlers. Prefer composition, small cohesive modules,
and explicit typed contracts over inheritance or global state.

Services communicate over HTTP contracts only. A service must not read another service's database,
create a database link, or join across bounded contexts. Cross-boundary references are values and are
validated through the owning service. Background work is a scheduled or on-demand module unless an
accepted PRD explicitly introduces another execution model.

Engine-specific behavior stays inside the selected persistence adapter and repository boundary.
Authentication authority is application-level: `super_admin` bypasses application permission checks
but never becomes an operating-system root user, database superuser, or cluster administrator.

Reject speculative abstractions and placeholder domains. Add a shared abstraction only after at
least two real consumers demonstrate the same stable contract.
