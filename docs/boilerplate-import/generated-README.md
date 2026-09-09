# VoiceUp

VoiceUp: farklı toplantılarda konuşmacıları kalıcı ses profilleriyle tanıyan, yeni kişileri ayırt eden ve konuşmaları kişilere bağlayan yerel toplantı analiz ürünü.

This repository starts with a working platform baseline: PostgreSQL, JWT authentication, RBAC,
application super-admin, health/readiness endpoints, a localized frontend and real browser evidence.
It intentionally contains no sample business entity.

Primary domain context: specs/speaker-identity/. Backend profile: python-fastapi.
Persistence authority: sqlalchemy-alembic.

## First run

~~~sh
scripts/bootstrap.sh
scripts/stack.sh up -d --build --wait
scripts/db.sh apply
scripts/create-super-admin.sh
scripts/quality-gate.sh all
export KT_SCAFFOLD_OFFLINE_BUNDLE=/approved/bundles/<platform-matrix>
export KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-sha256-of-SHA256SUMS>
scripts/e2e.sh auth
~~~

`scripts/quality-gate.sh all` includes the network-free dependency admission check. To reproduce
the forge security job locally, point `INTERNAL_SCANNER_MATERIAL_DIR`,
`INTERNAL_SCANNER_SHA256SUMS`, its out-of-band `INTERNAL_SCANNER_SHA256SUMS_SHA256`,
`INTERNAL_SCANNER_ADMITTED_ON`, `INTERNAL_SEMGREP_RULESET` and `TRIVY_CACHE_DIR` at one
bank-admitted, at-most-seven-day-old scanner snapshot and run `scripts/security-gate.sh`. Dependabot is active only when
the bank-managed GitHub Enterprise service can reach approved internal mirrors; every proposal
must still pass the admission ledger.

The complete local gate also requires the generated project's pinned `kt-scaffold` version and
Helm on `PATH`; the chart policy uses that CLI's admitted Python interpreter and never downloads a
runtime parser.

All runtime services remain inside the local or cluster network. Populate the offline bundle through
the bank's controlled mirror before disconnecting; the application itself never downloads code,
fonts, scripts, models or telemetry destinations at runtime. The E2E helper defaults to offline,
verifies the bundle manifest against its out-of-band bank admission digest and platform matrix,
installs only from its npm cache, and runs its matching Chromium build. It fails closed when the
bundle, trust anchor or compatible browser is absent.

## First business capability

Create a PRD with local agent tools or the optional `kt-scaffold spec` CLI, review it, change Status
to Accepted, then implement schema, backend, frontend and browser evidence from that spec path. The
workspace-bound local MCP can invoke the preinstalled generator for the verified first write; the
remote governance MCP never inspects or directly edits this repository. The local coding agent owns
every later change. See specs/README.md.

Product-facing documentation belongs under `docs/en/` and `docs/tr/`. Keep it linked to accepted
PRDs without copying engineering rules or implementation plans into a second requirements source.
