---
id: "50-quality-gate"
title: "Run the deterministic post-change gate before hand-off"
scope: quality
authority: mandatory
priority: 50
trigger: always
applies_to: []
gate: "scripts/quality-gate.sh"
---

# Post-change quality gate

Run the narrowest relevant checks while developing, then `scripts/quality-gate.sh all` before hand-off.
The full gate uses the selected profile and stops at the first failure in this order:

1. configuration-surface synchronization;
2. creation of a unique, profile-specific PostgreSQL database whose name ends in `_test`;
3. profile-native migration deployment into that disposable database;
4. backend formatter/lint and type checks;
5. backend unit plus live PostgreSQL integration suites with `RUN_POSTGRES_INTEGRATION=1`;
6. migration desired-state, applied-history and drift validation against the same test database;
7. offline OpenAPI export and committed-contract drift check;
8. frontend lint, production build, unit suite and committed-type drift check;
9. governance drift and deployment-chart rendering.

The disposable database is dropped on success, failure, or interruption. The full gate must never
apply migrations to the configured application database. The narrower `backend` scope does not
create a database or enable live PostgreSQL tests; its migration checks inspect the configured
database without writing it. Use the full gate for hand-off evidence.

Run the profile-native migration validate/status/drift checks when schema authority or migrations
changed. Run configuration sync when settings changed, chart contract/readiness checks when delivery
files changed, and security scanners when code, dependencies, images, or manifests changed. UI changes
also require the browser rule; a browser pass never replaces build or unit tests.

Generated artifacts are committed contracts. Regenerate them and fail on an unexpected diff; do not
skip the drift step or patch generated output by hand. A failure must be reported with the actual
command and observed output. Do not fix unrelated user-owned changes merely to manufacture a green
tree; isolate and report them.

Automation consumes only the `KT_GATE_SCOPE`, `KT_GATE_STEP`, and `KT_GATE_TESTS` records emitted by
the generated gate. Do not remove, rename, or synthesize those records from human-oriented prose.

Local stdio/CLI execution records `local-executed` provenance. Streamable HTTP cannot execute code in
a caller workstation: first prepare a command bound to the workspace and gate hashes, run that exact
command locally, then finalize its marker output with the returned challenge. Such evidence remains
`client-reported`; only an approved runner attestation may claim `runner-attested` provenance.

Format every run using `53-test-run-report.md`, including skipped and unavailable evidence.
