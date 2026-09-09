---
id: "12-tdd"
title: "Develop behavior through red, green, and refactor"
scope: process
priority: 30
trigger: always
applies_to: []
gate: "quality_gate"
---

# Test-driven development

For every behavior change:

1. **Red:** add a test that fails for the missing or broken behavior.
2. **Green:** implement the smallest complete behavior that satisfies the accepted PRD.
3. **Refactor:** improve the design while keeping the relevant suite green.

Test observable contracts, not implementation choreography. A confidence-critical boundary uses the
real database, filesystem, HTTP application, or downstream adapter when practical. If a boundary must
be mocked, use a signature-constrained mock and pin the exact produced shape, including required and
forbidden fields. A mock written only to agree with the consumer is false-green evidence.

Cover the happy path, validation and authorization failures, tenant isolation, idempotent retry,
soft-delete behavior where applicable, and the regression that motivated a fix. Generated code ships
with its tests in the same change. Do not weaken, skip, or delete a failing test merely to make a gate
green.

Framework behavior does not need a duplicate test. Business invariants, profile adapters, contract
generation, permission checks, and cross-layer wiring do.
