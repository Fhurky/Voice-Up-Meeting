# Implementation initiatives and resolved ambiguities

This record captures decisions taken autonomously while implementing `scaffolding-plan.md`. It is
not a substitute for a capability PRD and is never copied into a scaffolded product repository.
Later numbered decisions explicitly supersede earlier ones where the product direction changed.

1. **Atlas was ignored.** The word was treated as the confirmed typing error; no Atlas dependency,
   command, schema source, or migration path was introduced.
2. **No Claude or Codex plugin is produced.** There is no plugin manifest, marketplace artifact,
   install deep-link, client extension, or client-specific server. Project-local skills and rules
   are governance projections only.
3. **The global MCP is a knowledge plane, not a workspace authority.** The bank-managed
   `kt-scaffold` implementation exposes the same five read-only operations, each with English and
   ASCII-safe Turkish aliases, over local stdio and internal
   Streamable HTTP. Generated projects contain no MCP server registration. MCP exchanges bounded
   project metadata, canonical artifacts, update intent and reconciliation decisions only. Local
   Codex/Claude agents own filesystem mutation, execution, database work and evidence.
4. **Project intent replaces dry-run.** Init requires a concrete intent and primary domain, renders
   once into a sibling staging tree, validates it, and publishes transactionally. There is no
   dry-run or disposable trial project mode. Both MCP and CLI accept one validated input object;
   the CLI is deliberately non-interactive, so missing required fields fail while optional fields
   come from explicit flags, `--answers`, or recorded defaults.
5. **Backend and persistence are fixed.** The only backend is Python/FastAPI and the only persistence
   chain is async SQLAlchemy/asyncpg + Alembic + PostgreSQL. Neither caller nor coding agent selects
   an alternative.
6. **Desired state remains migration authority.** Baseline migrations are generated from and drift
   checked against SQLAlchemy authority. A later schema request never fabricates handwritten or
   empty SQL from prose: the accepted PRD is recorded, the authority is changed through the domain
   flow, and the profile-native generator command is returned for review and execution against the
   local disposable PostgreSQL stack.
7. **There is no sample `item` domain.** Init creates only `specs/<domain>/DOMAIN.md`, an empty
   roadmap, and `PRDs/`. Business generators reject Draft or missing PRDs and operate only after
   `Status: Accepted`.
8. **Authentication is deliberately small but real.** Both profiles implement one shared JSON
   contract for JWT login and `/auth/me`, tenant context, RBAC guards, and an application-level
   `super_admin` bypass. The bootstrap is idempotent and reads credentials from environment input.
9. **Application super-admin is not operating-system or database root.** It has all application
   permissions and can switch tenant context. Containers and PostgreSQL application connections
   remain non-root/non-superuser because elevating infrastructure identity would violate the bank
   boundary without adding application capability.
10. **Offline is a hard execution boundary.** Runtime services have an internal-only network and no
    SaaS, CDN, public telemetry, or external listener dependency. Base images are digest-pinned and
    internal-registry-overridable; dependency builds support a fail-closed wheelhouse/npm-cache
    mode; the controlled artifact factory is the only place allowed to assemble the air-gap bundle.
11. **MCP SDK compatibility is pinned.** The implementation uses released `mcp==2.0.0` APIs for
    stdio and Streamable HTTP rather than designing against an unverified future major version.
    Promotion requires both protocol tests and the four-client conformance matrix to remain
    identical.
12. **No version-control authority was inferred.** The implementation, generators, tests, database
    operations, and local stack checks do not run a VCS mutation. No commit was created.
13. **Browser evidence is client-neutral and bundled.** The E2E harness is ordinary lockfile-pinned
    Node.js/Playwright code, not a second MCP server or a client plugin. Every admitted offline
    bundle matrix carries the matching Chromium tree, verifies it through `SHA256SUMS`, selects it
    with `PLAYWRIGHT_BROWSERS_PATH`, and fails L2 admission when it is absent or incompatible.
14. **Docker Desktop needs an explicit edge network.** An `internal: true` bridge cannot publish a
    usable loopback port on Docker Desktop. Data, cache, backend and frontend remain on the internal
    application network; only Nginx, and optional Grafana, also join a separate edge bridge and bind
    loopback. Contract tests reject any other host-published service.
15. **The backend choice is not an init input.** Backend and persistence values remain recorded for
    audit/update compatibility, while the public CLI and MCP schema expose no framework selector.
16. **Technology authority is machine-readable.** `technology-profile.yml` records required,
    conditional and forbidden technologies and is copied into every scaffold.
17. **Live database tests are destructive only inside `_test` databases.** The integration suite
    refuses any database name without the suffix. CI creates a disposable database, applies
    the real migration history, runs idempotent super-admin and authorization checks, and removes
    the isolated stack and volumes afterward.
18. **Acceptance prose is never executable evidence.** A generated domain browser scenario contains
    an explicit failing guard until the implementer replaces it with assertions. The quality gate
    discovers every suite runner, so an unimplemented scenario blocks L2 rather than passing on a
    generic page locator.
19. **Browser readiness is polled after the fixed-profile gates.** The gate polls readiness before
    launching Chromium, eliminating transient startup races without masking an unavailable service.
20. **Async SQLAlchemy declares its greenlet runtime.** The Python profile pins
    `sqlalchemy[asyncio]`, and both hash-locked requirement sets include the resolved `greenlet`
    wheel. A clean offline container therefore has the same async behavior as the development
    environment.
21. **Natural-language input is escaped per output context.** Product name and project intent remain
    free text, but code, JSON, YAML and HTML projections use context-specific serialization. API
    paths, frontend routes, permission codes and generator version are separately constrained so
    answer input cannot become generated source or shell syntax.
22. **Evidence tiers require the complete project gate.** A successful backend-only or
    frontend-only scope is useful diagnostic evidence but remains L0 for project-level reporting.
    Only `scope=all` can record L1, and only that full gate plus real browser execution can record
    L2.
23. **Generator version is tool-owned but historically readable.** Persisted semantic versions from
    older generators can be loaded only so `kt-scaffold update` can advance them to the installed
    version. Init cannot impersonate another release, callers cannot override the field, and an
    older installation refuses to rewrite a project produced by a newer release.
24. **The first accepted vertical must move real data.** Domain generation produces a tenant-safe,
    soft-delete-aware repository query, application service, protected typed endpoint, frontend
    service and localized loading/error/empty/list surface. A constant placeholder response is not
    a walking skeleton even when every layer has a file.
25. **A complete gate owns its disposable database.** `quality-gate.sh all` creates a uniquely named
    `_test` database, applies the actual migration history, enables the profile's PostgreSQL
    integration suite and drops the database through an exit trap. Backend-only diagnostics do not
    mutate a configured application database.
26. **Quality evidence is machine-observed.** Generated gates emit stable step and test markers;
    the MCP/CLI operation derives its result rows and pass counts from those markers. Process exit
    zero without the required marker protocol is not promoted to L1 or L2 evidence.
27. **Offline browser execution has one admitted entry point.** `scripts/e2e.sh` defaults to a
    checksum-sealed, platform-matched bundle and binds npm plus Playwright only to bundle content.
    An explicit bank-private-index mode is allowed, while public registries and an implicit online
    fallback are rejected.
28. **Migration drift uses an isolated boundary.** Alembic validation runs against the gate-owned
    disposable `_test` database and never resets or introspects the developer's main database to
    manufacture drift evidence.
29. **Update is an all-or-nothing replay.** Every prospective path is preflighted before a byte is
    written. Any user edit leaves the complete tree, recorded answers and manifest unchanged; a
    mid-write failure rolls all created and replaced files back. Corpus removals remain visible
    manual steps and are never auto-deleted.
30. **Running project code requires explicit trust.** The global MCP/CLI quality operation refuses
    execution unless the caller explicitly consents, rejects a symlinked or manifest-drifted gate
    script, executes its canonical absolute path, and passes an allow-listed environment rather
    than every ambient workstation secret.
31. **JWT validation is identity-bound and secrets fail closed.** The FastAPI profile has no
    production signing fallback, constrains the configured algorithm, and rejects missing or weak secrets.
    The bootstrap password travels over standard input, not a process argument or persisted answer.
32. **Tenant lifecycle is enforced at the data query.** Generated tenant-scoped repositories require
    the record and its owning tenant to be non-deleted, and the tenant to be active. This closes the
    window in which an otherwise valid JWT could read data after tenant deactivation.
33. **Migration jobs receive only migration authority.** Alembic uses a typed DB-only settings view
    and does not require or receive the JWT signing secret. The non-root migration image runs the
    direct Alembic deployment command.
34. **Offline admission has an out-of-band trust anchor and closed inventory.** The bank distributes
    the digest of `SHA256SUMS` separately. Consumers verify that digest, reject symlinks and any
    unlisted or missing file, validate the platform, and then use only its absolute wheelhouse/npm
    cache contexts. Generator and build-system Python artifacts additionally use reviewed
    `--require-hashes` locks before downloaded code can execute.
35. **Generated CI cannot silently become connected CI.** Every Compose-building workflow requires
    the admitted bundle and digest, sets `DEPENDENCY_MODE=offline`, exports both absolute BuildKit
    contexts, verifies the bundle, and loads the sealed runtime image archive before `--build`.
36. **Migration release identity follows source identity.** Environment overlays must carry a full
    nonzero lowercase source revision. The migration chart preserves it as provenance and derives a
    distinct immutable Job name, so two source releases cannot alias the same migration job.
37. **Namespace-local network peers are product-scoped.** Every intra-namespace pod selector includes
    the same `app.kubernetes.io/part-of` label. A component named `backend` from another application
    in a shared namespace therefore cannot satisfy this product's database or cache policy.
38. **Writable OCI mounts require a bank workspace boundary.** The OCI wrapper requires a canonical,
    absolute, non-root workspace and mounts only a strict descendant that is either empty for init
    or contains both regular scaffold markers. Home, workspace root, partial projects and symlinks
    are rejected before Docker starts.
39. **Release build contexts exclude workstation state.** Root and frontend Docker ignore policies
    exclude environment files, package-manager credentials, keys, dependency trees and artifacts.
    Release processes and the frontend development process run non-root; the frontend source bind
    is read-only while its dependency volume remains writable.
40. **Plan verification selectors are executable contracts.** Every `pytest -k` selector named by
    the acceptance matrix selects at least one focused test, including rule/skill parity, tool
    schema and CLI parity, transactional update, pinning, reporting, domain-first and spec-required
    behavior. A zero-test invocation cannot be mistaken for evidence.
41. **Native artifacts are assembled on their target platform.** The artifact factory refuses to
    seal a bundle when its own platform differs from the requested OCI platform. Wheel tags and
    Playwright binaries therefore cannot be relabelled as a foreign platform by changing metadata.
42. **Baseline logging is structured and bounded.** FastAPI emits JSON request-completion records
    with request ID, method, path, status and duration while excluding headers, bodies and queries.
43. **Read-only frontend mounts are granular.** Compose mounts source and configuration files
    read-only instead of mounting all of `/app` read-only. The container-owned `node_modules`
    volume stays writable, so a clean bootstrap retains the intended non-root and immutable-source
    boundary without failing dependency installation.
44. **Tenant lifecycle exists in desired-state authority.** The SQLAlchemy `Tenant` model and
    Alembic baseline include `is_active`, matching the repository's active-tenant predicate.
45. **The Python application image carries runtime dependencies only.** Development/test tooling is
    kept outside the non-root release image.
46. **Named BuildKit contexts are explicit in every supported invocation.** Compose, connected
    examples and offline examples supply the Python wheelhouse and frontend npm-cache contexts;
    admitted offline builds cannot fall back to the network.
47. **Generated Python is formatter-stable for long domain names.** Imports, constructors,
    dependency declarations, router setup and response expressions choose deterministic multiline
    forms when capability-derived identifiers exceed the configured line length. Two long accepted
    verticals were generated together and passed Black, isort, Ruff and strict mypy unchanged.
48. **Persistent observability state uses image-owned mount points.** Mounting new named volumes at
    arbitrary `/tmp` paths left their roots owned by UID 0 and trapped non-root Loki and Tempo in a
    restart loop. Their state now mounts at `/loki` and `/var/tempo`, directories the pinned images
    own as UID/GID 10001 so fresh-volume copy-up preserves ownership. Both processes explicitly run
    as 10001 with a read-only root filesystem, every capability dropped and `no-new-privileges`;
    no root initializer is required.
49. **Writable Kubernetes volumes have an explicit filesystem group.** Docker's fresh-volume
    copy-up does not apply to Kubernetes `emptyDir` or persistent claims. Every pod with a writable
    volume declares an `fsGroup` equal to its non-root `runAsGroup` and uses
    `fsGroupChangePolicy: OnRootMismatch`. The chart contract detects any missing, mismatched or
    unbounded writable volume before promotion.
50. **Remote generation was removed from the MCP boundary.** PatchSet and WorkspaceSnapshot solved a
    mutation problem the product does not assign to the central service. The global MCP neither
    receives nor reconstructs a source tree and never claims project conformance. The optional CLI
    remains available for deterministic local bootstrap and local-only operations.
51. **Transport parity applies to knowledge tools only.** Stdio and Streamable HTTP expose the same
    five tools: blueprint, artifact catalog, selective artifact retrieval, update check and
    reconciliation validation. Protocol tests reject target paths, workspace, patch and execution
    inputs on every tool.
52. **The MCP application never becomes the public authentication edge.** Its HTTP listener accepts
    loopback only. The bank sidecar/gateway owns TLS or mTLS, OAuth 2.1 discovery, bearer-token
    audience/scopes, request limits and audit identity; a non-loopback application bind fails.
53. **Quality evidence is local by design.** MCP does not execute or finalize project gates. Local
    agent tools or the optional CLI run the managed command, database and browser scenarios and own
    the resulting evidence. A reconciliation receipt is labelled `local-agent-attested` and is not
    presented as execution proof.
54. **Metadata minimization replaces snapshot filtering.** The generated exporter reads one bounded
    JSON manifest and never walks source, dependency, VCS, secret or database paths. The MCP request
    body is capped at 1 MiB; the exported metadata itself is capped at 256 KiB.
55. **URL-only governance does not require the generator.** Generated repositories ship
    standard-library governance and metadata exporters. Read-only drift checks work locally; edits
    are reconciled and applied by the local agent or the optional CLI, never by remote MCP.
56. **Governance updates are intent-level and authority-aware.** `mandatory` behaviors may be
    reworded or strengthened but not weakened; `recommended` artifacts may be adapted, deferred or
    rejected with rationale; `project-owned` artifacts remain outside central control. Deterministic
    proposals and receipts make that semantic negotiation auditable without pretending to inspect
    the workspace.
57. **Every public command is bilingual without duplicating behavior.** Five MCP knowledge
    operations are discoverable under English and ASCII-safe Turkish names, and every local CLI plus
    generated Claude/Codex skill has a Turkish alias. Each alias delegates to the same operation and
    parity tests require identical structured results.
58. **The only full-stack UI exception is Streamlit.** React/Vite plus FastAPI separation is the
    default; SSR and Next.js are forbidden and SSE is allowed. An accepted PRD may select Streamlit
    only when the complete UI is limited to prompt input, chat responses and history. Chainlit and
    general-purpose full-stack UI use remain outside the baseline.
59. **Dependency admission is an offline executable contract.** Direct Python authorities use exact
    pins; npm manifests, OCI digests and workflow actions join them in one normalized inventory.
    `dependency-admission.json` binds that inventory to release-date, advisory or explicit
    compatibility-exception evidence. Any pin change invalidates the reviewed digest before a
    network call or package installation occurs.
60. **Security configuration reaches both generator and generated repositories.** A bank-managed
    GitHub Enterprise Dependabot service may propose changes only through internal mirrors.
    Gitleaks runs through a repository-local pre-commit hook and the offline security workflow;
    Semgrep rules and the Trivy database must belong to one checksum-verified, closed and
    symlink-free scanner snapshot; an unlisted file fails before a scanner can consume it.
61. **Optional scaffold surfaces have explicit admission variants.** The generated ledger selects
    the reviewed observability-on/off entry from the persisted answer and rejects any mismatch
    between that answer and the optional files. Canonical image authority keeps both variants on
    the same normalized dependency identity today; separate variant keys prevent a future optional
    authority change from being admitted implicitly. Generation does not bless a newly calculated
    digest.
62. **Migration tooling cannot silence application logging.** Alembic preserves existing logger
    state when loading its own console configuration. The PostgreSQL integration gate proves that
    access logging remains enabled after upgrade and desired-state checks; application logging owns
    one idempotent JSON stdout handler without deleting host or test-runner handlers.
63. **The walking skeleton is exercised as one local system.** A fresh observability-off project
    builds from digest-pinned images, applies the real PostgreSQL migration, creates a super-admin,
    runs backend, frontend, OpenAPI, chart and governance gates, and completes the Playwright login
    scenario through loopback Nginx. The chart renderer reports a clear error when the pinned
    `kt-scaffold`/Helm toolchain is absent, and the matching Playwright revision comes from the
    platform-specific sealed bundle.
64. **MCP localization is semantic while schemas stay universal.** The Turkish tool names and
    descriptions state the same operation as their English pair; argument and result field names
    intentionally remain identical, ASCII-safe machine contracts. Canonical inventory now includes
    rule, generated command-skill and reconciliation-guidance bodies. Stdio and Streamable HTTP
    protocol tests invoke all twelve names, compare every alias schema/result and reject undeclared
    workspace, target, caller-supplied patch and execution context on every tool.
65. **Generated Turkish guidance is complete, not a translated heading.** Turkish command skills,
    the test-run-report skill and run-report bodies use Turkish descriptions, arguments,
    equivalence notes, instructions and structural labels. The English projections remain canonical
    for English/fallback locales, and regression tests reject mixed structural prose.
66. **Deterministic initial scaffolding belongs to a trusted local MCP boundary.** This supersedes
    initiatives 3, 50, 51, 54 and 55 only for empty-project initialization. `project_create` /
    `proje_olustur` is available only through a local stdio process bound to one explicit workspace
    root at startup. It invokes the installed generator in-process; it downloads and executes no
    delivered code. The remote governance service receives no target path or caller workspace.
67. **Creation output is bounded evidence, not source delivery.** Local stdio returns only status,
    counts and expected/observed tree digests. CLI and local stdio must produce identical trees for
    the same validated answers and generator version. Streamable HTTP exposes blueprint and
    governance operations only.
68. **The start wizard exists only where creation authority exists.** The bilingual,
    user-controlled `project_start` / `proje_baslat` prompt asks only for missing business context,
    derives defaults and admitted client selection, obtains one creation confirmation and directs
    exactly one local creation call. HTTP has neither the prompt nor a creation tool.
