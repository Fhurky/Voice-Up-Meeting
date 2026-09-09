# Scaffolding Plan — Vibe Coding Boilerplate

**Status:** Accepted architecture, implemented on 2026-08-06. This document remains the design and
acceptance contract; executable evidence is produced by the named tests and quality gates.
**Evidence tier of this document:** L0 (written); it does not replace implementation evidence.
**Line endings:** LF. **Language:** English.

## Resolved placeholders

Every optional value left unspecified by the requester resolves to its validated default. These
values appear literally throughout this plan and in the init answer schema; init is non-interactive
and never prompts for a missing required value.

| Placeholder | Value used in this plan | Assumption |
|---|---|---|
| Project intent | Required free text | Supplied to `project_init` or with `kt-scaffold init --intent "..." --primary-domain <slug>`; stored as project context, never executed as code |
| Primary domain | Required domain slug | No generic business resource is generated; examples are `payments` and `booking` |
| Product name | `Vibe Coding Boilerplate` | Validated default; override through the tool input, CLI flag or answers file |
| Product slug | `app` | Validated default; override through the tool input, CLI flag or answers file; must be lowercase alphanumeric with hyphens |
| Backend profile | `python-fastapi` | Fixed by `technology-profile.yml`; not an init question and not selectable by a developer or coding agent |
| Persistence profile | `sqlalchemy-alembic` | Fixed with the backend; SQLAlchemy models own desired state and Alembic owns migration history |
| Environment prefix | `APP_` | Derived from the product slug (`app` → `APP_`), proposed at `/kt-init`, and overrideable. Collisions detected in the current process or target tree are reported under Requirement 6 |
| Storage engine | `postgres` | The only engine; not an `/kt-init` question. See Decision 1 |
| Authentication profile | `jwt-rbac` | Fixed default: JWT access tokens, RBAC, and one application-level `super_admin` bootstrap identity |
| API prefix | `/api/app/v1` | Default, derived from the slug |
| Tenant header | `x-tenant-id` | Neutral replacement for the vendor-prefixed reference header |
| Command namespace | `kt-` | Fixed constant, not an `/kt-init` question. See Decision 8 |
| Scaffold package and server name | `kt-scaffold` | Carries the command namespace; see Decision 8 |
| Assistant display name | `Assistant` | Only a configurable label; the in-product assistant subsystem itself is out of scope |

---

## 1. Executive summary

The Vibe Coding Boilerplate is an empty-repository starting point that hands a team a complete
engineering system rather than a starter app. It is extracted from a mature multi-tenant
monorepo — its layering, spec-first flow, test discipline, browser-verification loop,
profile-owned migration workflow and agent-governance files — with every product, company and industry payload
removed.

**What someone gets in the first hour.** They run one command in an empty directory, supply what
they are building and its primary domain, accept or explicitly override the coherent backend and
persistence profile, and receive a repository that already builds and tests
green, already runs in a container stack, and already tells three different coding agents how to
work in it. The delivered working slice is platform-only: health, login, JWT issuance, `/me`, RBAC,
an application-level `super_admin`, generated OpenAPI and client types, a localized login/home
surface, tests, and a browser scenario. No placeholder business entity is generated. The first
business vertical starts under `specs/<domain>/`, is specified and planned before implementation,
and then lands schema, API, UI and evidence together.

**Written for where it will run, from the first commit.** These projects are vibe-coded quickly, but
they ship to a Rancher-managed Kubernetes non-production cluster with no internet egress, enforced
network policy, no external-secret API, read-only root filesystems and digest-only images. Those
constraints reach back into the application — where it may write, how configuration arrives, what the
build must publish, what a service may talk to — so the scaffold satisfies them on day one rather
than after the first failed deployment. Section 12 states the contract and a chart gate enforces it
on every change, which means a team's first deployment is a configuration exercise, not a rewrite.
At run time the generated system makes no internet, SaaS, public-registry, CDN or external-telemetry
connection: frontend assets are local, images come only from the internal registry by digest, and
observability terminates in approved local or in-cluster stores.

**Two artefacts, not one.** The generator and the project it generates are separate repositories
(Decision 14). The generator — the corpus, the `kt-scaffold` package and every template — is
provisioned bank-wide as one approved package. The normal installation is a controlled wheel from
the bank's private index; a digest-pinned OCI/offline bundle supplies the same package in hermetic
or air-gapped environments. Platform management registers that installation as the local
standard-input/output `kt-scaffold` MCP server for Claude Code, Codex, Cursor and any other approved
MCP client. None of it is copied into or registered by a generated project; a scaffold records the
compatible version it was made with, the way it records its migration tool and formatter versions.

**What `/kt-init` produces.** The user opens an empty directory in Claude Code, Codex or Cursor and
calls the globally available `project_init` tool with the intent `"<what is being built>"` and a
primary-domain slug — or runs the bank-managed `kt-scaffold init --intent ... --primary-domain ...`
command with no agent at all. Missing required values are validation errors; neither surface
prompts. An agent may propose a coherent backend/persistence profile from the intent before the
single call, while unattended callers use explicit flags, `--answers`, or validated defaults. The
resolved answer object is recorded before init writes the
full tree: the rule corpus and every governance file generated from it for all three clients,
the first `specs/<domain>/` context and PRD workspace, `plans/`, the selected backend and persistence
profile, the frontend platform shell, the browser harness with one authentication scenario, the
local container stack, the deployment charts, and the
continuous integration workflows. It also writes `.kt-scaffold/`, which is what makes the scaffold
updatable rather than a one-way copy (Decision 11).

**The one structural change relative to the reference.** In the reference repository the same
rules are maintained by hand in three places — the Claude directive file, the tool-agnostic agent
file, and the editor rule files — plus a second copy inside the skills tree. They drifted, and the
divergences were real: two different commands for running the backend test suite, two definitions of
the mandatory soft-delete column set, and an API-standards skill naming a settings key the settings
object no longer used. They were found by audit and have since been corrected in the reference —
which is the point: hand-reconciled copies need an audit to stay true. This boilerplate makes that class of drift structurally impossible. There
is exactly one rule corpus. Every client file is generated from it, marked generated, and verified
by a continuous-integration job that regenerates and fails on any difference. Editing a generated
file is a defect, not a maintenance task.

---

## 2. Neutralization contract

This is the final rename map. The left column is the token as it exists in the reference; the
right column is what the boilerplate uses. Rows below the divider were found by grepping the
reference for brand, prefix and industry tokens and were not in the supplied map.

| Reference token | Boilerplate token |
|---|---|
| Reference repository name | `app-vibe-coding-boilerplate` |
| Reference product name, its short form, and its platform variant | `Vibe Coding Boilerplate` |
| Wrapper directory named after the product surface | `app/` |
| Wrapper subdirectories for backend, frontend, infra, devops | `app/backend`, `app/frontend`, `app/infra`, `app/devops` |
| Company environment-variable prefix | `APP_` |
| Application database name | `app_db` |
| Product-named API prefix | `/api/app/v1` |
| Vendor-prefixed tenant header | `x-tenant-id` |
| Company prefix on database functions and views | `app_` |
| Product-named schema project directory | `schema/core/` |
| Company-prefixed Helm chart names | `app-backend`, `app-frontend`, `app-migrate`, `app-worker`, `app-observability`, `app-postgres`, `app-redis` |
| Browser-suite base URL variable | `APP_E2E_BASE` |
| In-product assistant proper name | Configurable display name, default `Assistant` (extension point only) |
| — | — |
| Company-prefixed backend development image | `app-backend-dev` |
| Company-named database role and login | `app` |
| Browser-suite credential variables | `APP_E2E_SUPER_ADMIN_USER`, `APP_E2E_SUPER_ADMIN_PASS` |
| Browser-suite package name | `app-e2e` |
| Browser failure-artifact directory | `test-results/` |
| Editor workspace file named after the reference repository | `app.code-workspace` |
| Public-identifier generator function | `app_generate_public_id` |
| Tenant hierarchy view and permission function | `app_tenant_hierarchy`, `app_get_user_permissions` |
| Generated OpenAPI document filename | `app-api.yaml` |
| Product-named settings keys (project name, secret key, token lifetime, database name) | `APP_PROJECT_NAME`, `APP_SECRET_KEY`, `APP_ACCESS_TOKEN_EXPIRE_MINUTES`, `APP_POSTGRES_DB` |
| Industry-named seed tenant public identifier | `DemoTenant000001` |
| Platform tenant public identifier | `PlatformTenant0001` |
| Reference container names | `app-postgres`, `app-redis`, `app-backend`, `app-frontend`, `app-nginx`, `app-otel-collector`, `app-grafana` |

**Dropped outright, not renamed.** Identifier-tokenization and compact-equality database
functions (they exist only to serve the excluded catalog search); the second schema project and
its build artifacts; the industry glossary and catalog seed resources; the personal-data
classification vocabulary of the reference's regulatory regime; the analyst workspace permission
family; the reference's warehouse naming exemption and its skill; the assistant evaluation skill;
mockups; diagrams; the localization staging directory. None of these carry an engineering
invariant that survives de-branding.

**How reference paths are cited in this plan.** Sections 3 through 11 each close with a
traceability note naming the reference files an item was derived from. Those paths are written in
the **neutralized vocabulary of the table above**, not in the reference's own spelling: the
reference's product-named wrapper directory appears as `app/`, and its product-named schema
project appears as `schema/core/`. Everything below those two segments — package names, module
names, skill names, workflow names — is the reference's actual path, so anyone holding the
reference can resolve a citation by reversing exactly those two substitutions.

**The one deliberate exception: the tooling namespace.** This boilerplate is being adopted as the
company's own engineering architecture, and its command surface carries the company namespace on
purpose. `kt-` appears in exactly three places, all of them operator-facing tooling: the command
names (`/kt-init`, `/kt-gate`, …), the scaffold package and server key (`kt-scaffold`), and the
scaffold state directory (`.kt-scaffold/`). It appears nowhere in the scaffolded product — not in
the environment prefix, the wrapper directory, the database name, the API prefix, the chart names,
the container names, the settings keys or the schema identifiers. Decision 8 records the reasoning
and the single constant a fork outside the company changes.

**Test for this contract.** A reader of this plan cannot name the original product or the
industry. Grep of the scaffolded tree for the company prefix in either case, for the hyphenated
and underscored company forms, for the wrapper directory name, and for the excluded engine's name
returns nothing outside the three tooling locations named above.

---

## 3. Target directory trees

### Decision 14 — The generator is not part of what it generates

There are two repositories in this system and they were conflated in the first draft, which
produced a contradiction a reader hits immediately: the generator lived inside the tree it
generates, so `/kt-init` in an empty directory had nothing to run it with, and `bootstrap.sh` was
described as post-clone setup for a tree nobody clones.

They separate as follows.

**The generator repository** is what this plan builds: the canonical corpus, the `kt-scaffold`
package, every project template, and the tests and workflows that keep them honest. It is released
as an approved wheel through the bank's private index and as a digest-pinned OCI/offline bundle.
Whichever source provisions it, there is one bank-managed implementation exposed either as a local
stdio process or through the internal Streamable HTTP control plane. It is never copied into a
project.

**The scaffolded project** is what `project_init` or `kt-scaffold init` writes. It carries its own
corpus, its generated client files, its scripts, and `.kt-scaffold/` — and it does **not** carry the package or the
templates. It records a pinned `kt-scaffold` version in `.kt-scaffold/answers.yml`, and
`scripts/bootstrap.sh` verifies that the bank-managed installation is compatible before any project
command runs. A project does not vendor its formatter, and there is no reason for it to vendor its
generator: two copies of one package is version skew plus a second test suite, bought for nothing.

**The two MCP authority surfaces are intentionally different.** The local stdio process may be
started with one explicit empty workspace root and exposes trusted project creation plus governance.
It invokes the installed generator in-process and never downloads or executes delivered code. The
Streamable HTTP deployment is workspace-blind and exposes governance and blueprint metadata only.
There is no in-project MCP copy to keep in step.

What the project keeps is the thing that must be project-owned: `rules/`. The corpus is written by
`project_init` and from that moment belongs to the team that owns the repository — they extend it, and
`/kt-update` brings corpus improvements forward under the conflict rules of Decision 11.

### 3.1 The generator repository

```
kt-scaffold/
├── README.md                              What this produces, how to release it, how to run it offline
├── AGENTS.md, CLAUDE.md, .claude/, .cursor/, .codex/   GENERATED from rules/ — this repository dogfoods its own output
├── rules/                                 THE canonical corpus; every scaffold starts as a copy of it
├── plans/scaffolding-plan.md              This generator plan; never copied into a product scaffold
├── src/kt_scaffold/                       The package: CLI, MCP server, corpus, renderer, sandbox, update
│   └── templates/
│       ├── common/                       Governance, React frontend shell, infra and delivery
│       └── python-fastapi/               FastAPI, SQLAlchemy, Alembic, pytest
├── packaging/
│   ├── Dockerfile                         The digest-pinned OCI/offline provisioning image
│   └── offline-bundle.sh                  Builds the air-gap bundle described in section 8
├── tests/                                 Schema, transactional publish, sandbox, idempotency, update, profile and CLI parity
└── .github/workflows/                     Package tests, self-render drift, and a full scaffold-and-gate job
```

The last workflow is the one that matters: on every change it scaffolds one project per supported
backend/persistence profile into scratch directories and runs each quality gate. A template change that
would break a fresh scaffold fails here, before release, rather than in the first team that runs
`/kt-init` after it.

### 3.2 The scaffolded project

This is the tree `project_init` or `kt-scaffold init` writes. Every entry carries a one-line
description. `GENERATED` marks a file produced from the rule corpus and never hand-edited.

```
app-vibe-coding-boilerplate/
├── README.md                              First-hour path: bootstrap, quality gate, first feature
├── AGENTS.md                              GENERATED — the agent contract; the primary rule document
├── CLAUDE.md                              GENERATED — imports @AGENTS.md, then the Claude-specific delta
├── .editorconfig                          LF line endings and indent width per file type
├── .gitattributes                         Forces LF per extension; migration checksum file always LF
├── .gitignore                             Environment files, build output, caches, local data
├── .markdownlint.json                     Markdown lint configuration shared by editors and CI
├── app.code-workspace                     Multi-root editor workspace (backend, frontend, schema, tools)
├── rules/                                 SINGLE SOURCE OF TRUTH for every agent-facing rule
│   ├── README.md                          How to add or change a rule; generated files are read-only
│   ├── corpus.schema.json                 JSON Schema validating each rule's front matter
│   ├── GENERATED.lock                     Corpus digest plus digest of every emitted client file
│   ├── 00-project-overview.md             What the repository is; monorepo rationale
│   ├── 01-architecture-principles.md      Layering, dependency direction, design principles
│   ├── 02-communication-style.md          Terse answers, one question at a time, no effort estimates
│   ├── 03-workflow-hygiene.md             Version-control ownership, no self-initiated phasing, no parked work
│   ├── 10-spec-first.md                   A feature starts from an accepted PRD under specs/<domain>/
│   ├── 11-plan-driven.md                  plans/ is the pre-decision area; split scope becomes its own spec
│   ├── 12-tdd.md                          Red-green-refactor; real boundaries over loose mocks
│   ├── 13-definition-of-done.md           Evidence tiers L0 through L3 and the honesty rule
│   ├── 14-browser-verification.md         Live browser pass plus committed scenarios
│   ├── 20-backend-structure.md            Package layout, dependency injection, package initializer rule
│   ├── 21-backend-api-standards.md        REST conventions, route prefix, public-identifier-only writes
│   ├── 22-backend-configuration.md        One settings object, prefixed variables, four-surface sync rule
│   ├── 23-backend-caching.md              Canonical keys, scope in key, stampede lock, fail-open
│   ├── 24-backend-testing.md              Test layout, fixtures, mock discipline, coverage posture
│   ├── 30-frontend-structure.md           Single-page-application constraints, routing, naming
│   ├── 31-frontend-api-integration.md     Generated client types, error handling, session-expiry rule
│   ├── 32-frontend-styling.md             Design tokens, component library usage, layout primitives
│   ├── 33-frontend-localization.md        Every user-facing string localized in all configured locales
│   ├── 34-frontend-state-management.md    Context boundaries and JWT/RBAC session synchronization
│   ├── 40-persistence-source.md           The selected profile declares one schema authority; migrations are generated and reviewed
│   ├── 41-schema-mandatory-columns.md     The mandatory column block every table carries
│   ├── 42-reference-integrity.md         Physical links inside a service boundary; value references across boundaries
│   ├── 43-schema-comments.md              Comment conventions for enums, links, and overflow keys
│   ├── 44-schema-engine-boundary.md       Where engine knowledge is allowed and where it is not
│   ├── 45-deployment-target.md            The cluster contract of section 12: what every chart, image and Secret reference must satisfy
│   ├── 50-quality-gate.md                 The mandatory post-change verification sequence
│   ├── 51-metrics-before-claims.md        No performance or root-cause claim without a cited measurement
│   ├── 52-end-to-end-feature.md           The ordered end-to-end completion checklist
│   └── 53-test-run-report.md              Fixed skeleton every run result is reported in
├── .kt-scaffold/
│   ├── answers.yml                        The `/kt-init` answers, the corpus version, and the pinned generator version
│   └── manifest.json                      Per-file digests at scaffold time; what `/kt-update` compares against
├── .claude/
│   ├── settings.json                      Claude Code project settings
│   ├── rules/<nn>-<scope>.md              GENERATED — path-scoped rules, `paths:` derived from applies_to
│   └── skills/kt-<name>/SKILL.md          GENERATED — corpus skill groups and one skill per tool
├── .cursor/
│   └── rules/<nn>-<scope>.mdc             GENERATED — one editor rule file per corpus scope
├── .codex/
│   ├── config.toml                        GENERATED — agent-file and project-governance pointers only
│   └── skills/kt-<name>/SKILL.md          GENERATED — same skill bodies, Codex discovery path
├── .specify/memory/constitution.md        GENERATED — spec-kit-readable projection of the corpus
├── specs/
│   ├── README.md                          Domain-first, spec-driven workflow and naming contract
│   ├── TEMPLATE-DOMAIN.md                 Bounded context, actors, language, invariants, and boundaries
│   ├── TEMPLATE-PRD.md                    One independently deliverable capability specification
│   ├── openapi/app-api.yaml               GENERATED — exported contract; the client types are built from it
│   └── <domain>/
│       ├── DOMAIN.md                      Project-intent-derived domain context; no business code yet
│       ├── roadmap.md                     Ordered capability/spec map; may start empty
│       └── PRDs/<nnn>-<capability>/       PRD.md plus derived plan.md and tasks.md
├── plans/
│   └── README.md                          Pre-decision working documents; absorbed plans get pruned
├── e2e/
│   ├── README.md                          How to run suites and when a scenario is warranted
│   ├── QUALITY_MANIFEST.md                Surface-to-evidence matrix and the next-scenario roadmap
│   ├── package.json                       One script per suite; pinned Playwright dependency
│   ├── shared/harness.mjs                 Login, checks, reporting, environment-sourced credentials
│   └── auth/
│       ├── 01-super-admin-login.mjs      Login, JWT session, `/me`, and protected-route access
│       └── run-all.mjs                    Sequential runner reporting green file count
├── app/
│   ├── backend/                           Fixed Python/FastAPI backend
│   ├── frontend/                          Single-page application — see the frontend subtree below
│   ├── infra/                             Local container stack, reverse proxy, observability, release images
│   └── devops/                            Self-contained deployment charts and environment overlays
├── schema/
│   ├── README.md                          Common generate, review, apply, status, and validate contract
│   ├── profile.yml                        Recorded schema authority and migration adapter
│   └── migrations/                        Profile-native, generated, reviewed, append-only migrations
├── scripts/
│   ├── README.md                          Check here before writing any ad-hoc command
│   ├── bootstrap.sh                       Post-scaffold check: pinned generator, Docker and governance render available
│   ├── scaffold.sh                        Agent-free wrapper: init, update, and every generator
│   ├── quality-gate.sh                    Formatter, type check, tests, generated-artifact drift
│   ├── db.sh                              Profile adapter: generate, apply, status, validate
│   ├── render-clients.sh                  Human and CI wrapper over the client-file renderer
│   ├── render-charts.sh                   Renders every release against an overlay and applies the section 12 contract checks; `--self-test` proves each check rejects what it claims to
│   ├── export-openapi.sh                  Offline OpenAPI export from the application object
│   └── generate-types.sh                  Regenerate the frontend client types from the exported document
├── docs/
│   ├── en/README.md                       Public, end-user-facing documentation, English
│   └── tr/README.md                       Public, end-user-facing documentation, Turkish
└── .github/workflows/
    ├── backend-test.yml                   Formatter, import order, type check, unit and integration tests
    ├── frontend-test.yml                  Lint, build, unit tests
    ├── governance-drift.yml               Regenerates client files and fails if the working tree changed
    ├── schema-check.yml                   Profile-native migration validation, drift, and destructive-change checks
    ├── charts-render.yml                  Renders every release shape with fixture overlays and enforces the deployment contract (section 12)
    └── security-scan.yml                  Admission, Gitleaks, Semgrep and offline Trivy gate
```

Backend subtree:

```
app/backend/
├── Dockerfile.dev                         Development image; dependencies baked, source mounted
├── entrypoint.dev.sh                      Reload-capable entry point
├── pyproject.toml                         Formatter, import order and type-checker configuration
├── requirements.in / requirements.txt     Runtime dependencies, pinned
├── requirements-dev.in / requirements-dev.txt  Development and test dependencies, pinned
├── .env.example                           Every variable documented with a placeholder, never a secret
├── app/main.py                            Application object, middleware order, router mount, lifespan
├── app/api/router.py                      Aggregate router mounted on the configured API prefix
├── app/api/health.py                      Liveness and readiness endpoints excluded from tracing
├── app/api/auth/                          Login, token issuance, permission guards
├── app/core/config.py                     The single settings object; every key prefixed
├── app/core/request_context.py            Per-request tenant, actor, roles, permission expansion
├── app/core/security.py                   Password hashing and JWT primitives
├── app/db/base.py                         Model registry every entry point imports first
├── app/db/session.py                      Engine and session factory; the only engine-aware module
├── app/domain/models/                     SQLAlchemy schema authority for the default Python profile
├── app/infrastructure/repositories/       Async data access, one repository per aggregate
├── app/middleware/tenant_context.py       Tenant header and token parsing without a database call
├── app/schemas/                           Request and response models, one package per domain
├── app/services/                          Business logic, tenant-scoped, identifier resolution
├── app/scripts/create_super_admin.py      Interactive/env-sourced bootstrap; stores no secret in the repository
├── app/scripts/export_openapi.py          Offline OpenAPI export used by CI and the type generator
└── tests/                                 Mirrors the package layout; shared fixtures in the root conftest
```

Frontend subtree:

```
app/frontend/
├── Dockerfile.dev                         Development image with polling hot reload
├── package.json                           Development, build, lint, test and type-generation scripts
├── vite.config.ts / vitest.config.ts      Bundler and unit-test configuration
├── tsconfig*.json / eslint.config.js      Strict type settings and lint rules
├── components.json                        Component-library generator configuration
├── nginx.release.conf                     Release-image server configuration
├── nginx.security-headers.conf            Shared response-header policy
├── index.html                             Entry document; no remote asset dependency
├── src/main.tsx / src/App.tsx             Entry point and route table
├── src/globals.css                        Design tokens and base layer
├── src/components/auth/                   Authentication and permission route guards
├── src/contexts/AuthContext.tsx           JWT session, roles, permissions, super-admin flag
├── src/contexts/IntlContext.tsx           Locale selection and local JSON message catalogues
├── src/lib/apiClient.ts                   Fetch wrapper, tenant header, session-expiry discrimination
├── src/lib/authStorage.ts                 Token persistence
├── src/lib/config.ts                      Build-time configuration surface
├── src/locales/<locale>.json            One catalogue per configured locale, kept in parallel
├── src/pages/LoginPage.tsx                Real login round trip
├── src/pages/HomePage.tsx                 Authenticated platform landing surface; no fake business domain
├── src/pages/NotFoundPage.tsx             Unmatched-route surface
├── src/services/auth.ts                   Typed login and current-session API service
└── src/types/api.d.ts                     Generated from the exported OpenAPI document
```

Infrastructure and deployment subtrees:

```
app/infra/
├── README.md                              How to bring the stack up and what each service is for
├── .env.example                           Local overrides with safe defaults, no secrets
├── docker-compose.local.yml               Composed at scaffold time from the observability answer
├── nginx/nginx.local.conf                 Single local entry point serving application and API on one origin
├── observability/                         Collector, trace store, metric store, log store, dashboard provisioning — only when `/kt-init` enabled it
└── Dockerfile.{backend,frontend,migrate}.release  Release images

app/devops/
├── README.md                              The cluster contract, the release order, and the Secrets an administrator creates
├── OPERATIONS.md                          Install, promote, migrate, roll back, restore, rotate a secret
├── ACCEPTED-RISKS.md                      Risk, why accepted, compensating control, re-evaluation trigger, owner
├── images.yaml                            Bill of materials: every image the cluster runs that this repository does not build, pinned by index digest
├── charts/app-backend/                    Deployment, service, ingress, autoscaler, budget, network policy
├── charts/app-frontend/                   Static-asset deployment and ingress
├── charts/app-migrate/                    Migration job, one release per source revision, run before the dependent release
├── charts/app-worker/                     Parameterized chart for scheduled and on-demand modules
├── charts/app-postgres/                   StatefulSet, role bootstrap, backup job, and the restore and storage probes that ship disabled
├── charts/app-redis/                      Cache — authenticated, memory-bounded, no persistence
├── charts/app-observability/              Collector and dashboard release; dashboards are chart files — only when `/kt-init` enabled it
├── environments/cluster/*.yaml            Committed non-secret overlays for the target cluster, one file per release
└── environments/lab/*.yaml                The same releases on a single-node developer cluster; only environment facts differ
```

**Traceability.** The tree derives from the reference layout described in
`.cursor/rules/05-project-structure.mdc`, `CLAUDE.md` "Project Structure", the actual
`app/backend/app/` and `app/frontend/src/` trees, `schema/README.md`, `e2e/README.md`,
`scripts/README.md` and `.github/workflows/`. Generalized: the wrapper directory and every path
segment named after the product; the domain-specific backend packages collapse to one generic
domain; the eight deployment charts collapse to six that every scaffold needs plus one that follows
the observability answer, and the reference's two environment overlays keep their shape — one for the
target cluster, one for a developer cluster — because a single overlay cannot demonstrate that the
structure is environment-independent (Decision 16). Dropped: the excluded engine's estate chart, the second schema project and its build output, the industry
resource directories, the mockup and diagram directories, the localization staging directory, the
evaluation-results directories, and every workflow that only existed to build the excluded
engine's artifacts. Added, with no reference counterpart: `rules/`, `.kt-scaffold/`,
`.claude/rules/`, `.codex/skills/`, `.specify/memory/constitution.md`,
`governance-drift.yml`, `schema-check.yml`, `scripts/bootstrap.sh`, `scripts/scaffold.sh`,
`scripts/render-clients.sh` and `scripts/db.sh`. Held back in the generator repository and
deliberately absent here: the `kt-scaffold` package, its templates, and its installation and global
client-registration assets (Decision 14).

---

## 4. Architecture baseline

**Shape.** A monorepo holding one modular-monolith service, one single-page application, one
schema project, one browser-scenario project, one scaffold server, and the infrastructure and
delivery definitions for all of them. The monorepo is deliberate: an agent working on a feature
needs the schema, the service, the generated contract and the interface in one context window,
and cross-layer completion is the unit of work this system enforces.

### Decision 17 — Intent and domain come before business code

`/kt-init` begins with a required project intent and a primary domain. It creates the selected
platform profile plus `specs/<domain>/DOMAIN.md`, `roadmap.md`, and an empty `PRDs/` directory. It
does not invent a generic entity or CRUD surface. A business vertical may be generated only from an
accepted `specs/<domain>/PRDs/<nnn>-<capability>/PRD.md`; its derived `plan.md` and `tasks.md` live
beside it. Every domain generator takes that `spec_path` as a required input. This keeps the CLI
deterministic while letting the vibe coder choose the stack and first vertical from explicit intent.

**Backend layers and dependency direction.** Dependencies point inward and never reverse.

```
api/            HTTP surface: routing, guards, request and response models, dependency providers
  ↓
services/       Business logic, tenant scoping, public-identifier resolution, cross-aggregate rules
  ↓
infrastructure/ Repositories, security primitives; the only place raw queries live
  ↓
domain/         Persistence models and enumerations — depends on nothing above it
```

`core/` (typed settings, request context and security primitives) and `db/` (registry and session)
are cross-cutting and may be imported by any layer; they import nothing from `api/` or `services/`.
`middleware/` sits outside the request handler and populates the request context. Cache,
observability and worker application adapters are deliberately absent until an accepted PRD needs
their call surface; their local/deployment infrastructure sockets do not manufacture domain calls.

**Frontend layers.**

```
pages/          Route-level composition and data orchestration
  ↓
components/     Presentational and interactive pieces; the generated primitives live under ui/
  ↓
services/       Typed API calls aligned with the generated OpenAPI contract
  ↓
lib/            Client, storage, formatting, configuration
```

`contexts/` provides session and locale to the whole tree. Generated pages call their domain service
instead of building requests by hand; committed OpenAPI/type drift checks keep that typed boundary
aligned with the backend contract.

**Inter-service communication rule.** Services communicate over HTTP only. There is no message
broker, no cross-database query, no federated table, no database link. Each service connects to
its own database; references across a boundary are carried by value. Background work is scheduled
or on-demand modules invoked as commands against the service image, not queue consumers. This is
kept from the reference because it is what makes the bounded contexts real rather than nominal —
and because it is what keeps a bounded context's data private to the service that owns it.

### Decision 20 — Authentication defaults to JWT, RBAC and application super-admin

**Multi-tenancy and authorization.** The default is intentionally small: signed JWT access tokens,
RBAC, and one application-level `super_admin` identity. The active tenant travels in the configured
tenant header. Ordinary users are checked against their token's tenant and role claims;
`super_admin` may enter any tenant and bypass application permission checks. Endpoint guards use
`require_permission("<domain>:<action>")` and `require_super_admin()`. The first administrator is
created after scaffolding by an interactive or environment-sourced bootstrap command; its password
is never written to `.kt-scaffold/`, an example file, or version control. This is application
authority only: containers stay non-root, the runtime database role is not a database superuser,
and no Kubernetes cluster-admin permission is introduced.

The baseline browser harness and generated domain fixtures authenticate as `super_admin`, so setup,
exercise and teardown are never blocked by an incomplete permission seed. A domain PRD may add
restricted-role scenarios when authorization behavior is itself under test; the scaffold does not
force them into every feature.

**Traceability.** Derived from `CLAUDE.md` "Architecture Principles", "Multi-Tenancy & Auth" and
"Inter-Service Communication"; `app/backend/app/` layer directories;
`app/backend/app/core/request_context.py`; `app/backend/app/middleware/tenant_context.py`;
`app/backend/app/api/auth/permissions.py`; `app/backend/app/db/base.py`;
`.cursor/rules/01-coding-principles.mdc`. Generalized: the role ladder collapses to RBAC plus an
explicit `super_admin` bypass. Dropped: the
read-only analytical session and everything that depended on it, and the assistant capability and
approval machinery.

---

## 5. Technology stack

| Component | Technology | Rationale | Core or optional |
|---|---|---|---|
| Backend | Python 3.13, FastAPI, Pydantic, async SQLAlchemy/`asyncpg`, Alembic, pytest | One fixed Python/PostgreSQL path; Node.js backends and alternative Python web frameworks are not selectable | Core |
| Storage engine | PostgreSQL major pinned by the profile BOM | The only engine; upgrades arrive as reviewed profile releases, not a `latest` lookup | Core |
| Persistence/migrations | SQLAlchemy model authority with generated, reviewed, versioned Alembic migrations | Fixed rather than selected at init | Core |
| Authentication | JWT access tokens + RBAC + application-level `super_admin` | Simple local baseline; no refresh-token subsystem or external identity provider | Core |
| Cache socket | Redis local service and chart, never a system of record | No cache adapter or call site exists in the platform slice. The first accepted PRD that needs caching must add a profile-native adapter, canonical scoped keys, stampede protection and tests together — Requirement 2 | Infrastructure socket |
| Frontend build | Pinned Vite 8, React 19 and TypeScript 7 native checker in strict mode; TypeScript 5.9 is retained only as the supported `openapi-typescript` peer | Separated client-side SPA; SSR and Next.js are forbidden, and the contract generator never relies on an unsupported peer override | Core |
| Chat-only full-stack exception | Streamlit | Allowed only when the accepted PRD limits the whole UI to prompt input, chat and history; not mixed into the React/FastAPI tree | Conditional mode |
| Server streaming | FastAPI SSE | Allowed for one-way streams such as LLM token delivery; auth, tenant and disconnect handling remain mandatory | Core capability |
| Routing | Pinned React Router 8 client-side routing | Matches the single-page constraint; no server-framework routing idioms | Core |
| Styling | Repository-local CSS design tokens and components | No runtime CDN, font host or generator dependency; the small baseline stays reviewable and offline | Core |
| Localization | Local JSON catalogues behind a React locale context; the locale set is chosen at `/kt-init`, proposed English and Turkish | Every generated user-facing string is a message identifier and each configured catalogue is updated together | Core |
| Client types | OpenAPI-to-TypeScript generation | Makes contract drift a build failure rather than a runtime surprise | Core |
| Forms | Native controlled React inputs in the baseline | The login form stays dependency-light; a domain may select a form library only through its accepted PRD and offline BOM | Core |
| Backend tests | pytest | Fixtures and real-boundary PostgreSQL integration tests | Core |
| Frontend tests | Vitest with a lightweight DOM | Fast unit coverage of components and services | Core |
| Browser scenarios | Playwright driven from plain Node scripts | Committed, reviewable scenarios that drive the real stack; no test-runner abstraction between the scenario and what a user does | Core |
| Live verification during development | The same plain Playwright scenarios used by the permanent E2E suite | Keeps browser evidence client-neutral and avoids a second MCP server. The Playwright package is lockfile-pinned and the matching Chromium tree is carried in the platform-specific offline bundle (Requirement 11) | Core |
| Scaffolding and rule distribution | One bank-managed `kt-scaffold` Python implementation, globally exposed through local stdio or internal Streamable HTTP; the same package provides its command-line surface | See section 8 and Decision 10 | Core |
| Governance file formats | `AGENTS.md`, Claude Code `.claude/rules/` with `paths:` front matter, Agent Skills `SKILL.md`, Cursor `.mdc` | Each client's own native mechanism, all emitted from one corpus; no format is invented here | Core |
| Scaffold provisioning | Controlled wheel/private index or digest-pinned OCI/offline bundle | Two approved sources provision the same bank-global package; neither a generated project nor a client-native governance file installs it | Core |
| Offline bundle | A build-time script producing wheels, npm cache, the matching Playwright Chromium tree, and OCI image tarballs | What makes all four tiers of Decision 15 executable on each admitted platform matrix | Core |
| Local stack | Docker Compose with a single reverse-proxy entry point | One origin serves application and API, so the client's relative paths work exactly as they do in a deployed environment | Core |
| Observability | OpenTelemetry to a local collector, with trace, metric and log stores behind one dashboard | Egress-free by construction; exporters terminate only in approved local or in-cluster stores | Init option; defaults enabled and can be explicitly disabled |
| Runtime network boundary | No internet, SaaS, public registry, CDN or external telemetry | Assets are bundled locally, images are internal and digest-pinned, and no runtime component calls an external service | Core |
| Deployment | Self-contained Helm charts, digest-pinned images, committed non-secret overlays, targeting a Rancher-managed Kubernetes non-production cluster with no egress | The deployment target is fixed at scaffold time rather than discovered later — see section 12. One chart per workload, no shared library chart, no vendored dependencies; a tag never decides what runs | Core |
| Continuous integration | GitHub Actions | Six focused workflows rather than one monolith | Core |
| Static analysis | Semgrep, rules pinned by admitted snapshot digest | Runs in `security-scan.yml` and locally through `scripts/security-gate.sh` | Core |
| Image, filesystem and configuration scanning | Trivy | Covers the container images, the lockfiles and the chart values in one scanner | Core |
| Dependency updates | Bank-managed GitHub Enterprise Dependabot against internal mirrors | The generated configuration is inert without that internal service. Proposals never admit themselves: `dependency-admission.json`, its separately reviewed observability-on/off inventory digests and the offline gate remain authoritative | Core |
| Secret scanning | Forge-native push protection plus a pre-commit hook | A secret that never lands is cheaper than one that has to be rotated | Core |

### Technology authority and scope

`technology-profile.yml` is the authority for this unit's vibe-coding track. External BOA, IAM and
enterprise application-framework rules are outside this project scope and are not imported as
constraints or exceptions. The architecture agent blocks technologies listed under `forbidden` and
does not infer alternatives from project intent.

The default is a React/Vite SPA separated from Python/FastAPI. SSR and Next.js are prohibited. SSE is
allowed for one-way server streaming. The only full-stack exception is the Streamlit
`chat-only-fullstack` mode, and an accepted PRD must prove that the UI is limited to prompt input,
chat responses and history.

**Traceability.** Derived from `CLAUDE.md` "Tech Stack", `.cursor/rules/02-infrastructure.mdc`,
`app/backend/requirements.in`, `app/frontend/package.json`, `e2e/package.json`,
`app/infra/docker-compose.local.yml` and `app/devops/charts/`. Generalized: observability becomes an
`/kt-init` answer that adds or removes the egress-free infrastructure bundle; application signal
call sites remain capability-owned rather than an empty baseline abstraction. External error
tracking is dropped rather than left as an unwired runtime seam. Dropped: the second database engine and its driver, the SQL parsing library that
existed only to guard that engine, the self-hosted model runtime, and the file-backed storage mode.

---

## 6. Persistence contract

PostgreSQL is the only storage engine. SQLAlchemy models are the one desired-state authority and
Alembic is the one tool that turns that source into a reviewed migration.

### Decision 1 — One engine and one persistence authority

Engine knowledge stays inside the persistence adapter and repository layer. Public
identifiers are application-generated and internal numeric identities never cross the API boundary.
Physical foreign keys are the default inside one service/database boundary; references to another
service or bounded context are carried by value and validated at the owning service boundary.
**Requirement 1:** engine behavior above that boundary fails the profile gate.

**Only the cache infrastructure socket ships.** Redis is available in local Compose and the
deployment chart, but the backend does not invent an application cache abstraction or call site.
A domain introduces its adapter, canonical key builder, stampede protection and
tests deliberately from an accepted PRD. **Requirement 2:** the fresh platform baseline has no cache
call site; any later adapter and call site link to the accepted PRD that requested them.

### Decision 18 — Persistence is fixed, not selected

`/kt-init` exposes no backend, ORM, database, or migration-tool choice. The fixed chain is Python,
FastAPI, async SQLAlchemy/asyncpg, PostgreSQL and Alembic. `.kt-scaffold/answers.yml` records those
values for audit and update compatibility, while `technology-profile.yml` owns the decision.

Change the declared SQLAlchemy authority, generate a versioned Alembic migration, inspect its
SQL/destructive effects, apply locally, validate drift, and commit the authority plus migration
together. Custom Alembic migrations may move data that model metadata cannot express, but
hand-written schema migrations are not the default path.

### Decision 2 — The mandatory column block

Every table carries the same block.

| Element | Definition |
|---|---|
| Identity primary key | `<table>_id`, identity column generated by default, never crosses the API boundary |
| Public identifier | `public_id TEXT NOT NULL UNIQUE` on resource tables; junctions, mappings, locale sidecars and append-only streams use their natural key instead |
| Overflow column | `props`, native binary JSON, defaulting to an empty object |
| Audit quad | `created_at`, `updated_at`, `created_by`, `updated_by` |
| Soft-delete triplet | `is_deleted`, `deleted_at`, `deleted_by` |
| Partial active index | An index restricted to rows where `is_deleted` is false |
| Timestamps | Timestamp with time zone; the database runs in UTC. Naive values are rejected by `db/codec.py`, never silently localized |
| Descriptions | A table description and descriptions for important enumerations, links and overflow keys, emitted through the selected profile or a reviewed SQL migration |

The block is encoded once as a SQLAlchemy mixin/helper and tested against the migrated PostgreSQL
schema.

### Migration workflow

1. Edit the SQLAlchemy model authority.
2. Generate the migration: `scripts/db.sh generate <migration_name>`.
3. Read the generated migration. Check for unintended drops, missing indexes and constraints,
   unsafe type changes, and missing defaults.
4. Apply locally: `scripts/db.sh apply`. Local only — deployed environments apply through the
   migration release, never from a developer machine.
5. Run `scripts/db.sh validate` and `scripts/db.sh status`.
6. Commit the schema authority and the migration together.

**Requirement 3:** every scaffold records SQLAlchemy/Alembic as its one schema authority and
migration adapter. A schema migration with no corresponding authority change fails the drift check. Destructive
statements require the requester's literal destructive verb in every environment, local included.

### Commands

| Step | Command |
|---|---|
| Bring the stack up | `docker compose -f app/infra/docker-compose.local.yml up -d` |
| Prepare the schema | `scripts/db.sh apply` |
| Backend and frontend gates | `scripts/quality-gate.sh all` |
| Bootstrap super admin | `scripts/create-super-admin.sh` (interactive, or credentials supplied only through the process environment) |
| Browser scenario | `KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth` |

**Traceability.** The common lifecycle derives from the reference's schema workflow. SQLAlchemy and
Alembic are explicit fixed requirements. The excluded analytical engine and its product-specific
guardrails remain out of scope.

---

## 7. Agent governance

### The problem being solved

In the reference, the same rule is written by hand in up to four places: the Claude directive
file, the tool-agnostic agent file, the editor rule file for that concern, and the skill for that
concern. The reference acknowledges the risk and resolves it by declaring the skill authoritative
on conflict. That is a convention, and it did not hold. An audit of the reference found six
divergences at once: two different backend test commands, two definitions of the mandatory
soft-delete column set, a settings key named as it no longer existed, a documented message-file
layout the application did not use, a command pointing at a script that was not there, and three
frontend skills with no editor-rule mirror. All were corrected afterwards. Every one was a
maintenance failure, not an authoring failure — which is why the fix here is structural.

### Decision 5 — One corpus, everything else generated

`rules/` holds the corpus. One rule is one file. Each file carries machine-readable front matter
validated against `rules/corpus.schema.json`:

| Field | Meaning |
|---|---|
| `id` | Stable identity, referenced by generated files and by tools |
| `title` | One-line statement of the rule |
| `scope` | `governance`, `process`, `backend`, `frontend`, `schema`, `deployment`, `quality` |
| `trigger` | `always`, `path-match`, or `on-demand` |
| `applies_to` | Glob patterns the rule governs; empty means repository-wide |
| `priority` | Ordering weight within a scope; lower sorts first |
| `clients` | Which client files this rule is emitted into |
| `skill` | The skill group this rule belongs to when emitted as a skill |
| `gate` | The gate that enforces it, or `none` when it is guidance |

The body is the rule prose in Markdown — the same text that today lives duplicated.

One more front-matter field settles which rules a given scaffold receives: `applies_when` names the
backend profile, persistence profile or observability answer a rule depends on, and `project_init` omits any rule whose
condition the scaffold does not meet. A scaffold that declined observability therefore ships no
tracing rule, because a rule about a component that is not there teaches agents that rules are
optional.

### Decision 8 — One command namespace, `kt-`, fixed for every scaffold

Every command this system emits is prefixed `kt-`: `/kt-init`, `/kt-gate`, `/kt-done`, and the rest
of the table in section 8. The package, the MCP server key and the scaffold state directory carry
the same token — `kt-scaffold`, `.kt-scaffold/`.

Three things follow from it, and each was a reason to choose it:

1. **Collisions stop being a question.** `/init` is a built-in of Claude Code and the behaviour when
   a project skill claims a built-in's name is undefined. A namespace removes that class of problem
   for every command, including the ones added later, rather than one name at a time.
2. **One muscle memory across every repository.** The product slug changes per scaffold; the
   toolchain does not. An engineer moving between two of this company's repositories types the same
   commands in both, and a command that starts with `kt-` is unambiguously this system's rather than
   another globally managed command's or another framework's.
3. **Coexistence with the tools already in use.** spec-kit occupies `/speckit.*`, and skill
   systems and client built-ins occupy short generic names. A namespaced surface can sit beside them in one
   repository without either side being renamed (Decision 13).

The prefix is a constant in the renderer, not an `/kt-init` question — asking would produce
inconsistent namespaces across a fleet, which is the opposite of the point. A fork outside the
company changes that one constant and regenerates.

**Scope limit.** This is the only place the company token appears. It never reaches the scaffolded
product: the environment prefix, the wrapper directory, the database name, the API prefix, the
chart names, the container names, the settings keys and the schema identifiers all stay slug-derived
per the neutralization contract in section 2.

### Decision 9 — Every client is served through its own native mechanism, not a lowest common denominator

The first draft of this plan emitted one condensed directive file per client. That was wrong on two
counts, and both are properties of the clients as they exist today rather than matters of taste.

**A directive file is not a rule store.** Claude Code loads `CLAUDE.md` in full at the start of
every session and its own documentation targets under 200 lines, because longer files consume
context and measurably reduce adherence. A corpus of thirty-plus rules condensed into one file
fails that target on the day it is generated, and it puts backend rules in front of an agent
editing a locale catalogue. Claude Code's path-scoped rules directory exists for exactly this:
`.claude/rules/*.md` accepts a `paths:` front-matter list and loads a rule only when the agent
touches a matching file. The corpus already carries `applies_to`, so the mapping is mechanical.

**Two full copies of the same prose is the drift problem in miniature.** `AGENTS.md` is the
cross-tool contract and `CLAUDE.md` is Claude Code's; Claude Code does not read `AGENTS.md`, and
the documented way to make one serve both is an `@AGENTS.md` import at the top of `CLAUDE.md`. The
generator emits the contract once and imports it, so the Claude file holds only what is genuinely
Claude-specific.

The emission map that follows from this:

| Generated artifact | Built from | Shape |
|---|---|---|
| `AGENTS.md` | Rules with `trigger: always` whose `clients` include the agent contract | The primary document: non-negotiable rules, where things live, definition of done. Every other client either reads it or is generated from the same corpus |
| `CLAUDE.md` | The `@AGENTS.md` import plus rules marked Claude-specific | Import line, then the Claude-only delta: plan-mode conventions, the skill index, the command list. Under 200 lines by construction (Requirement 8) |
| `.claude/rules/<nn>-<scope>.md` | Rules with `trigger: path-match`, grouped by `scope` | One file per scope, `paths:` front matter derived verbatim from `applies_to`; loads only when the agent opens a matching file |
| `.claude/skills/kt-<skill>/SKILL.md` | Rules with `trigger: on-demand`, grouped by `skill` | One skill per group. `description` from the group title, `paths` from `applies_to`, `user-invocable: true` |
| `.claude/skills/kt-<command>/SKILL.md` | The tool surface in section 8 | One skill per tool, `disable-model-invocation: true` and an `argument-hint`, so it is a command the operator types and never something an agent fires on its own |
| `.codex/skills/kt-<name>/SKILL.md` | The same two skill sets | Identical bodies at Codex's discovery path. The Agent Skills format is a published open standard both clients read, so this is a copy of one rendering, not a second rendering |
| `.cursor/rules/<nn>-<scope>.mdc` | Rules grouped by `scope` | One file per scope, with the description and always-apply flag derived from `trigger` |
| `.codex/config.toml` | The agent-file and project-governance pointers | Project governance only; the bank-managed global MCP registration is outside the generated repository |
| `.specify/memory/constitution.md` | Rules with `trigger: always`, in corpus order | A read-only projection for spec-kit users. See Decision 13 |

Every generated file opens with a banner naming the generator and stating that hand edits are
lost. `rules/GENERATED.lock` records the corpus digest and the digest of every emitted file.
These client-native rules and skills are governance projections inside the generated project. They
tell each client how to work in that repository; they neither install nor distribute `kt-scaffold`
and they never replace the bank-managed global stdio registration.

**Precedence.** Within a generated file, `priority` orders the content. Across files, there is no
precedence question left to answer, because there is only one source. The reference's
"the skill wins on conflict" rule disappears, because conflicts cannot be authored.

**Requirement 7 — no generated command may collide with a client built-in.** Claude Code ships
`/init` among others, and the behaviour when a project skill takes a built-in's name is not
specified by that client. Two controls make the question moot: every command this boilerplate emits
carries the `kt-` namespace (Decision 8), and the renderer additionally holds a reserved-name list
per client and fails rather than emitting a colliding skill directory.

**Requirement 8 — the generated `CLAUDE.md` stays under 200 lines**, counting the import line and
not the imported file. The renderer fails if it would exceed it, which forces the overflow into
`.claude/rules/` where it belongs rather than letting the directive file grow silently.

### Drift protection

`governance-drift.yml` runs the renderer in check mode on every pull request and every push to a
protected branch. It regenerates every client file into the working tree and fails if anything
changed, printing the differing paths. The same check is available locally through
`scripts/render-clients.sh --check` and through the `clients_render` tool in check mode. A rule
change is therefore a two-file commit — the corpus file and the regenerated outputs — and a
hand-edited generated file cannot survive review. The same job asserts Requirements 7 and 8, so a
colliding command name and an over-length directive file fail in the same place drift does.

**Traceability.** Derived from `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.mdc`,
`app/backend/.claude/skills/*`, `app/frontend/.claude/skills/*`,
`app/backend/.cursor/rules/*.mdc`, `app/frontend/.cursor/rules/*.mdc`, `.codex/config.toml`
and `.claude/settings.json`. Generalized: the union of all rule content across those files becomes
one corpus, and the "skill is authoritative on drift" convention becomes a generation contract
plus a CI gate. Dropped: every rule whose subject is the excluded product — the analytical surface,
the assistant capabilities and approval machine, the industry data conventions, and the
warehouse exemption.

---

## 8. Command layer

The `kt-scaffold` package serves the rule corpus and the generators to Claude, Codex and Cursor
identically, which is what makes the single-source design usable rather than merely tidy. The
reference has no command layer at all; this section is net-new.

### Decision 10 — One package, separate local-creation and remote-governance surfaces

The bank provisions one approved `kt-scaffold` build. Fully offline workstations and runners launch
it locally over stdio with an explicit fixed workspace root; centrally connected clients use the
internal Streamable HTTP URL through the bank OAuth/TLS gateway for governance only. Generated
repositories do not carry a second server configuration.

The local stdio creation tool reads one validated answer object and invokes `project_init`
in-process. It uses no shell, download, archive or runtime-delivered executable. The CLI remains the
equivalent unattended automation path. The HTTP plane cannot create or mutate a workstation tree.

| Layer | What it is | Status |
|---|---|---|
| `kt_scaffold` package | The generators, corpus reader, renderer, sandbox and update engine | The single mechanism |
| Bank-managed local stdio MCP | Six bilingual operation pairs | Trusted creation bound at process startup plus governance |
| Internal Streamable HTTP MCP | Five bilingual operation pairs | Workspace-blind blueprint and governance surface |
| `kt-scaffold` and generated project scripts | The command-line surface, usable with no agent and in CI | Primary operator and automation surface |
| Generated client-native rules and skills | Repository governance projected from the project corpus | Guidance only; never an installation or server-registration channel |

Every caller submits one complete validated input object. An agentic client may help its user form
that object before invoking the globally listed tool, but the server itself does not run a prompt
loop. The command line is likewise unattended: it accepts explicit flags or an answers file and
fails validation when `intent` or `primary-domain` is absent.

**Requirement 9 — local ownership.** The installed local generator owns deterministic initial bytes
and the local MCP process is bound to its target path at startup. The trusted local MCP and CLI share
the same `project_init` implementation. Governance updates remain semantic local reconciliation
rather than remote mutation.

### Transport and metadata delivery

- **Local stdio:** launched by the client with `--workspace-root`; exposes creation and governance
  without network or executable delivery.
- **Streamable HTTP:** served at `/mcp` behind the internal OAuth 2.1/TLS gateway. The application
  binds loopback only and refuses a direct non-loopback listener.
- **Separated schemas:** the local surface lists six bilingual pairs; HTTP lists the five governance
  pairs. Neither tool accepts `target_dir`, caller source, workspace snapshots, database data or
  code-execution consent. The target exists only in the local process launch configuration.
- **No SSE and no client plugin:** the URL is standard MCP Streamable HTTP. Generated repositories
  register neither transport.

Generated projects persist `.kt-scaffold/project-manifest.json`: profiles, locales, blueprint and
governance versions plus content-addressed artifact inventory. Its standard-library exporter reads
only that file and caps it at 256 KiB. MCP requests are capped at 1 MiB. Initial creation renders
from the server's canonical templates; the server never walks or reconstructs a caller project.

### Decision 19 — Init writes once, transactionally; project intent replaces trial scaffolds

`project_init` has no dry-run mode. It requires a project intent and primary-domain slug, refuses a
non-empty target, renders into a sibling staging directory, validates the complete result, and
publishes it through a journaled transaction. A failure or interrupted retry rolls back the
init-owned paths and leaves no partial repository. Other
generators also write directly but refuse conflicts; `/kt-update` applies safe untouched files and
reports edited-file conflicts without overwriting them.

### Security envelope

| Control | Behavior |
|---|---|
| Write sandbox | Writes go only to the resolved target root. Init renders and validates in a sibling staging directory before a journaled publish; generators use atomic file replacement and revalidate the root identity immediately before publish |
| Traversal | Parent-directory segments, absolute inputs in relative-path arguments and symbolic-link components in managed write paths are rejected outright |
| Version control | The server never runs version-control commands. It writes files; the human stages and commits |
| Idempotency | Re-running a generator with the same inputs reports every file as unchanged and writes nothing |
| Destructive operations | The server never deletes. Existing or edited files are conflicts unless a command-specific explicit overwrite is supported and supplied |
| Secrets | The server writes only example environment files with placeholder values. It never reads or writes a real environment file |
| Remote isolation | MCP accepts bounded project metadata and reconciliation decisions only; source, secrets and database data remain local |
| Update authority | Mandatory behavior cannot be rejected or weakened; recommended and project-owned artifacts retain explicit local decision rights |
| HTTP exposure | The MCP process binds loopback; the bank gateway owns TLS/mTLS, OAuth audience/scopes, request limits and audit identity |

### Tool surface

MCP tools return the stable envelope:

```
{ ok: boolean,
  changes: [],
  warnings: [ string ],
  next_steps: [ string ] }
```

The local and remote MCP surfaces are intentionally narrow:

| Tool | Command | Input | Output beyond the envelope |
|---|---|---|---|
| `project_blueprint` | Product intent and selected profiles | Architecture, directory contract and bounded `ProjectMetadata` |
| `project_create` (local stdio only) | The same validated initial answer object | Local-observed status, counts and verified expected/observed tree digests |
| `governance_catalog` | Optional kind, authority and scope filters | Artifact metadata without bodies |
| `governance_artifacts_get` | Explicit artifact IDs | Selected canonical bodies only |
| `governance_update_check` | `ProjectMetadata` | Deterministic intent-level `GovernanceUpdateProposal` |
| `reconciliation_validate` | Proposal and local decisions | Authority-aware local-agent-attested receipt |

The local `/kt-*` skills are workflow guidance. They use the trusted local MCP or CLI; they never
imply that the remote governance plane can inspect, mutate or execute the repository.

**Every skeleton tool emits its test alongside the artifact, and the artifact already obeys the
conventions.** `backend_domain_new` writes the persistence model with the mandatory column block
already reflected, the repository, the tenant-scoped service, the request and response models with
public-identifier-only writes, the endpoint package with its dependency providers and permission
guards, the registry entry, and a test module covering the happy path, the tenant-isolation edge
and soft-delete behavior. `frontend_page_new` writes the page, its typed contract-aligned service,
the route registration, message keys in every configured locale, and page/service unit tests.
`browser_scenario_new` writes a numbered scenario against the shared harness, registers it in the
suite runner, adds the package script if the suite is new, and appends the surface row to the
quality manifest. Backend and page generators are gate-ready; a generated browser scenario is
intentionally fail-closed until its acceptance prose is replaced by real browser assertions.

`schema_change_prepare` records the accepted-PRD request, identifies the profile-owned authority
files and returns the native generator command. It never fabricates an empty or prose-derived
migration and never executes SQL through MCP. The domain flow changes the desired-state authority;
the developer then generates, reviews and applies the candidate migration through `scripts/db.sh`.

### Decision 11 — A scaffold is a living relationship with the corpus, not a one-way copy

The first draft treated `/kt-init` as a single write: answer the questions, receive a tree, and
the boilerplate's job is done. That reproduces the failure that separates copy-once scaffolding from
the tools that replaced it — a template evolves, and every project generated before the change is
frozen at the version that made it. For a boilerplate whose entire premise is that governance drift
is unacceptable, freezing twenty repositories at January's corpus while the corpus improves in
March is the same defect at fleet scale.

`/kt-init` therefore writes two files that make the tree updatable:

- **`.kt-scaffold/answers.yml`** — the intent and resolved structured answers, plus the corpus version and package
  version that produced the tree. This is what lets a later run re-render without asking again.
- **`.kt-scaffold/manifest.json`** — the digest of every file as written. This is what distinguishes
  a file the team has since edited from one still exactly as generated.

`/kt-update` replays the answers against the newer corpus and classifies every file against the
manifest:

| File state | What `/kt-update` does |
|---|---|
| Generated, untouched since scaffold | Regenerated in place |
| Generated, edited by the team | Left alone; reported in `conflicts[]` with the diff it would have applied |
| Not generated by the scaffold | Never touched, never reported |
| New in the corpus since the recorded version | Created |
| Removed from the corpus since the recorded version | Reported in `manual_steps[]`, never deleted — the server does not delete (security envelope) |

**Requirement 10 — no silent overwrite and no silent skip.** An update reports every file in one of
those five states; a file that is neither applied nor listed as a conflict is a defect. Safe changes
are atomic and conflicts always carry the proposed diff.

What this deliberately does not attempt: merging a team's edits with the corpus's. A conflict is
reported with both sides and resolved by a human. Three-way automatic merge over hand-edited
application code is a class of tool this plan is not building.

**Decision 6 — `done_report` is advisory, not blocking.** When the claimed tier is not supported by
observed evidence, the tool reports the gap — `tier_supported` below `claimed_tier`, every shortfall
enumerated in `missing[]`, and a `verdict` naming both — and returns `ok: true`. It does not refuse,
and it has no override argument to design around. The reasoning: a blocking gate would fire hardest
exactly where it is least useful — a machine with no stack up, an environment with no browser — and
the predictable response to a gate that fires on the wrong thing is that people route around it. The
honesty this methodology needs is that the shortfall is *stated*, and a report that says
"claimed L2, supported L1, browser suite not run" carries that whether or not the tool also blocks.
What keeps it from being decorative is that the gap lands in the hand-off summary through the
run-report skeleton, where a reader sees it without opening the tool output. Requirement 5: an
unsupported tier claim always appears in `missing[]` and always reaches the hand-off summary; it is
never downgraded silently to match the evidence.

**Both verification tools return their result already shaped as a run report.** `report_skeleton`
is the fixed structure defined by `rules/53-test-run-report.md` and described in section 9.
Local `quality_gate phase=execute` requires explicit `allow_project_code_execution: true` after the
target has been trusted, then fills sections 1 and 2 from what it actually observed. HTTP uses
`prepare` to bind the exact command to workspace and gate hashes, followed by `finalize` to parse
the caller-run marker output; that evidence is labelled `client-reported`, never server-observed.
`done_report` returns each entry of `missing[]` as a numbered open item and any
unsupported tier claim as a defect item carrying the decision marker. Filling section 3 is the
agent's work; choosing its shape is not. `scripts/quality-gate.sh` prints the same two pre-filled
sections, so the format survives the degraded mode with no server running.

### Client registration and per-client surface

| Client | Project governance it reads | Command surface | Bank-managed global registration | Check after clone |
|---|---|---|---|---|
| Claude Code | `CLAUDE.md` (which imports `AGENTS.md`) plus `.claude/rules/*.md` by path | Globally listed `kt-scaffold` tools; `.claude/skills/kt-*/SKILL.md` supplies repository guidance | Internal HTTP URL or local stdio command | `scripts/bootstrap.sh` validates local prerequisites; transport conformance validates the tool listing |
| Codex | `AGENTS.md` plus `.codex/skills/kt-*/SKILL.md` | Globally listed `kt-scaffold` tools | Internal HTTP URL or local stdio command | Same check |
| Cursor | `AGENTS.md` plus `.cursor/rules/*.mdc` by glob | Globally listed tools; CLI remains an optional fallback | Internal HTTP URL or local stdio command | Same check |
| Other approved MCP clients | `AGENTS.md` or a future corpus projection where supported | The same globally listed six bilingual operation pairs | The same internal URL or stdio executable in the client's global form | Generic MCP conformance compares the same schemas and bundle digests |

Cursor reads `AGENTS.md` natively but ignores its front matter, so the glob-scoped rules stay in
`.mdc` where that client can act on them. Skills for Cursor are an extension point rather than a
shipped artifact: the standard is published and the client is listed among its adopters, but the
discovery path is not something this plan will assert without verifying it against the client in
hand.

`scripts/bootstrap.sh` runs after a scaffold and after any clone of it. It confirms the pinned
generator version is compatible with the bank-managed installation, checks Docker availability and
runs the governance renderer in check mode, which validates the corpus and its projections. Global
stdio schemas are verified separately by the managed-client conformance matrix. If the package is
missing or incompatible bootstrap stops; it never downloads a dependency while checking a project.

### CLI operation without an MCP client

This is a supported automation and recovery configuration (Decision 10). The rules stay readable as
plain files: `rules/*.md` is Markdown with front matter, and `AGENTS.md`, `CLAUDE.md`,
`.claude/rules/`, the skill files and the editor rule files are all committed. The command line
exposes every tool from the same installed package without requiring an agent.

| Capability | Without the server |
|---|---|
| `project_init` | `kt-scaffold init --intent "..." --primary-domain <slug>` from the controlled global installation or the OCI/offline wrapper; it validates intent, domain and profiles before accepting the single write |
| `scaffold_update` | `kt-scaffold update`, same classification and the same conflict report |
| `clients_render` | `scripts/render-clients.sh`, the same renderer |
| `quality_gate` | Explicit project-code consent, then `scripts/quality-gate.sh`, the same sequence and the same pre-filled report skeleton |
| `schema_change_prepare` | `kt-scaffold schema` records the accepted-PRD request and returns the profile-native command; after the desired-state authority changes, `scripts/db.sh generate` creates the candidate migration |
| `spec_new`, the skeleton generators, `done_report` | `kt-scaffold <subcommand>`, identical arguments |

Requirement 9 is what makes this table short: the scripts and the tools call the same package, so
either path produces byte-identical results. What is lost without an MCP client is structured tool
discovery; the non-interactive command line performs the same argument validation while consuming
explicit flags or an answers file.

### Provisioning — Decision 12

Three controlled provisioning paths, one implementation, one `project_init`. No path reimplements a
capability or adds a client-specific plugin.

| Path | How platform management provisions it | MCP transport | Offline | Default for |
|---|---|---|---|---|
| **A · Internal MCP plane** | Deploy the approved package loopback-bound beside the bank OAuth/TLS gateway; clients register one internal `/mcp` URL | Streamable HTTP blueprint and governance only | Internal-network only | Managed developer workstations with central connectivity |
| **B · Controlled Python package** | Install the approved wheel and locked dependencies from the private wheelhouse into the managed global environment | Trusted local stdio creation plus CLI | Yes | Offline-capable workstations and runners |
| **C · OCI/offline bundle** | Load the digest-pinned image or signed tarball and install the bank-owned wrapper with only the admitted target mounted | Local stdio | Yes, with no registry or package-index access at run time | Air-gapped workstations and hermetic CI |

All paths are exercised by the acceptance criteria. HTTP conformance proves the workspace-blind
governance contract; stdio conformance proves the separate trusted creation boundary. Local MCP and
CLI creation must produce identical tree digests for identical answers.

The console entry point, MCP schemas and OCI entry point are generated from the same tool surface and
package version, so a tool added to the table appears in both forms without a second implementation.

**A note on what a user actually does.** The editor registers the local stdio server with the open
empty directory fixed as `--workspace-root`. The user calls `project_create`; that tool invokes the
preinstalled generator directly and returns an observed receipt. Automation uses `kt-scaffold init`.
`project_blueprint` remains available locally and remotely for planning. The generated project never
installs or carries the package that generated it (Decision 14).

### Offline operation — Decision 15

"Offline" is four separate problems and they have four different answers. Collapsing them is how a
plan promises an air-gapped experience it cannot deliver, so they are separated and admitted as one
explicit OS/architecture/runtime matrix at a time.

| Tier | What runs without a network | Mechanism | Status |
|---|---|---|---|
| 1 · Scaffolding | `/kt-init` and `/kt-update` produce a complete tree | The wheel and its dependencies in a local index, or the OCI image loaded from a tarball. `packaging/offline-bundle.sh` in the generator repository builds both | Ships |
| 2 · Building | The backend and frontend install and compile | The selected profile's hashed Python locks or frozen Node.js lockfile plus the frontend lockfile, served from a mirror or pre-populated cache. The bundle is built per supported OS/architecture/runtime matrix | Ships |
| 3 · Running | The stack comes up and the API answers | Digest-pinned images, loaded from the same bundle. A scaffold with observability declined needs five services rather than ten, which is the configuration an air-gapped environment should choose | Ships |
| 4 · Browser verification | `quality_gate --allow-project-code-execution --include-browser` and the live browser pass | The lockfile-pinned Playwright package and its matching Chromium tree are carried in the platform-specific bundle and selected through `PLAYWRIGHT_BROWSERS_PATH` | Ships for every admitted bundle matrix |

**The honest consequence of tier 4, stated rather than discovered.** A bundle built for the wrong
platform, or admitted without its matching Chromium tree, cannot support L2. The quality gate must
report browser evidence as missing rather than passed. Bundle admission therefore verifies the
matrix record and SHA256 manifest before the disconnected E2E run; the supported bundle itself
includes Chromium, so absent browser evidence is a broken or mismatched bundle, not a planned
product limitation.

**Requirement 11 — everything the scaffold depends on is pinned by version and digest.** That
includes the Playwright package and matching Chromium build, which the first draft left unspecified. A dependency resolved as
"latest" at run time cannot be bundled, cannot be reproduced, and quietly changes what a passing
gate means.

### Interoperability — Decision 13

spec-kit owns spec-driven development as a category, and rebuilding what it already does well is not
this project's aim. Two properties keep the two systems compatible in one repository:

- **Disjoint namespaces.** spec-kit occupies `/speckit.*`; this system occupies `/kt-*`
  (Decision 8). Neither renames anything to accommodate the other.
- **The corpus projects into spec-kit's constitution.** `.specify/memory/constitution.md` is emitted
  from the `trigger: always` rules as one more generated client file, marked generated and covered
  by the drift gate. A team running spec-kit's workflow gets this system's non-negotiable rules in
  the file spec-kit already reads, with no second authoring surface.

What this boilerplate adds over an SDD toolkit is the part those toolkits deliberately leave out: a
tree that already builds and already tests green, the gates that enforce the rules rather than
stating them, and the evidence tiers in section 9. The two layers compose; they do not compete.

The domain layout mirrors the useful part of Spec Kit's current workflow without copying its
implementation: each accepted capability progresses **Spec → Plan → Tasks → Implement**. A large
domain uses `roadmap.md` as a spec-of-specs and decomposes work into independently deliverable PRDs;
each PRD keeps bidirectional traceability to its roadmap entry.

### The `/kt-init` narrative

A user opens an empty directory and calls the locally registered `project_create` tool with the intent
`"<what is being built>"` and `primary_domain`, or runs
`kt-scaffold init --intent ... --primary-domain ...`. Both fields are required and omission fails
validation. Optional choices arrive in the same call or resolve to recorded defaults; the command
writes once and does not offer a trial scaffold.

**How input is supplied depends on the caller, and the answer object does not.** Two unattended
transport modes, one answer object:

| Mode | When | Behaviour |
|---|---|---|
| Trusted local MCP tool | An approved client launches stdio with the explicit empty workspace root | The caller submits intent/domain fields and selected inert agent clients; the installed generator publishes transactionally and returns a local-observed digest receipt |
| Command line | No agent or no MCP client | Explicit flags or `--answers answers.yml`; missing intent/domain fails and the validated answer model supplies all other defaults |

The command-line mode makes the first-hour claim testable in CI. Both modes write the same
`.kt-scaffold/answers.yml`, so a tree scaffolded one way updates the other way. Generated
client-native skills become governance projections only after this first write; they are not a
precondition for starting in an empty directory.

The resolved inputs:

1. Project intent — required natural language; stored in the project overview and answers file.
2. Product name.
3. Product slug — proposed from the product name, validated as lowercase alphanumeric with hyphens.
4. Primary domain — a domain slug such as `payments` or `booking`; creates the domain context and
   PRD workspace, never business implementation.
5. Backend and persistence — fixed as `python-fastapi` + `sqlalchemy-alembic`; recorded for audit and
   update compatibility but not overrideable by the caller or coding agent.
6. Environment-variable prefix — proposed from the slug in upper case. `/kt-init` reports a
   collision with variables already present in the current process or target tree; it does not claim
   to discover unrelated repositories. **Requirement 6:** no detected collision is resolved silently.
7. API prefix — proposed as `/api/<slug>/v1`.
8. Tenant header name — proposed as `x-tenant-id`.
9. Locale set — proposed as English and Turkish. Unsupported report-label locales fall back to the
   canonical English labels rather than generating an incomplete mapping.
10. Observability — whether to scaffold the collector and the trace, metric and log stores behind
   one dashboard. Proposed enabled. When it is
   declined, `app/infra/observability/`, the observability chart and the collector services are
   not written. The baseline has no invented application signal adapter in either variant; an
   accepted capability adds profile-native instrumentation only when it defines the signal contract.

Authentication is not another question. Every backend profile ships JWT + RBAC and the
application-level `super_admin` bootstrap. The bootstrap secret is provided after init through an
interactive prompt or process environment and is never stored in the answer object.

The deployment target is not an init input: `app/devops/` is written in every scaffold against the cluster
contract of section 12, and the facts that vary between clusters — hosts, Secret names, controller
namespace, StorageClass, registry — are overlay values an operator supplies, never scaffold answers.
That is deliberate. Init accepts product facts, not deployment-environment guesses that the charts
would then encode as if they were known.

An **overlay** is simply an environment-specific Helm values layer over the same chart. `lab` and
`cluster` keep the workload shape identical while changing facts such as hosts, registry,
StorageClass, replica count and Secret names. Contract tests use committed non-secret fixture
values; environment-readiness validation separately rejects unconfigured real overlays.

Charts are therefore written in every scaffold, on the grounds that a team that deploys differently
deletes a directory once, while a team that needed charts and did not get them rebuilds the pattern
from nothing.

The tree in section 3 is then written: the governance files for all three clients generated
from the corpus, the primary domain context and PRD workspace, `plans/`, the selected backend and
persistence profile, the frontend platform shell, the authentication browser scenario and quality
manifest, the local stack files, the deployment charts and
overlays, the continuous-integration workflows, and `.kt-scaffold/` carrying the answers and the
file manifest. It returns the next steps, including the two commands below.

**What "the platform baseline passes on first run" means, precisely.** After `/kt-init`,
`scripts/bootstrap.sh`, the local stack, `scripts/db.sh apply`, and
`scripts/create-super-admin.sh`:

`scripts/quality-gate.sh all` exits zero, having run — in this order — the selected profile's
formatter/linter, type check, backend unit and integration suites, the OpenAPI
export followed by a difference check against the committed document, the client-type
regeneration followed by a difference check against the committed types, the frontend lint, the
frontend build, the frontend unit suite, and the governance renderer in check mode. That is the L1
definition.

`KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth` exits zero after a real super-admin login, JWT-backed
`/me` round trip and protected frontend route. This proves the platform wiring without pretending
that an arbitrary business entity exists. The first domain L2 scenario arrives with its accepted
PRD.

### Drift protection and tool testing

`governance-drift.yml` regenerates every client file and fails when the working tree changes,
which makes the reference's three-copy divergence structurally impossible. In addition, every tool
carries tests for malformed input, atomic rollback on injected failure, idempotent repeat, path and
symbolic-link escape rejection, conflict refusal, and command-line/MCP output parity (Requirement 9).

---

## 9. Methodology

Thirteen columns. Each names the rule, the file that carries it, and the gate that enforces it.

| Column | Rule | Carried by | Enforcing gate |
|---|---|---|---|
| 1. Domain-first, spec-driven | A feature belongs to `specs/<domain>/`; `DOMAIN.md` defines the bounded context, `roadmap.md` decomposes it, and each independently deliverable capability begins as an accepted PRD before plan, tasks or code | `rules/10-spec-first.md`, `specs/README.md`, `specs/TEMPLATE-DOMAIN.md`, `specs/TEMPLATE-PRD.md` | `spec_new` creates and links the PRD; every domain generator requires its `spec_path` |
| 2. Plan-driven | `plans/` holds pre-decision working documents. Scope that splits is not parked — it becomes its own spec with its own definition of done | `rules/11-plan-driven.md`, `plans/README.md` | Review; `done_report` reports parked scope as missing evidence |
| 3. Test-driven development | Red, green, refactor. Test real boundaries or pin the value's shape; a mock-only green is not a pass. Skeletons arrive with their tests | `rules/12-tdd.md`, `rules/24-backend-testing.md` | `quality_gate` runs the suites; every skeleton tool emits a test file |
| 4. Evidence-tiered definition of done | L0 written, L1 unit and integration green, L2 live against the running stack over real HTTP or a real browser, L3 owner acceptance on real data. State the tier reached; never claim one not run | `rules/13-definition-of-done.md`, `AGENTS.md` | `done_report` compares the claimed tier against observed evidence and names what is missing |
| 5. Browser verification | Interface changes get a live pass through the same client-neutral Playwright harness used by permanent `e2e/` scenarios; scenarios are indexed in the quality manifest and execute with the bundled Chromium build | `rules/14-browser-verification.md`, `e2e/README.md`, `e2e/QUALITY_MANIFEST.md` | `browser_scenario_new` registers the scenario; trusted callers use `quality_gate --allow-project-code-execution --include-browser` |
| 6. Single-source agent governance | One corpus, generated client files in each client's native mechanism, explicit priority, no hand edits to generated output, and a scaffold that can be brought forward when the corpus moves | `rules/` and `rules/README.md`, `.kt-scaffold/answers.yml` | `governance-drift.yml`, which also asserts the command-name and directive-size requirements; `clients_render` in check mode; `scaffold_update` reports a tree left behind by a corpus change |
| 7. Profile-owned persistence | One recorded schema authority per profile; migrations are generated and reviewed, every domain table carries the mandatory column block, physical integrity is used inside a service boundary, and cross-service references stay logical | `rules/40-persistence-source.md` through `rules/44-schema-engine-boundary.md`, `schema/README.md` | The profile adapter and `schema-check.yml` validate history, drift and destructive changes; `schema_change_prepare` requires an accepted PRD |
| 8. Configuration discipline | One settings object, every key prefixed, and no direct environment reads in application code. A new variable lands in the settings object, the example file, every local stack environment block and every deployment overlay in the same change | `rules/22-backend-configuration.md`, `app/backend/.env.example` | `quality_gate` runs a check that every settings key appears in the example file and in each overlay; review rejects a direct environment read |
| 9. End-to-end completion | Schema, backend, generated contract, generated types, frontend and tests land in one pass. No self-initiated phasing, no parked work | `rules/52-end-to-end-feature.md` | The gate's contract-drift and type-drift steps fail a partial change; `done_report` names the layer that was skipped |
| 10. Post-change verification gate | Formatter, import order, type check, tests, contract and type regeneration where the surface changed, and a browser pass for interface changes | `rules/50-quality-gate.md`, `scripts/quality-gate.sh` | `quality_gate`; `backend-test.yml` and `frontend-test.yml` |
| 11. No claim without evidence | No performance, saturation or root-cause statement without a cited measurement: the query, the value and the window. Distinguish peak from steady state, and symptom from cause | `rules/51-metrics-before-claims.md` | Review; the rule is the checklist a reviewer applies to any performance assertion |
| 12. Fixed-format run reporting | Every test, browser, verification or dogfooding run is reported in one fixed skeleton: a verdict line carrying the counts, what was run, then continuously numbered items under five fixed group labels. No invented thematic headers, no positive-and-negative split | `rules/53-test-run-report.md`, `.claude/skills/kt-test-run-report/SKILL.md` | `quality_gate` and `done_report` return the skeleton already pre-filled; the shared `validate_report` contract rejects malformed candidate reports in tests/consumers |
| 13. Deployment-ready by construction | A change that cannot be deployed to the target cluster is not done. New writable paths, new configuration keys, new services and new images land with their chart, overlay and Secret reference in the same change, inside the constraints of section 12 | `rules/45-deployment-target.md`, `app/devops/README.md` | `charts-render.yml`; the configuration-sync step of `quality_gate`, which checks typed settings, the example/Compose surfaces and the chart's single pre-created Secret boundary |

### Column 12 in detail — the run-report skeleton

The reference binds no rule and no skill to the shape of a run result, and it shows: summaries
arrive with invented thematic headers, findings split into positive and negative blocks, and items
left unnumbered, so two runs of the same suite cannot be diffed section by section and a reader
cannot tell in one line whether anything needs a decision. The skeleton below is adapted from the
test summary report of IEEE 829 and the test completion report of ISO/IEC/IEEE 29119-3, cut down
to what one agent writes after a single run. It lives in `rules/53-test-run-report.md` and is
emitted as `.claude/skills/kt-test-run-report/SKILL.md`, the `.cursor` quality rule file, and the
quality section of `CLAUDE.md` and `AGENTS.md` like every other rule.

```
# Run report — <YYYY-MM-DD> · <scope, one sentence>

1. Result: <one-sentence verdict> — unit N passed / browser M passed / skipped K;
   awaiting decision: J (M3, M6).
2. Ran: <suite → file → count lines, or one compact table; name the environment: local, staging>.
3. Items:
   **DEFECT**
   M1 ... (FIXED, file/test)
   **TRAP**
   M2 ...
   M3 ... ← DECISION
   **OBSERVATION** — none
   **OPEN**
   M4 ...
   **SIDE-EFFECT**
   M5 ...
4. Open questions: Q1..Qn   ← ONLY when the reader asked to converge; otherwise the section is
   not written at all.
```

| Group label | What goes under it |
|---|---|
| `DEFECT` | A defect found. The same item states whether it was fixed or left, and where — file and test |
| `TRAP` | Behavior a future run has to know before it repeats this one |
| `OBSERVATION` | Noticed and deliberately untouched; the item says where it was recorded |
| `OPEN` | A case not covered, with its reason in one clause |
| `SIDE-EFFECT` | Any repository change outside the test files themselves: configuration, fixture extension, formatter settings, a revert |

**Decision 7 — the group labels follow the `/kt-init` locale answer.** `rules/53-test-run-report.md`
carries canonical English and the supported localized mappings. The renderer emits a mapping for a
supported primary locale and otherwise falls back to canonical English; it never invents an
incomplete translation. The full shipped mapping is below. A report is read by the team
that ran it, and a label it has to translate on sight is a label it will quietly replace.

Everything except the words is identical across sets: the section numbering, the verdict line, the
continuous item numbering, the decision marker's position and the rule that section 4 is written
only on request. The cost this accepts is that two scaffolds on different locales produce reports
that are structurally but not textually diffable; because the sets are mapped one to one, a tool
that needs to compare across locales can translate the labels mechanically.

The rule states nine constraints:

1. Sections 1 through 3 always appear, in that order, under those exact names. An empty section is
   written `— none`; it is never dropped and never renamed.
2. One continuous item numbering runs across the whole of section 3. It does not restart per
   group, and no heading beyond the five group labels may be introduced.
3. All five group labels appear in the order above, each on its own line, present even when empty.
   Inventing a sixth group or renaming one is a defect in the report.
4. Any item needing the reader's decision ends with `← DECISION`, and section 1 states the count
   and the item numbers — `awaiting decision: 2 (M3, M6)`, or `awaiting decision: none`. This is
   how a reader scans "do I have to act" in one line.
5. Section 1 carries the counts, and no completion wording appears without them. This is column 4's
   evidence discipline applied to the report itself: the counts are what make a claimed tier
   checkable.
6. Inside a group, items are ordered by severity descending, with `← DECISION` items first.
7. One line per item, two at most. Detail belongs in the scenario file or the test docstring and is
   referenced, not inlined.
8. A fixture or data change made only to enable the run is a side-effect item, never a section of
   its own.
9. The prose language follows the language the run is being reported in; the labels come from the
   emitted label set below.

**Label sets.** The corpus rule initially carries canonical English and Turkish; new mappings arrive
as complete corpus changes. The generated skill emits the supported primary-locale set or English
fallback. Structure,
ordering, numbering and the decision marker's position are identical in every set — only the words
change, so a reader of either set is reading the same report.

| Canonical | `tr` |
|---|---|
| `Run report` | `Koşum raporu` |
| `Result` | `Sonuç` |
| `Ran` | `Koşulan` |
| `Items` | `Maddeler` |
| `DEFECT` | `KUSUR` |
| `TRAP` | `TUZAK` |
| `OBSERVATION` | `GÖZLEM` |
| `OPEN` | `AÇIK` |
| `SIDE-EFFECT` | `YAN-ETKİ` |
| `Open questions` | `Açık sorular` |
| `← DECISION` | `← KARAR` |
| `— none` | `— yok` |

Front matter: `scope: quality`, `priority` after `52-end-to-end-feature`, `gate: done_report`,
`trigger: always` with an empty `applies_to` — a run is reported from any context, including one
that edited no test file, so this is repository-wide rather than path-matched. The emitted skill's
description names the vocabulary that has to select it — test-suite run, browser pass,
verification sweep, scenario batch, dogfooding pass — because a format rule nobody loads is a
format rule nobody follows.

**Traceability.** Derived from `.claude/skills/end-to-end-feature/SKILL.md`,
`.claude/skills/prd/SKILL.md`, `.claude/skills/schema-migration/SKILL.md`,
`.claude/skills/no-physical-fks/SKILL.md`, `.claude/skills/metrics-before-claims/SKILL.md`,
`.claude/skills/schema-comments/SKILL.md`, `app/backend/.claude/skills/testing/SKILL.md`,
`app/backend/.claude/skills/configuration/SKILL.md`,
`app/frontend/.claude/skills/live-verification/SKILL.md`, `e2e/QUALITY_MANIFEST.md`,
`specs/README.md`, `plans/README.md` and the `CLAUDE.md` workflow section. Generalized: each column
that the reference enforced only by convention now names a gate; the configuration sync rule gains
an automated check because the reference documents the four surfaces but verifies none of them.
Dropped: the assistant evaluation column and the contract-driven-semantics rule, both of which
exist only to govern the excluded in-product assistant. Added, with no reference counterpart:
column 12 — the reference binds no rule, skill or template to the shape of a run result, so the
skeleton is net-new; its section set is adapted from IEEE 829 and ISO/IEC/IEEE 29119-3, and its
group labels from the requester's own reporting practice.

---

## 10. Seed content inventory

Classification: **Template** — a fill-in shape with placeholders. **Working** — real, executing
code or configuration that passes the gate as delivered. **Placeholder** — a stub whose only job
is to mark a location and explain what belongs there.

### Governance and rules

| File | Kind |
|---|---|
| `rules/*.md` (the corpus listed in section 3) | Working |
| `rules/corpus.schema.json`, `rules/README.md`, `rules/GENERATED.lock` | Working |
| `AGENTS.md`, `CLAUDE.md`, `.claude/rules/**`, `.claude/skills/kt-**`, `.codex/skills/kt-**`, `.cursor/rules/**`, `.codex/config.toml` | Working, generated |
| `.specify/memory/constitution.md` | Working, generated — the spec-kit projection |
| `.claude/settings.json`, `.codex/config.toml` | Governance-only project settings; both explicitly declare no project-local MCP server |
| `.kt-scaffold/answers.yml`, `.kt-scaffold/manifest.json` | Working, written by `/kt-init` and read by `/kt-update` |

### Scaffold package — generator repository only, never in a scaffolded tree (Decision 14)

| File | Kind |
|---|---|
| `src/kt_scaffold/{server,corpus,render,safety,update}.py`, `__main__.py` | Working |
| `src/kt_scaffold/tools/*.py` (twelve modules) | Working |
| `src/kt_scaffold/templates/**` | Template |
| `packaging/Dockerfile`, `packaging/offline-bundle.sh` | Working |
| `tests/**` | Working |

### Specifications and plans

| File | Kind |
|---|---|
| `specs/README.md`, `plans/README.md` | Working |
| `specs/openapi/app-api.yaml` | Working, generated by the contract export |
| `specs/TEMPLATE-DOMAIN.md`, `specs/TEMPLATE-PRD.md` | Template |
| `specs/<domain>/DOMAIN.md`, `roadmap.md`, `PRDs/` | Working context generated from the init intent; no business implementation |

### Schema

| File | Kind |
|---|---|
| `schema/README.md`, `schema/profile.yml` | Working, recording SQLAlchemy/Alembic authority |
| SQLAlchemy models plus Alembic configuration/history | Working, generated at scaffold time |
| `schema/alembic/` | Working, generated and reviewed |

### Backend (fixed Python/FastAPI profile)

| File | Kind |
|---|---|
| `app/main.py`, `app/api/router.py`, `app/api/health.py` | Working |
| `app/api/auth/**`, including the permission guards | Working |
| `app/core/{config,request_context,security}.py` | Working |
| `app/db/{base,base_class,session}.py` | Working, engine-shaped |
| `app/domain/models/{tenant,user,role,permission,mixins}.py` | Working in the Python profile |
| `app/infrastructure/repositories/user_repository.py` | Working in the Python profile |
| `app/middleware/tenant_context.py` | Working |
| `app/schemas/auth/**` | Working |
| `app/services/auth_service.py` | Working |
| `app/scripts/{create_super_admin,export_openapi}.py` | Working |
| `tests/**` for every working module above | Working |
| `.env.example` | Template |

### Frontend

| File | Kind |
|---|---|
| `src/main.tsx`, `src/App.tsx`, `src/globals.css` | Working |
| `src/contexts/{AuthContext,IntlContext}.tsx` | Working |
| `src/lib/{apiClient,authStorage,config,utils}.ts` | Working |
| `src/components/ui/**` | Working, a minimal primitive set |
| `src/components/layout/**`, `src/components/common/**` | Working |
| `src/pages/{LoginPage,HomePage,NotFoundPage}.tsx` | Working |
| `src/services/auth.ts` | Working |
| `src/locales/<locale>.json`, one per configured locale | Working, covering every string the shipped pages use |
| `src/types/api.d.ts` | Working, generated |
| Unit tests beside each page, context and service | Working |

### Browser scenarios

| File | Kind |
|---|---|
| `e2e/shared/harness.mjs` | Working |
| `e2e/auth/01-super-admin-login.mjs`, `e2e/auth/run-all.mjs` | Working |
| `e2e/package.json`, `e2e/README.md` | Working |
| `e2e/QUALITY_MANIFEST.md` | Working, with one platform-auth surface row and an empty domain roadmap section |

### Infrastructure, delivery and continuous integration

| File | Kind |
|---|---|
| `app/infra/docker-compose.local.yml`, `nginx/nginx.local.conf` | Working, shaped by the observability answer |
| `app/infra/observability/**` | Working, only when `/kt-init` enabled observability |
| `app/infra/Dockerfile.*.release` | Working |
| `app/infra/.env.example` | Template |
| `app/devops/charts/**` | Working, and passing the section 12 contract gate on a fresh scaffold |
| `app/devops/environments/{cluster,lab}/*.yaml` | Template, with non-secret environment facts allowed to remain unresolved until readiness validation |
| `tests/fixtures/overlays/{cluster,lab}/*.yaml` | Working, non-secret render fixtures used by the contract gate |
| `app/devops/images.yaml` | Working, listing the images the local stack already pins |
| `app/devops/README.md`, `OPERATIONS.md` | Working, carrying the cluster contract, the release order and the operator runbook |
| `app/devops/ACCEPTED-RISKS.md` | Template — the four-column shape with no rows, so the first accepted risk has a place to land |
| `.github/workflows/*.yml` | Working |
| `scripts/{bootstrap,quality-gate,db,render-clients,render-charts,export-openapi,generate-types}.sh` | Working |
| `docs/en/README.md`, `docs/tr/README.md` | Placeholder, explaining the public-documentation boundary |

**Traceability.** The inventory mirrors the file classes actually present in the reference —
`app/backend/app/`, `app/frontend/src/`, `schema/core/`, `e2e/`, `app/infra/`,
`app/devops/`, `scripts/`, `.github/workflows/`. Generalized: the platform baseline replaces the
reference product domains; the primitive component set is trimmed to auth and the home surface. Dropped:
the industry resource directories, catalog seed data, glossary artifacts, the second schema
project, and every worker whose subject was the excluded product.

---

## 11. Platform baseline and first domain vertical

The scaffold ships a working platform baseline, not a fictional business resource.

**The baseline touches, in order:**

1. The selected persistence profile's tenant, user, role and permission authority plus generated
   migration history.
2. Password hashing, JWT issuance and validation, RBAC guards, and an explicit `super_admin` bypass.
3. `scripts/create-super-admin.sh`, which prompts or reads process environment values, stores only
   the password hash in PostgreSQL and is idempotent.
4. Health, login and `/me` endpoints under the configured API prefix.
5. Offline OpenAPI export and generated TypeScript client types.
6. Localized login and authenticated home pages. The home page names the project intent and primary
   domain but exposes no unimplemented business action.
7. Profile-native backend tests, frontend tests, and configuration/contract drift checks.
8. `e2e/auth/01-super-admin-login.mjs`, which proves real login, JWT session, `/me`, tenant context
   and protected-route access using the application super-admin.
9. `e2e/QUALITY_MANIFEST.md`, which records the platform L1/L2 evidence.

**The first business vertical.** `/kt-spec <domain> <capability>` creates a roadmap-linked PRD.
After acceptance, `/kt-domain --spec-path ...` and the schema/page/scenario generators may build the
vertical. They must consume that spec, generate tests with the artifacts, and land persistence,
backend, OpenAPI, client types, frontend, localization and browser evidence together. No generator
accepts an unscoped resource name as a substitute for a domain spec.

This preserves the reference's end-to-end completion discipline while removing its product payload
and the misleading generic-resource example.

---

## 12. Deployment contract

Everything the previous eleven sections describe exists to reach one place: a Rancher-managed
Kubernetes non-production cluster with no internet egress. That target is stated here, at scaffold
time, rather than discovered by whoever first tries to deploy — because the cluster's constraints are
not deployment details. Read-only root filesystems decide where the backend may write; the absence of
an external-secret API decides how configuration arrives; digest-only images decide what the build
must publish; default-deny networking decides what a service may talk to. A tree that learns these
after the fact has already made the opposite choice everywhere, and the charts written for it become
a translation layer over an application that assumed something else.

### Decision 16 — the deployment target is a design constraint, and both overlays ship from day one

The scaffold assumes the cluster properties below. They are the reference's measured facts, carried
across because they describe an ordinary locked-down enterprise cluster rather than anything specific
to one product. Each is an assumption the adopting team confirms once, before the first install — not
a value the scaffold guesses.

| Assumption | What the scaffold does about it |
|---|---|
| A recent Kubernetes minor, fixed per cluster | Helm renders with that version's capability set; the local gate then enforces an approved kind/API-version allow-list and structural workload contract. Full API-server/OpenAPI admission remains a platform deployment-stage check |
| Ingress through an ingress controller; no Gateway API | Charts render `Ingress` only. One TLS host serves the application and the API, split by path |
| The ingress controller runs in a namespace the cluster chooses | The overlay names it, and the NetworkPolicy admits it by label. Naming the wrong one renders and installs cleanly, then returns 504 with nothing in any log — the reference measured exactly this |
| NetworkPolicy is enforced | Default-deny in both directions, peers selected by the `part-of`/`component` pod labels every template carries |
| metrics-server present, no monitoring-operator custom resources | Autoscaling on CPU and memory only; observability is namespace-local and provisions from disk, never a `ServiceMonitor` |
| No external-secret or secret-store API | Charts reference pre-created Secrets by name through `existingSecrets`. No chart ever authors one |
| One default StorageClass, delete reclaim policy | Every claim declares a size; the database chart ships a storage probe, a backup job and an isolated restore check, all disabled until an operator runs them deliberately |
| Internal registry only, zero cluster egress | Image references carry a digest and an internal repository. `images.yaml` is the reviewed list of images the repository does not build |
| A namespace-scoped delivery identity, never cluster-admin | Nothing any chart renders is cluster-scoped |

**Two overlays, one structure.** An overlay is an environment-specific values layer applied to the
same Helm chart. `environments/cluster/` and `environments/lab/` differ only in environment facts —
hosts, sizes, StorageClass, registry, replica counts, retention. An overlay that
changed the *shape* of a release would stop proving anything about the release the real cluster runs.
The second overlay is what makes the first testable before anyone has cluster access, which for a
vibe-coded project is the normal starting condition.

Committed real-environment overlays may retain clearly marked unresolved facts. Contract CI renders
both shapes with non-secret fixture values under `tests/fixtures/overlays/`; a separate
environment-readiness command fails until a deployable overlay has real hosts, registry, Secret
names and StorageClass. This separates "the chart is structurally valid" from "this environment is
configured" and removes the fresh-scaffold contradiction.

### The contract every chart honours

- **Self-contained.** No library chart, no `dependencies`, no vendored archives, so `helm template`
  works on a plain checkout — which is what lets rendering be a hard gate rather than a step that
  silently skips.
- **Closed runtime dependency boundary.** **Requirement 16:** the frontend bundles its scripts,
  fonts and styles locally; workload configuration may name only approved local or in-cluster
  services; telemetry exporters terminate in-cluster. No workload uses the internet, SaaS, a CDN,
  a public registry or an external telemetry endpoint at run time.
- **Digest-only images from the internal registry.** **Requirement 12:** a tag never reaches a
  workload, and for an image the project builds the digest is the image *index* digest, so one set of
  values deploys onto whichever node architecture the cluster has.
- **No chart-authored Secrets.** **Requirement 13:** secret material never appears in a chart, a
  values file, an overlay or the repository. Charts name Secrets; an administrator creates them.
- **A pod-security floor.** **Requirement 14:** non-root with an explicit user and group, no
  privilege escalation, all capabilities dropped, `RuntimeDefault` seccomp, read-only root filesystem
  with every writable path declared and size-bounded, no mounted service-account token, requests and
  limits on every container, and startup, readiness and liveness probes on every HTTP workload.
- **Declared network.** **Requirement 15:** every workload renders a NetworkPolicy with both
  directions present, so an empty rule list denies instead of allowing, and no workload receives
  unrestricted egress.
- **ClusterIP only.** No node ports, no load balancers; ingress is the single entry point.
- **Separate database lifecycle, no runtime DDL.** The database, the migration release and the
  application upgrade independently; the runtime role holds DML rights only and the migration release
  is named after the source revision, so a schema change never redeploys the database.
- **Immutable chart versions.** A published version is never overwritten.

### The gate

`scripts/render-charts.sh` is the mechanism and `charts-render.yml` is the same contract command in
CI. Contract mode renders every release with committed fixture values; `--environment-ready`
renders a chosen real overlay and rejects unresolved facts. The checks fail on: a lint or
template error, an unresolved placeholder, a public-registry or tag-only image, a workload that runs
as root or allows privilege escalation, a missing seccomp profile, resource limits, probe or
NetworkPolicy, a writable root filesystem, a mounted service-account token, a chart-authored Secret,
a Service that is not ClusterIP, a claim with no size, a Job that restarts always, a pod template
missing its identity labels, and a kind/API version outside the scaffold's approved allow-list.
It also fails on a remotely loaded frontend asset, an external telemetry exporter or a runtime host
outside the approved local and in-cluster allow-list.

One check crosses releases: a configuration value naming an in-cluster host must match a Service some
release actually renders. In the reference this caught six overlays pointing telemetry at a collector
Service no chart produced — nothing about the install would have failed, and the signals would simply
have gone nowhere.

### What the scaffold deliberately does not decide

The promotion pipeline, the release-manifest format, the deploy controller, TLS ownership and the
registry's own policy belong to the organization's delivery platform, not to a project template. The
scaffold's obligation stops at producing releases that satisfy the contract above and a
`README.md`/`OPERATIONS.md` pair stating the install order, the Secrets an administrator creates and
the rollback path. `ACCEPTED-RISKS.md` ships empty with its four columns — risk, why accepted,
compensating control, re-evaluation trigger — because the first knowingly unsafe thing a team does
needs somewhere to be written down other than a commit message.

**Traceability.** Derived from the reference's `app/devops/README.md`, `OPERATIONS.md`,
`ACCEPTED-RISKS.md`, `images.yaml`, the chart set under `app/devops/charts/`, both overlay
directories, `scripts/render_charts.py`, and the cluster facts and locked decisions recorded in the
reference's Rancher delivery plan. Generalized: the measured facts of one cluster become an
assumption table an adopting team confirms, and the environment directory names lose their site
identity. Dropped: the excluded engine's estate release and its bootstrap, the promotion, signing and
release-manifest machinery that belongs to a delivery platform rather than a project, and the
site-specific registry, host and identity values.

---

## 13. Extension points

Each excluded subsystem is described only as a socket: where it would attach and what it would
have to satisfy. None of it is built.

| Excluded subsystem | Where it would attach | What it would have to satisfy |
|---|---|---|
| A second, read-only analytical engine | A new `schema/<name>/` project outside the migration tool's control, a dedicated read-only session module beside `app/db/session.py`, and a service package under `app/services/`. The application database stays the write surface and never becomes the analytical one | The bounded-context rule: no cross-database query, no federated table, no database link. References across the boundary are by value only |
| Statement guardrails for analyst-authored queries | A gate module in that new service package, invoked before any statement reaches the read-only session | Policy decisions must come from a parse tree, never from pattern matching over raw text. Single statement, read-only, function denylist, relation allow-list |
| Column-level masking at query time | A parse-tree rewriting step in the same gate, plus classification columns on whatever metadata table describes the analytical surface | Masked columns must also be rejected in predicates, joins, grouping, ordering and aggregates, or the mask leaks through value probing |
| A data catalog and its synchronization | Metadata tables declared through the selected persistence profile, a scheduled module under `app/workers/`, and read endpoints under `app/api/` | Metadata is synchronized; data is never copied. Visibility is configuration — an exposure flag intersected with grant patterns — not code |
| Discovery search over that catalog | A search service reading the catalog tables, with any database helper added through a reviewed profile migration | Cache keys must carry tenant, permission scope and locale, per the caching rule |
| A query workbench surface | Pages under `app/frontend/src/pages/`, a service under `src/services/`, and endpoints under `app/api/` | Every read goes through the guardrail gate. The workbench never reaches the database directly |
| Usage insights and rollups | Rollup tables in the schema project and a scheduled module under `app/workers/` | Rollups are derived, never authoritative; retention is a settings value, not a literal |
| The first cached endpoint | A profile-native adapter under the infrastructure boundary plus one service-layer call site, traced to its accepted PRD; the shipped Redis service/chart is only the socket | Canonical keys built by normalize, canonicalize and hash; tenant, permission scope and locale always in the key; a per-key lock against stampede; every operation fail-open. The cache is never a system of record — a value that cannot be recomputed from the database does not belong in it |
| Observability in a scaffold that declined it | `app/infra/observability/`, its Compose overlay and the observability chart, plus a profile-native application adapter when an accepted PRD defines the signal contract | Enabling infrastructure does not manufacture domain call sites. Exporters remain egress-free and terminate only in approved local or in-cluster stores |
| An in-product assistant with a capability platform, approval state machine, memory and an evaluation harness | A service package under `app/services/`, a model-client package beside it, capability modules each permission-gated, an approval table in the schema project, an evaluation suite under `tests/`, and a drawer component in the frontend shell | Every state-changing capability passes through preview, explicit approval within a time-to-live, and a permission replay against the caller's current grants before executing, with every transition audited. Determinism comes from typed state and schemas, never from matching natural-language text |
| Industry vocabularies, table inventories and mockups | `docs/`, `specs/<domain>/`, or a resource directory the scaffold does not create | Nothing industry-specific enters the base schema or rule corpus; domain content enters only through that domain's accepted specs |
| Skills for a fourth client | One more emission target in `render.py` and one more row in the emission map of Decision 9 | The skill bodies already exist and the format is a published standard; adding a client is a discovery path and a reserved-name list, never a second authoring surface. This is how Cursor skills land once that client's path is verified against the client in hand |
| An additional air-gap browser target platform | Add a separate `packaging/offline-bundle.sh` matrix build and runner admission record for that OS/architecture/runtime tuple | Each admitted bundle carries the lockfile-pinned Playwright package and matching Chromium tree, records the matrix, verifies `SHA256SUMS`, and runs the browser suite with network egress blocked. Matrices are never merged implicitly |

---

## 14. Acceptance criteria

Each item states the evidence tier it carries and is verifiable by the named command or file.
The boxes form the executable acceptance checklist; their checked state belongs in the current run
report and is never presumed merely because this plan exists.

**Governance and rule corpus**

- [ ] **L0** — `rules/` contains every corpus file listed in section 3, each with front matter valid against `rules/corpus.schema.json`. Verify: `scripts/render-clients.sh --validate`
- [ ] **L1** — `scripts/render-clients.sh --check` exits zero on a fresh scaffold. Verify: that command
- [ ] **L1** — Hand-editing any generated file makes `governance-drift.yml` fail. Verify: the workflow's own test job, which mutates a generated file in a scratch copy and asserts a non-zero exit
- [ ] **L0** — Every generated file opens with the generator banner. Verify: `grep -L "GENERATED" AGENTS.md CLAUDE.md .claude/rules/*.md .cursor/rules/*.mdc .claude/skills/kt-*/SKILL.md .codex/skills/kt-*/SKILL.md .specify/memory/constitution.md` returns nothing
- [ ] **L0** — Rule IDs are unique and no normalized rule body is duplicated across corpus files. Verify: corpus validation checks both ID uniqueness and normalized body digests
- [ ] **L1** — The generated `CLAUDE.md` is under 200 lines and its rule content is reachable only through the `@AGENTS.md` import and `.claude/rules/` (Requirement 8). Verify: `scripts/render-clients.sh --check`, which fails the render when the file would exceed the limit
- [ ] **L1** — Every path-scoped corpus rule emits a `.claude/rules/` file whose `paths:` list equals its `applies_to` globs. Verify: `pytest tests -k path_scoped_rules`
- [ ] **L1** — Every skill emitted for Claude has a byte-identical body at Codex's discovery path. Verify: `pytest tests -k skill_parity`
- [ ] **L1** — No generated command name collides with a client built-in, and every generated command carries the `kt-` namespace (Requirement 7, Decision 8). Verify: `pytest tests -k reserved_names`, which asserts the per-client reserved list and the prefix
- [ ] **L1** — `.specify/memory/constitution.md` contains every `trigger: always` rule and nothing else, and drifts like any other generated file. Verify: `scripts/render-clients.sh --check` after editing one corpus rule

**Scaffold package and command layer**

- [ ] **L1** — Local stdio registers six bilingual pairs and HTTP registers the five workspace-blind governance pairs; strict schemas reject undeclared workspace, target, patch and execution inputs. Verify: `pytest tests -k mcp_`
- [ ] **L1** — `project_create` invokes only the installed in-process generator, returns bounded local-observed receipt metadata and refuses unsafe, non-empty, partial, edited or symlink targets. Verify: `pytest tests -k local_creation`
- [ ] **L1** — `project_init` uses staging plus a journaled publish, leaves no partial tree on injected failure or retry, and refuses a non-empty target. Verify: `pytest tests -k transactional_init`
- [ ] **L1** — Every generator is idempotent: a second identical run reports every file unchanged. Verify: `pytest tests -k idempotent`
- [ ] **L1** — A path argument resolving outside the sandbox is refused, including through a symbolic link and through parent-directory segments. Verify: `pytest tests -k sandbox`
- [ ] **L1** — The server never invokes a version-control command. Verify: `pytest tests -k no_vcs`, which asserts the subprocess allow-list
- [ ] **L1** — Every local CLI operation has a Python-operation equivalent producing byte-identical output for the same arguments. Verify: `pytest tests -k cli_parity`
- [ ] **L2** — Real local stdio creates the same tree digest as CLI without shell/download execution, while real HTTP exposes governance only; generated projects register no server and update/reconciliation tests preserve mandatory behaviors. Verify: stdio/HTTP protocol, local-creation parity and governance suites, then the client rollout matrix
- [ ] **L2** — A complete scaffold is produced with no MCP client or agent present. Verify: `kt-scaffold init --intent "test intent" --answers answers.yml` in a scratch directory, then `scripts/quality-gate.sh all`

**Provisioning and offline**

- [ ] **L1** — A scaffolded tree contains no copy of the generator or its template bundle (Decision 14). Verify: the scaffold-and-gate job asserts that `tools/kt-scaffold/`, `src/kt_scaffold/` and `src/kt_scaffold/templates/` are absent; Helm's project-owned chart `templates/` directories remain valid
- [ ] **L1** — `.kt-scaffold/answers.yml` records the required generator version, and `scripts/bootstrap.sh` rejects a missing or incompatible bank-managed global installation without downloading anything. Verify: `pytest tests -k pinned_generator`
- [ ] **L2** — The controlled wheel/private-index installation and the OCI/offline wrapper produce byte-identical trees from the same intent and answers. Verify: scaffold once per provisioning path into two scratch directories and diff them; reproducible manifests contain no wall-clock field
- [ ] **L2** — Both provisioning paths scaffold unattended. Verify: run `kt-scaffold init --intent "test intent" --answers answers.yml` through the managed executable and the OCI wrapper with no terminal input, then run `scripts/quality-gate.sh all` in both trees
- [ ] **L2** — A machine with no network route scaffolds, builds and runs a scaffold from the offline bundle alone. Verify: load the bundle on a host with egress blocked, then `kt-scaffold init --intent "test intent" --primary-domain test-domain`, `scripts/bootstrap.sh`, bring the stack up, `scripts/db.sh apply`, `scripts/quality-gate.sh all`
- [ ] **L2** — On that egress-blocked machine the bundled Chromium build completes the authentication browser scenario; a missing or wrong-platform browser tree fails bundle admission and cannot be reported as a pass (Decision 15, tier 4). Verify: `KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth`
- [ ] **L1** — Every dependency the scaffold resolves at run time is pinned by version, integrity hash or OCI digest, including Playwright and its Chromium tree (Requirement 11). Verify: `pytest tests -k pinning`, which checks the profile BOM, lockfiles, browser package lock and offline bundle inventory, image inventory and compose files
- [ ] **L1** — The built frontend, rendered charts and running stack contain no internet, SaaS, public-registry, CDN or external-telemetry dependency. Verify: `pytest tests -k runtime_network_boundary` plus the egress-blocked stack test
- [ ] **L1** — The generator repository's own workflow scaffolds a project and runs its quality gate on every change. Verify: that workflow, with a deliberately broken template

**Scaffold update**

- [ ] **L1** — `/kt-init` writes `.kt-scaffold/answers.yml` and `.kt-scaffold/manifest.json`, and `/kt-update` replays them without re-asking. Verify: `pytest tests -k update_replay`
- [ ] **L1** — `/kt-update` against an unchanged corpus reports every file unchanged and writes nothing. Verify: `pytest tests -k update_noop`
- [ ] **L1** — A generated file edited by hand is reported as a conflict and left untouched; an untouched generated file is regenerated (Requirement 10). Verify: `pytest tests -k update_conflict`
- [ ] **L1** — A file removed from the corpus appears in `manual_steps[]` and is never deleted. Verify: `pytest tests -k update_removal`
- [ ] **L2** — A scaffold generated at corpus version N updates to version N+1 and still passes the gate. Verify: scaffold, bump one corpus rule, `kt-scaffold update`, `scripts/quality-gate.sh all`

**Persistence contract**

- [ ] **L1** — A fresh scaffold passes `scripts/quality-gate.sh all`. Verify: that command
- [ ] **L2** — `KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth` passes after the super-admin bootstrap against a fresh stack. Verify: that command
- [ ] **L1** — `answers.yml` and `schema/profile.yml` agree on one backend, schema authority and migration adapter. Verify: `pytest tests -k persistence_profile`
- [ ] **L1** — The fixed Python/SQLAlchemy/Alembic profile scaffolds and migrates cleanly. Verify: the scaffold CI job
- [ ] **L1** — Every baseline table carries the mandatory column block where applicable, and references inside the application database have declared integrity. Verify: the migrated-schema assertion
- [ ] **L1** — A migration whose changes are absent from the recorded schema authority fails the drift check (Requirement 3). Verify: `schema-check.yml` with one mismatch
- [ ] **L1** — The fresh platform baseline has no cache adapter or call site, while Redis remains an isolated infrastructure socket; a later adapter/call must cite its accepted PRD and carry its own contract tests (Requirement 2). Verify: the profile gate and source-boundary search
- [ ] **L1** — Declining observability at `/kt-init` omits `app/infra/observability/`, its Compose overlay and the observability chart; neither variant invents domain instrumentation. Verify: generate both variants and compare the remaining managed tree

**Deployment contract**

- [ ] **L1** — Every release shape renders with committed non-secret fixture overlays on a fresh scaffold and passes the contract gate. Verify: `charts-render.yml`
- [ ] **L1** — Environment-readiness mode rejects a real overlay with unresolved host, registry, Secret-name or StorageClass values. Verify: `scripts/render-charts.sh --environment-ready cluster`
- [ ] **L1** — A workload rendered with a tag instead of a digest, or with a repository outside the internal registry, fails the gate (Requirement 12). Verify: the gate's own self-test, which mutates one rendered value per rule and asserts each mutation is caught
- [ ] **L1** — A chart that would author a Secret, or an overlay carrying a secret value, fails the gate (Requirement 13). Verify: the same self-test
- [ ] **L1** — A pod template missing any element of the security floor — non-root, no privilege escalation, dropped capabilities, seccomp, read-only root filesystem, unmounted service-account token, resources, probes — fails the gate (Requirement 14). Verify: the same self-test, one mutation per element
- [ ] **L1** — A workload with no NetworkPolicy, or one whose pod template omits the `part-of`/`component` labels its peers select on, fails the gate (Requirement 15). Verify: the same self-test
- [ ] **L1** — A configuration value naming an in-cluster host that no release renders as a Service fails the gate. Verify: the same self-test, pointing the telemetry endpoint at a Service name no chart produces
- [ ] **L1** — Every rendered manifest uses the selected Helm capability version and the scaffold's approved kind/API-version allow-list; a deliberately deprecated API version fails locally. Full API-server/OpenAPI admission is a platform-stage check
- [ ] **L0** — The two overlays differ only in environment facts: the set of files, the set of keys in each and the release shape are identical. Verify: diff the key sets of `environments/cluster/` and `environments/lab/`

**Methodology gates**

- [ ] **L1** — `scripts/quality-gate.sh all` runs the Python format/lint/type/test sequence, contract export and drift check, type regeneration and drift check, frontend lint/build/tests, and the governance renderer in check mode, in that order, and stops at the first failure. Verify: that command with a deliberately broken step in each phase
- [ ] **L1** — A typed settings key missing from `app/backend/.env.example` or, where consumed locally, the backend Compose environment fails the configuration-sync gate; the deployment chart is separately required to consume one pre-created `existingSecret` boundary. Verify: mutate each surface once
- [ ] **L1** — A backend change to the API surface with a stale committed contract fails the gate. Verify: the contract-drift step after editing a response model without re-exporting
- [ ] **L1** — JWT/RBAC behavior and the `super_admin` bypass agree across the schema seed, backend guards and frontend session model. Verify: the backend auth contract test
- [ ] **L0** — `specs/TEMPLATE-DOMAIN.md` and `TEMPLATE-PRD.md` carry domain boundaries, roadmap traceability, the Spec → Plan → Tasks → Implement flow, and evidence-ticked acceptance criteria. Verify: read the templates
- [ ] **L0** — `rules/53-test-run-report.md` carries the skeleton, the five group labels, the nine constraints and the label sets, and renders to `.claude/skills/kt-test-run-report/SKILL.md` with the label set of the primary locale. Verify: `scripts/render-clients.sh --check`, then read the emitted skill
- [ ] **L1** — `quality_gate` returns `report_skeleton` with sections 1 to 3 present, all five group labels present including the empty ones, and section 1's counts taken from the observed results rather than restated by the caller. Verify: `pytest tests -k report_skeleton`
- [ ] **L1** — A report with a renamed group label, a missing group, a sixth group, or numbering that restarts per group is refused by the shared `validate_report` skeleton validator. Verify: the report contract tests
- [ ] **L1** — `done_report` emits every `missing[]` entry as a numbered open item and every unsupported tier claim as a defect item carrying the decision marker, and section 1 states the decision count and the item numbers. Verify: `pytest tests -k report_decisions`
- [ ] **L1** — `done_report` returns `ok: true` on an unsupported tier claim, reports `tier_supported` below `claimed_tier`, and never silently downgrades the claim to match the evidence (Decision 6, Requirement 5). Verify: `pytest tests -k done_report_advisory`
- [ ] **L1** — The run-report label set follows a supported primary locale and falls back to canonical English for any unsupported locale, with structure unchanged (Decision 7). Verify: `pytest tests -k report_labels`

**Platform baseline and domain-first flow**

- [ ] **L1** — The health/auth/RBAC/super-admin baseline exists at every step in section 11 and passes the fixed-profile quality gate.
- [ ] **L2** — The browser scenario asserts real super-admin login, JWT-backed `/me`, tenant context and protected-route access. Verify: `KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth`
- [ ] **L1** — Init creates `specs/<domain>/DOMAIN.md`, `roadmap.md` and `PRDs/` but no business-domain implementation. Verify: `pytest tests -k domain_first_init`
- [ ] **L1** — `/kt-domain`, `/kt-schema`, `/kt-page` and `/kt-scenario` refuse to generate a business vertical without an accepted `spec_path`. Verify: `pytest tests -k spec_required`
- [ ] **L0** — `e2e/QUALITY_MANIFEST.md` carries the platform auth row and leaves domain rows to accepted PRDs. Verify: read the manifest

**First-hour experience**

- [ ] **L2** — From an empty directory: call the globally listed `project_init` tool with an intent and primary domain, run `scripts/bootstrap.sh`, bring the stack up, `scripts/db.sh apply`, `scripts/create-super-admin.sh`, `scripts/quality-gate.sh all`, then `KT_SCAFFOLD_OFFLINE_BUNDLE=<verified-bundle> KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-digest> scripts/e2e.sh auth` — all succeed with no source file edited by hand. Verify: run the sequence in a scratch directory
- [ ] **L0** — No brand, wrapper directory name, or excluded-engine name appears anywhere in the scaffolded tree, and the company prefix appears only in the three tooling locations named in section 2. Verify: grep the scratch directory for the token list in section 2, then confirm every hit is a command name, the `kt-scaffold` package or `.kt-scaffold/`
- [ ] **L2** — The bank-managed global `kt-scaffold` installation appears under the same server key and exposes the same tool schemas in Claude Code, Codex, Cursor and another approved MCP client. Verify: start fresh sessions with no project-local server configuration and compare their tool listings

---
## 15. Open questions and decision record

The original eight questions and the four owner amendments of 2026-08-05 are resolved. They are
recorded rather than deleted so a reader can see what changed and what each choice costs.

| # | Question | Resolution | Where it lands |
|---|---|---|---|
| Open Question 1 | How is the environment-variable prefix chosen? | Derived from the product slug and checked against the current process and target tree; no claim is made about unrelated repositories | `/kt-init` input 6, section 8 |
| Open Question 2 | What language is the scaffold server and generated backend written in? | Python; the generated application backend is fixed to FastAPI | Sections 3, 5 and 8 |
| Open Question 3 | What is the cache layer in the file-backed mode? | Retired with that mode. Only the Redis infrastructure socket ships; a domain adapter and call site require an accepted PRD | Decision 1, Requirement 2 |
| Open Question 4 | Is the observability stack scaffolded by default? | Yes. The init option defaults enabled; explicitly disabling it omits the infrastructure bundle. Application instrumentation remains capability-owned in both variants | `/kt-init` input 10, sections 3, 5, 10 and 12 |
| Open Question 5 | What is the default locale set? | Init defaults to English and Turkish; explicit overrides are accepted, and unsupported report-label locales use canonical English labels | `/kt-init` input 9, Decision 7 |
| Open Question 6 | Are deployment charts scaffolded by default? | Always written, in every scaffold, against the cluster contract of section 12 and in two overlays. Not an `/kt-init` question | Sections 3, 10 and 12, Decision 16 |
| Open Question 7 | Is `done_report` advisory or blocking? | Advisory. It reports the gap and returns success; the shortfall reaches the hand-off summary through the run-report skeleton | Decision 6, Requirement 5 |
| Open Question 8 | What language are the run-report group labels in? | Locale-driven for supported mappings; otherwise canonical English | Decision 7 |
| Owner Amendment 9 | Who chooses the migration tool? | The unit technology profile fixes SQLAlchemy/Alembic; the vibe coder and agent do not choose it | Decision 18 |
| Owner Amendment 10 | Does a generic business resource ship? | No. Init ships platform auth/health and a domain/PRD workspace; the first business vertical requires an accepted PRD | Decisions 17 and 20, section 11 |
| Owner Amendment 11 | Does init preview before writing? | No. Required intent plus structured profile resolution precede one transactional write; failures roll back init-owned paths | Decision 19 |
| Owner Amendment 12 | What authentication ships? | JWT access tokens, RBAC, and an application-level super-admin bootstrap in the FastAPI baseline | Decision 20 |

### Decision and requirement index

Numbers are stable identifiers assigned in the order the decisions were taken, so they do not run in
document order. This index is the map.

| # | Decision | Section |
|---|---|---|
| 1 | PostgreSQL is fixed; persistence is profile-owned | 6 |
| 2 | The mandatory column block | 6 |
| 3 | *Retired* — was the two-mode column block; folded into Decision 2 | — |
| 4 | *Retired* — was the path between engines; removed with the second mode | — |
| 5 | One corpus, everything else generated | 7 |
| 6 | `done_report` is advisory, not blocking | 8 |
| 7 | Run-report group labels follow the locale answer | 9 |
| 8 | One command namespace, `kt-`, fixed for every scaffold | 7 |
| 9 | Every client is served through its own native mechanism | 7 |
| 10 | One bank-managed implementation exposes identical tools over stdio and internal Streamable HTTP; the CLI retains local parity | 8 |
| 11 | A scaffold is a living relationship with the corpus, not a one-way copy | 8 |
| 12 | Provisioning: internal HTTP control plane, controlled wheel, or OCI/offline bundle; one implementation | 8 |
| 13 | Interoperability: disjoint namespaces and a constitution projection | 8 |
| 14 | The generator is not part of what it generates | 3 |
| 15 | Offline is four shipping tiers for each explicitly admitted platform matrix | 8 |
| 16 | The deployment target is a design constraint, and both overlays ship from day one | 12 |
| 17 | Project intent and domain come before business code | 4 |
| 18 | The vibe coder selects a persistence profile, not a loose tool name | 6 |
| 19 | Init writes once and transactionally; it has no dry-run mode | 8 |
| 20 | Authentication defaults to JWT, RBAC and application super-admin | 4 |

| # | Requirement | Enforced by |
|---|---|---|
| 1 | Engine-specific behavior stays inside the selected persistence adapter and repository boundary | Profile gate and review |
| 2 | No cache call site in the fresh platform baseline; domain caching requires an accepted PRD | Profile gate and spec traceability |
| 3 | One schema authority is recorded; migrations are generated from it and drift is rejected | Profile adapter; `schema-check.yml` |
| 4 | *Retired* — was the concurrency-assumption note on an engine change; removed with the second mode | — |
| 5 | An unsupported tier claim always reaches the hand-off summary | `done_report` |
| 6 | A prefix collision detected in the current process or target tree is never resolved silently | `/kt-init` conflict scan |
| 7 | No generated command collides with a client built-in | The renderer's reserved-name list; `governance-drift.yml` |
| 8 | The generated `CLAUDE.md` stays under 200 lines | The renderer; `governance-drift.yml` |
| 9 | Every tool has a byte-identical command-line equivalent | `pytest -k cli_parity` |
| 10 | An update reports every file: no silent overwrite, no silent skip | `pytest -k update_conflict` |
| 11 | Every run-time dependency is pinned by version, integrity hash or OCI digest | `pytest -k pinning` |
| 12 | No image reaches a workload by tag or from outside the internal registry | `charts-render.yml` |
| 13 | No chart authors a Secret, and no secret value enters a values file or overlay | `charts-render.yml`; secret scanning |
| 14 | Every rendered pod meets the security floor of section 12 | `charts-render.yml` |
| 15 | Every workload renders a NetworkPolicy with both directions declared | `charts-render.yml` |
| 16 | Runtime has no internet, SaaS, public-registry, CDN or external-telemetry dependency | `charts-render.yml`; `pytest -k runtime_network_boundary`; egress-blocked stack test |

### Revisions of 2026-08-04, from an ecosystem survey

After those questions were resolved, the plan was checked against the state of the agent-tooling
ecosystem — the client documentation as it stands today, the rule-synchronization tools that solve
part of this problem, and the spec-driven toolkits that solve a neighbouring one. Six things
changed. None reverse a resolved question; each is either a correction against a client's actual
behaviour or a gap the survey exposed.

| # | Finding | Change |
|---|---|---|
| R1 | `/init` is a built-in of Claude Code and the behaviour of a same-named project skill is unspecified | Every command carries the `kt-` namespace, and the renderer holds a per-client reserved-name list — Decision 8, Requirement 7 |
| R2 | Claude Code targets under 200 lines for `CLAUDE.md`, does not read `AGENTS.md`, and now supports path-scoped `.claude/rules/` with `paths:` front matter | `AGENTS.md` becomes the primary document, `CLAUDE.md` imports it and stays thin, path-scoped rules go where the client can scope them — Decision 9, Requirement 8 |
| R3 | Custom commands have been merged into skills in Claude Code, and the Agent Skills format is a published open standard that Codex reads too | `.claude/commands/` is dropped; commands ship as skills, and the same bodies are emitted at Codex's discovery path — Decision 9 |
| R4 | Approved agent clients need one consistent tool surface without project-by-project server setup | One bank-managed plane is registered globally as internal Streamable HTTP or local stdio, with six bilingual pairs; MCP owns deterministic initial bytes and local clients own safe target publication plus later adaptation — Decision 10, Requirement 9 |
| R5 | Copy-once scaffolding freezes every generated project at the template version that made it; the tools that replaced it keep an answers file and an update command | `/kt-init` writes `.kt-scaffold/`, `/kt-update` replays it and classifies every file — Decision 11, Requirement 10 |
| R6 | spec-kit owns spec-driven development as a category, and there is no reason to compete with it | Disjoint command namespaces and a generated `constitution.md` projection, so both systems run in one repository — Decision 13. Client-native files remain project-governance projections; package provisioning is centralized — Decision 12 |
| R7 | Section 3 described the generator and the generated project as one tree, so `/kt-init` in an empty directory had nothing to run it with and `bootstrap.sh` was post-clone setup for a tree nobody clones | Two trees, two artefacts. The package and the templates stay in the generator repository; the project pins a version and calls it — Decision 14, sections 3.1 and 3.2 |
| R8 | Offline appeared nowhere, while the browser runtime every L2 claim depends on was left unpinned | Two provisioning paths including a digest-pinned OCI/offline bundle, four shipping offline tiers, and a pinning/integrity requirement covering Playwright plus Chromium — Decisions 12 and 15, Requirement 11 |

**Second revision, 4 August 2026 — the adopting organization's standards.** The plan was then read
against the organization's implementation procedure for AI-assisted development, its
approved-technology list, and the policy files of the fourteen agents that enforce them. Two things
came out of it.

*What the reading confirmed.* The procedure's "golden path" — development starts from an approved
template and a ready project skeleton, versioned in step with the rule sets — is this boilerplate,
described independently. Its first control layer states that the machine-readable form of the
guidance documents lives **inside the approved template**, which is the corpus of section 7 arriving
at the same design from the other direction. Its requirement that findings feed back into the guides
and the templates is Decision 11's update path, stated as an obligation rather than an option. And
its data-security rules for command-layer servers — only allowlisted servers may run, source and
dependencies verified, write operations require approval — are the security envelope of section 8,
with Decision 10's bank-managed dual transport, structured patch preconditions and local CLI parity
turning out to be the posture that survives the constraint.

*What the reading changed.*

| # | What was found | What changed |
|---|---|---|
| R9 | The file-backed storage engine is on the organization's forbidden list | The second mode is removed entirely: section 6 is now a single-engine persistence contract, the `db_engine` question is gone from `/kt-init`, and the structural discipline the two modes paid for is re-argued on its own merits — Decision 1 |
| R10 | Several stack items are not on the approved list, and one corporate document contradicts another about compiled languages | An explicit per-profile conformance summary in section 5; baseline exceptions are numbered and a selected profile may add its own visible exception |
| R11 | The gate the organization enforces reads deterministic scanner output, not model judgement | The scanners are named rather than implied: Semgrep, Trivy, forge-native dependency updates and push protection, all pinned — section 5 and `security-scan.yml` |
| R12 | Language and framework versions are constrained, and the plan carried stale ones | Each backend profile carries an explicit supported-runtime matrix and a pinned BOM; the plan never resolves `current` or `latest` at scaffold run time |
| R13 | The deployment side was one line of stack table and one line of workflow list, while the reference carries a measured cluster contract and a gate that enforces it. A boilerplate whose output cannot pass the target cluster's constraints teaches every project built from it to discover them late | Section 12 is now the deployment contract: the cluster assumptions an adopting team confirms, the contract every chart honours, the render gate that enforces it, two overlays instead of one, and a corpus rule so an agent working in a scaffold knows the constraints before it writes the code — Decision 16, Requirements 12 to 15, methodology column 13 |

**Owner revision, 5 August 2026.** Current recommendations were checked against official project
repositories and documentation; the runtime uses a versioned catalog rather than live popularity
lookups.

| # | Finding | Change |
|---|---|---|
| R14 | [Alembic](https://github.com/sqlalchemy/alembic) is SQLAlchemy's native MIT-licensed migration project and the dominant ecosystem fit | Python/PostgreSQL proposes SQLAlchemy + Alembic and records ORM metadata as schema authority |
| R15 | Backend choice must not be delegated to project intent or an agent | Node/NestJS/Prisma support and init-time backend selection are removed; `technology-profile.yml` fixes FastAPI and Alembic |
| R16 | A free-text project intent prevents blind trial scaffolds but does not make arbitrary writes safe | `project_init` and `kt-scaffold init --intent ... --primary-domain ...` require both context fields and write once through staging and a journaled publish; global dry-run is removed |
| R17 | A generic resource contradicts domain-first/spec-driven development | The business walking slice is removed; platform auth/health ships and every business generator requires an accepted domain PRD |
| R18 | [Spec Kit's core flow](https://github.github.com/spec-kit/) is Spec → Plan → Tasks → Implement, with a [roadmap/spec-of-specs](https://github.github.com/spec-kit/concepts/spec-of-specs.html) pattern for oversized scopes | Domain folders carry `DOMAIN.md`, `roadmap.md` and independently deliverable PRDs linked to plans and tasks |

What the survey did **not** change, because the survey confirmed it: the drift gate has essentially
no equivalent in the rule-synchronization tools, which overwrite hand edits rather than failing a
build; the evidence tiers and the fixed run-report skeleton have no equivalent anywhere found; and
the verify-then-commit-a-scenario split in methodology column 5 matches the practice the browser
automation community converged on independently.

### Decisions that carry a stated cost

These choices were made over alternatives that were better on one axis. The costs are recorded
in the sections above and repeated here so they are not rediscovered as surprises:

1. **Three baseline exceptions to the approved-technology list** cost this project arguments it has to
   win at a gate it does not control, and the risk that one of them is refused after the tree is
   built. They buy an architecture that is coherent rather than assembled from whatever was already
   approved. The alternative — conforming on every point — was rejected for E1 by the owner outright,
   and for E2 and E3 because conforming would mean a synchronous driver under an asynchronous
   framework and a definition of done with no L2 tier (section 5).
2. **One engine** costs the prototype and single-user cases a scaffold they could have used, and
   costs this plan a two-mode contract it had already designed and argued for. It buys a tree that
   passes the adopting organization's gate, which is the only test that matters here. The structural
   discipline the second mode paid for — the codec boundary and application-side identifier — is
   kept on its own merits (Decision 1).
3. **Charts in every scaffold** costs a team that deploys differently one directory deletion, and
   buys a team that needed the pattern the fact that it exists. The asymmetry of those two costs is
   the whole argument. **Fixing the deployment target** (Decision 16) costs more than that: a team
   deploying somewhere else inherits constraints it does not need — read-only root filesystems,
   digest-only images, declared network — and has to relax them deliberately. That is the intended
   direction of travel. Relaxing a constraint is a decision someone makes once; discovering one after
   the application already depends on its absence is a rewrite.
4. **Locale-driven report labels** cost cross-locale reports their textual comparability, and buy
   each team labels it reads without translating. The one-to-one label map in Decision 7 keeps
   mechanical translation available to anything that needs to compare across scaffolds.
5. **A company-namespaced command surface** costs anyone adopting this outside the company one
   constant to change, and a repository that already uses the `kt-` prefix for something else a
   collision to resolve. It buys collision immunity against every client built-in and other
   managed command surface, and one command vocabulary across the fleet. The alternative — a namespace
   derived per scaffold from the product slug — was rejected because it makes the commands different
   in every repository, which is the opposite of a shared architecture (Decision 8).
6. **An update path** costs a manifest, an answers file and a conflict-reporting code path that must
   be maintained honestly. It buys a fleet that can be brought forward when the corpus improves.
   The alternative — regenerate into a scratch directory and diff by hand — was rejected because it
   is exactly the manual reconciliation this plan removed from governance, reintroduced one level up
   (Decision 11).
7. **Keeping the generator out of the generated project** costs a scaffolded repository the ability
   to regenerate itself from its own source: it can call the pinned version, but it cannot read or
   patch it. It buys one implementation, one test suite and no version skew between a project's copy
   and the release. The alternative — a trimmed companion copy inside each project — was rejected
   because two copies of one generator is the drift this plan exists to prevent, moved up a level
   (Decision 14).
8. **Shipping all four offline tiers per admitted platform matrix** costs a platform-specific
   Playwright/Chromium build, integrity manifest and disconnected admission run for every supported
   OS/architecture/runtime tuple. It buys honest L2 evidence without a hidden browser download. The
   alternative — merging incompatible matrices or treating a missing browser as a skip — fails
   methodology column 4 in the document that defines it (Decision 15).
9. **One backend/persistence profile** costs callers framework choice. It buys deterministic
   architecture, one dependency bundle, one quality path, and no agent-selected backend technology
   (Decision 18).
10. **No generic business slice** means a fresh scaffold demonstrates platform wiring rather than a
   copyable CRUD resource. It buys honest domain-first development: the first business code is
   shaped by the project intent and an accepted PRD, not by a placeholder entity (Decision 17).
11. **Direct transactional init** removes a preview loop. It buys a clear one-shot start and therefore
   requires stronger staging, validation and rollback tests (Decision 19).

### What is now blocking

There is no migration-tool selection: SQLAlchemy models and Alembic are fixed by the technology
profile. Unsupported migration binaries are rejected rather than accepted as overrides.

The implementation now exists. This document itself remains L0 evidence; every L1 and L2 claim in
section 14 is established only by its named executable check and the final run report.

Two client details remain rollout responsibilities: that each bank-managed client can register the
workspace-bound local stdio command and the separate internal Streamable HTTP governance URL; and
that each client reads its admitted project projection path. Protocol tests cover both authority
surfaces, but the managed-fleet runtime matrix remains an acceptance criterion. Governance discovery
cannot block local `project_init`.

Air-gapped browser verification is now a deliverable for each admitted bundle matrix: the bundle
contains the pinned Playwright dependency cache and matching Chromium tree, and the disconnected
runner proves the same authentication scenario. Supporting another OS/architecture tuple remains
an explicit extension because its browser and wheel artifacts must be built and admitted separately.
