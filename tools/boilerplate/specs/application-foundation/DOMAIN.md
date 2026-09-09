# Application Foundation domain

Status: Draft

## Purpose

Application Foundation owns the secure, runnable application and operations baseline emitted into a
new repository before business capabilities are implemented.

## Actors

- Application developer — starts from a working full-stack foundation rather than inventing platform
  plumbing.
- Application administrator — bootstraps the first application-level super administrator securely.
- Platform operator — deploys the generated release shapes into admitted local and Kubernetes targets.
- Security reviewer — verifies tenant isolation, non-root runtime, secret boundaries, and network policy.
- Service operator — observes health and baseline application signals without external telemetry.

## Ubiquitous language

- **Application super administrator** — application-wide RBAC bypass, never OS, database, or cluster root.
- **Active tenant context** — request-scoped tenant identity validated against the principal and tenant
  lifecycle.
- **Platform baseline** — health, authentication, persistence, UI shell, and operations behavior present
  before the first business vertical.
- **Release shape** — one independently renderable Helm workload such as backend, frontend, migration,
  database, cache, worker, or observability.
- **Observability variant** — admitted scaffold answer that includes or omits the optional telemetry stack.

## Invariants

1. The baseline contains no invented sample business entity or business endpoint.
2. JWT, RBAC, tenant isolation, and application super-admin behavior agree across persistence, backend,
   frontend, and browser acceptance.
3. Runtime workloads and application database connections remain non-root and least-privileged.
4. Secrets enter through runtime environment or pre-created platform secret boundaries and are not
   generated into source.
5. Local and cluster releases deny runtime egress by default and use immutable internal image identity.
6. Optional observability changes infrastructure presence, not domain behavior or instrumentation claims.

## Owned data and artifacts

- Generated FastAPI, React/Vite, PostgreSQL/Alembic, and authentication baseline behavior.
- Local Compose and Kubernetes/Helm release contracts and configuration synchronization.
- Baseline structured logging, health, metrics, traces, logs, and dashboard infrastructure.

## Upstream boundaries

- Technology Governance mandatory profile and exceptions.
- Delivery Assurance admitted dependencies, images, browser, and scanner artifacts.
- Organization-owned ingress, TLS, identity, storage class, registry, and promotion facts.

## Downstream boundaries

- Capability Delivery business verticals.
- Delivery Assurance full-stack and browser evidence.
- Application-team operations, risk acceptance, and environment overlays.

## Explicit non-responsibilities

- Defining business-domain models, workflows, metrics, or traces.
- Owning organization promotion controllers, cluster administration, TLS issuance, or secret creation.
- Providing a general-purpose queue, cache adapter, or websocket capability without an accepted PRD.
