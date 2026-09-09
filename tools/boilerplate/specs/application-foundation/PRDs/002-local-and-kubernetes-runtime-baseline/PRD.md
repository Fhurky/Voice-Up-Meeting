# PRD — Local and Kubernetes runtime baseline

Status: Draft

Document version: 0.1.0

Domain: [Application Foundation](../../DOMAIN.md)

Roadmap: [Capability 002](../../roadmap.md)

## Intent

Give every generated application a consistent, secure local runtime and a set of independently
renderable Kubernetes/Helm release shapes that expose environment facts without embedding secrets,
public dependencies, mutable image identities, or organization-specific promotion machinery.

This retrospective Draft records existing Compose, container, Helm, overlay, and contract-gate
templates. It does not claim admission to a real cluster.

## Actors and outcomes

- A developer can run the baseline through loopback-only local ingress with data services isolated from
  the edge network.
- A platform operator can render backend, frontend, migration, PostgreSQL, cache, worker, and optional
  observability releases from explicit environment facts.
- A security reviewer can verify non-root workloads, immutable images, secret boundaries, resource
  limits, probes, service-account restrictions, and NetworkPolicy.
- A release reviewer can distinguish project release artifacts from organization-owned promotion,
  registry, TLS, and deployment-controller responsibilities.

## Verified baseline and gap

The generated tree includes digest-oriented image inventory, local Compose files, loopback Nginx,
development and release Dockerfiles, Helm charts for application components, lab/cluster platform
overlays, migration job identity, render/check scripts, operations guidance, and CI chart rendering.
Templates apply non-root/read-only filesystem controls, bounded writable volumes, probes, resources,
ClusterIP services, part-of/component labels, and namespace-local network policies.

The current repository primarily provides static/render evidence. Real API-server admission, storage
class behavior, image pull, workload readiness, migration ordering, rollback, gateway/TLS integration,
and representative cluster acceptance remain environment-owned gates.

## Decisions, invariants, and trust boundaries

1. Local and Kubernetes targets are design constraints from the first scaffold release.
2. Runtime services have no public-network dependency and deny egress by default.
3. Images use approved internal repositories and immutable digests; tags alone are insufficient.
4. Source-authored charts do not create application secrets or embed secret values.
5. Runtime and build processes are non-root, drop capabilities, prohibit privilege escalation, and use
   read-only root filesystems except for explicit writable mounts.
6. Namespace-local peers match both component and product identity to prevent cross-application access.
7. Migration release identity is bound to immutable source identity and receives database authority only.
8. Environment overlays carry environment facts, not alternative architecture or duplicated sources of
   truth.
9. Promotion, registry admission, TLS, ingress identity, and cluster-wide policy remain organization
   platform responsibilities.

## Functional requirements

1. Local runtime must isolate database, cache, backend, and frontend on an internal application network;
   only the local edge and approved optional UI may bind loopback ports.
2. Development and release builds must use explicit build contexts, exclude workstation secrets/state,
   and support admitted offline dependency contexts.
3. Each Helm release must render independently from one canonical values source plus explicit
   environment facts.
4. Workloads must declare immutable image identity, resources, probes, pod/container security context,
   dropped capabilities, seccomp, read-only root filesystem, and disabled service-account token unless
   separately justified.
5. Every networked workload must have matching product/component labels and an explicit NetworkPolicy.
6. Services must be ClusterIP unless an accepted environment boundary defines a reviewed alternative.
7. Writable volumes must declare bounded purpose and ownership; Kubernetes volumes require matching
   `fsGroup` and change policy.
8. Migration jobs must use a migration-only image/configuration, immutable source revision, distinct job
   identity, direct Alembic command, and no JWT/application secret.
9. Render validation must reject unresolved placeholders, public registries, mutable tags, authored
   secrets, unsafe workload security, missing policies/probes/resources, unsupported API kinds/versions,
   external assets/telemetry, and unresolved service references.
10. Lab and cluster overlay key sets and release shapes must remain structurally aligned while values
    differ by environment fact.
11. Operations guidance must state install order, pre-created secret requirements, readiness checks,
    rollback, and accepted-risk recording.
12. Configuration consumed across application, Compose, and charts must be drift checked through the
    declared boundary.

## Security and authorization

- No chart may grant cluster-admin, broad RBAC, host mounts, privileged mode, host networking, or
  unrestricted egress as baseline behavior.
- Secret values stay in runtime secret systems and must not enter values files, examples, images, logs,
  or generated manifests.
- Public ingress requires the organization-approved TLS and identity gateway; local loopback bindings do
  not constitute production exposure.
- Release builds must exclude `.env`, package-manager credentials, keys, dependency trees, and local
  artifacts from their contexts.

## Data and migration

- PostgreSQL persistence and volume lifecycle must be explicit for local and cluster modes.
- Destructive data operations, backup/restore, high availability, disaster recovery, and production
  storage sizing require environment-specific accepted plans.
- Migration jobs run before application promotion according to the organization release controller; the
  scaffold defines the job contract, not the controller.
- Rollback must distinguish application image rollback from irreversible schema/data migration.

## Validation, observability, and evidence

- L1 covers Compose configuration, Dockerfile policies, chart lint/template, overlay schema, image
  identity, workload security, volume ownership, network policy, service reference, and forbidden
  external dependency mutation tests.
- L2 local evidence builds/loads admitted images, starts the stack, applies migration, runs readiness and
  full application/browser gates through loopback.
- L2 cluster evidence renders one immutable release, passes API-server/policy admission, pulls images,
  completes migration, reaches workload readiness, exercises HTTP behavior, and validates rollback.
- Contract rendering is not live cluster acceptance and must be reported separately.

## Risks and open questions

- Which Kubernetes versions, ingress/gateway API, storage classes, and policy engines are supported?
- What deployment controller owns sequencing, atomicity, rollback, and evidence receipts?
- Which components require production high availability, backup, autoscaling, or disruption budgets?
- How are image signatures, SBOMs, provenance, and registry admission enforced outside the repository?
- What is the approved exception process for egress or service-account access?

## Acceptance criteria

- [ ] Platform and security owners accept the local/cluster responsibility boundary.
- [ ] Local runtime exposes only approved loopback edge ports and keeps data/application services on the
  internal network.
- [ ] Release build contexts contain no workstation secrets or dependency fallback.
- [ ] Every chart passes immutable-image, non-root, read-only, resources, probes, service-account,
  volume, label, and NetworkPolicy contract tests.
- [ ] Mutation tests prove every required security-floor element and service reference is enforced.
- [ ] Migration jobs use source-bound immutable identity and receive database-only authority.
- [ ] Lab and cluster overlays have aligned structure and contain no secrets.
- [ ] A fresh offline local stack reaches readiness and passes the full browser gate.
- [ ] One representative cluster deployment passes live admission, migration, readiness, behavior, and
  rollback checks for the same image digests.
- [ ] Documentation names all organization-owned promotion, identity, TLS, registry, and recovery gaps.

## Delivery flow

Draft -> platform/security review -> Accepted -> template reconciliation -> static/render gates -> offline
local runtime evidence -> representative cluster evidence -> environment owner acceptance
