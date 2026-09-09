---
id: "52-end-to-end-feature"
title: "Deliver each accepted capability across every affected layer"
scope: quality
authority: mandatory
priority: 70
trigger: always
applies_to: []
gate: "done_report"
---

# End-to-end feature completion

Begin by reading the accepted PRD, its `plan.md` and `tasks.md`, the domain context, resolved profiles,
and the nearest complete vertical pattern. Verify cited files against current code. Skip a layer only
when the PRD marks it `N/A — <reason>`.

For a capability that touches them, complete these surfaces in dependency order:

1. recorded schema authority and generated/reviewed migration;
2. persistence/domain model or profile equivalent;
3. repository/adapter and application service with tenant and RBAC invariants;
4. typed API request/response/error contract and dependency wiring;
5. profile-native unit/integration tests;
6. offline OpenAPI export and committed contract;
7. generated frontend API types and domain service;
8. localized page/components, route, menu and permission gating;
9. frontend tests and a committed browser scenario linked to acceptance criteria;
10. configuration, worker, cache, observability, chart, overlay, Secret reference, and public docs
    impacts required by the PRD.

Use additive-first deployment ordering for a compatibility-sensitive schema change: add compatible
shape, deploy readers/writers, backfill through an explicit operation, switch behavior, then remove old
shape only under separately authorized destructive scope.

Do not hand off with stale OpenAPI/types, a route with no backend guard, a setting absent from an
environment surface, an unregistered model/provider, an untranslated string, or an unrenderable
workload. `done_report` names every missing layer and the highest evidence tier actually reached.
