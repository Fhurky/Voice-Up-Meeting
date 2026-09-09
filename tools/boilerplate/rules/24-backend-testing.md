---
id: "24-backend-testing"
title: "Test FastAPI backend contracts at real boundaries with pytest"
scope: backend
authority: mandatory
priority: 60
trigger: path-match
applies_to:
  - "app/backend/**"
  - "schema/**"
gate: "backend-test.yml"
---

# Backend testing

Use pytest and the commands recorded by the fixed Python/FastAPI profile; invoke them through
`scripts/quality-gate.sh` so local and continuous-integration behavior stays aligned. Tests mirror the
application structure: API, services/application, domain, infrastructure/repositories, core,
middleware, workers, integration, and shared fixtures.

Prefer real boundaries for confidence-critical behavior:

- migrate a real PostgreSQL test database with Alembic;
- exercise the real HTTP application for routing, validation, JWT, RBAC, tenant context, and error
  envelopes;
- use real serialization and generated OpenAPI for contract tests;
- test worker entry points with their real registry/bootstrap wiring.

Unit tests isolate business rules. Boundary mocks must be signature-constrained and their response or
error shape must come from the producer contract. Assert important keyword arguments and forbidden
fields. A bare mock that merely records “called” is not evidence of correct dispatch.

Each behavior covers the happy path, malformed input, unauthenticated and forbidden paths where
applicable, tenant isolation, not-found/conflict behavior, idempotent retry, transaction rollback,
and soft-delete visibility. A regression fix includes a test that fails without the fix.

Fixture credentials and bootstrap passwords come from the test process environment and never from a
committed file. Keep fixtures deterministic and clean them through public boundaries. Coverage
percentages are diagnostic; prioritize critical invariants and untested branches over gaming a
number.
