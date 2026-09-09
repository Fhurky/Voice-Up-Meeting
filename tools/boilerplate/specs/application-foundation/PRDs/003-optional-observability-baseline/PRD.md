# PRD — Optional observability baseline

Status: Draft

Document version: 0.1.0

Domain: [Application Foundation](../../DOMAIN.md)

Roadmap: [Capability 003](../../roadmap.md)

## Intent

Allow a generated application to include a secure, offline-capable observability infrastructure
baseline—structured application logs, OpenTelemetry Collector, Prometheus, Tempo, Loki, and Grafana—or
omit that infrastructure cleanly, without inventing business telemetry or creating external runtime
dependencies.

This retrospective Draft records an existing scaffold variant. It does not claim production SLOs,
retention, scale, or operational acceptance.

## Actors and outcomes

- An application developer gets baseline request correlation and health signals without selecting a
  telemetry stack.
- A service operator can run a local or namespace-scoped telemetry stack with internal-only endpoints.
- A platform operator may decline the optional stack at scaffold time and receive no stale charts,
  Compose overlays, configuration, or rules for absent components.
- A security reviewer can verify that logs and telemetry exclude sensitive content and do not export to
  public services.
- A domain owner retains responsibility for capability-specific metrics, traces, dashboards, and alerts.

## Verified baseline and gap

The technology profile enables observability by default and specifies structured JSON logs, request
correlation, OpenTelemetry Collector, Prometheus, Tempo, Loki, and Grafana. The generated tree includes
local configurations, Compose overlay, an observability Helm chart, baseline dashboard, persistent state
mounts, and hardened non-root workloads. `observability=false` removes the infrastructure directory,
Compose overlay, and chart during rendering.

Current gaps include approved production retention and classification, resource sizing, high
availability, alert ownership, SLOs, remote write/export boundaries, access control, backup, and live
signal continuity evidence across application, collector, stores, and dashboard.

## Decisions, invariants, and trust boundaries

1. Observability is an admitted scaffold variant, not a caller-selected alternative stack.
2. Baseline application signals are health, readiness, structured request completion, and request
   correlation only.
3. Capability-specific metrics, spans, dashboards, alerts, and SLOs require the owning accepted PRD.
4. Headers, bodies, query strings, tokens, credentials, and sensitive business data are forbidden in
   baseline telemetry.
5. Runtime telemetry remains internal with no public SaaS, CDN, external exporter, or implicit egress.
6. Disabling observability removes optional infrastructure and related rules cleanly but does not disable
   safe application logging.
7. Local telemetry infrastructure is development/verification baseline, not proof of production scale or
   retention compliance.

## Functional requirements

1. Application request logs must be structured JSON and include request ID, method, normalized path,
   status, and duration.
2. Logging configuration must be idempotent, preserve host/test handlers appropriately, and remain
   active after migration tooling initializes logging.
3. The observability-on variant must include internal collector, metrics, trace, log, and dashboard
   configuration with explicit endpoints and no unresolved service names.
4. The observability-off variant must omit optional Compose, chart, configuration, dashboard, and
   projection artifacts declared by the variant ledger.
5. Both variants must retain the same fixed application architecture, security, dependency authority,
   and business behavior.
6. All telemetry workloads must satisfy the runtime security floor, immutable-image policy, explicit
   writable volume ownership, probes, resources, and NetworkPolicy.
7. Loki and Tempo state must use image-owned writable mount points and non-root identities compatible
   with fresh local and Kubernetes volumes.
8. Grafana administrative credentials and every production secret must enter through external runtime
   secret boundaries.
9. Configuration checks must reject public exporters, remote assets, unresolved in-cluster endpoints, and
   sensitive-field logging.
10. Operations documentation must state local credentials, data lifecycle limitations, readiness,
    troubleshooting, teardown, and production non-goals.

## Security and authorization

- Telemetry endpoints remain internal and are not a substitute for authenticated production access.
- Dashboard and store access, multi-tenancy, retention, encryption, and audit controls require
  organization environment decisions before production use.
- Logs, labels, span attributes, and metrics must apply classification and cardinality controls.
- Application and telemetry workloads receive no unrestricted egress or cloud credentials.

## Data and migration

- Local observability volumes are disposable development state unless explicitly promoted by an
  environment plan.
- Production retention, deletion, backup, restore, legal hold, and tenant separation are outside the
  baseline and must be accepted before real data use.
- Enabling or disabling the scaffold variant changes managed infrastructure files but must not erase
  project-owned telemetry or data silently.
- Schema or dashboard format upgrades require versioned compatibility and rollback notes.

## Validation, observability, and evidence

- L1 generates both variants and compares their admitted file sets, dependency inventory, profile,
  charts, Compose config, security controls, and absence of public endpoints.
- L2 starts the on variant, sends real HTTP requests, correlates application log/trace/metric identity,
  queries or views the expected signal through internal endpoints, and verifies restart-safe non-root
  state mounts.
- The off variant passes the application full gate with no reference to absent telemetry services.
- Production claims require separate scale, loss, retention, access, alert, and failure-mode evidence.

## Risks and open questions

- What production retention, encryption, backup, tenant separation, and access policy applies?
- Are these stores production components or only a local verification baseline?
- Which team owns SLOs, alerts, dashboards, and on-call routing?
- What cardinality and volume limits protect the collector and stores?
- Which signals are mandatory when a business capability handles sensitive or regulated data?

## Acceptance criteria

- [ ] Application and platform owners accept the baseline signals and observability-on/off scope.
- [ ] Structured logs contain required correlation fields and exclude sensitive inputs.
- [ ] Migration and application logging coexist without duplicate or silently disabled handlers.
- [ ] Observability-on emits all admitted infrastructure with internal endpoints and hardened workloads.
- [ ] Observability-off omits every optional artifact and passes the full application gate.
- [ ] Both variants satisfy the same dependency and technology authority.
- [ ] Fresh local and Kubernetes writable volumes support non-root Loki and Tempo without root
  initialization.
- [ ] A live internal request produces correlated baseline signals across the selected pipeline.
- [ ] Public exporters, external assets, unresolved services, and secret-bearing configuration fail
  contract tests.
- [ ] Documentation does not imply production SLO, retention, access, or scale acceptance.

## Delivery flow

Draft -> application/platform/security review -> Accepted -> variant reconciliation -> static/runtime
tests -> live signal continuity evidence -> environment-specific production design
