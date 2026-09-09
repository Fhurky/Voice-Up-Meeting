# Project Factory domain

Status: Draft

## Purpose

The Project Factory owns the lifecycle that turns validated project intent into a deterministic,
content-addressed repository and later advances centrally managed scaffold content without erasing
project-owned work.

## Actors

- Product initiator — supplies the project purpose and primary business domain.
- Application team — selects the local target and owns the generated repository after creation.
- Platform operator — distributes an admitted `kt-scaffold` build and its MCP deployment.
- Release maintainer — publishes compatible generator releases and managed-file changes.
- Security reviewer — reviews target containment, artifact integrity, rollback, and remote/local trust
  boundaries.

## Ubiquitous language

- **Validated answers** — normalized, secret-free project inputs plus tool-owned generator version.
- **Rendered tree** — the complete canonical project output for one answers/version tuple.
- **Bundle descriptor** — the content-addressed archive and per-entry create-only PatchSet contract.
- **Applicator** — the local mechanical verifier and transactional publisher of a prepared bundle.
- **Managed file** — a generated path whose last accepted digest is recorded by the local manifest.
- **Project-owned edit** — local content that the Project Factory must preserve and report as a
  conflict rather than overwrite.

## Invariants

1. Identical validated answers and generator version produce the same managed bytes and tree digest.
2. The remote service never receives a workstation target path, source tree, secret, database data,
   or caller-authored patch.
3. Local publication is create-only for initial bootstrap and transactional for both creation and
   managed update.
4. A conflict anywhere in an update prevents all generated writes, answer changes, and manifest
   changes.
5. Managed paths removed by a later corpus become explicit manual steps and are never auto-deleted.
6. Generator version is tool-owned; an older installation cannot rewrite output from a newer one.

## Owned data and artifacts

- Validated scaffold answers and initial bounded project metadata.
- Managed-file manifest, bundle descriptor, archive identity, and application receipt schemas.
- Deterministic rendering, staging, target-containment, update, conflict, and rollback semantics.
- Bootstrap parity across installed CLI, stdio MCP, and Streamable HTTP MCP delivery.

## Upstream boundaries

- Accepted technology profile and application-foundation release set.
- Canonical engineering-governance corpus and client projection renderer.
- Offline dependency and artifact admission from Delivery Assurance.
- Organization-owned identity, TLS, registry, and workstation policies.

## Downstream boundaries

- A newly scaffolded repository with an empty primary-domain roadmap.
- Capability Delivery generators acting only from accepted PRDs.
- Local quality gates and project-owned implementation work.

## Explicit non-responsibilities

- Inventing business requirements or accepting a domain PRD.
- Mutating an existing repository remotely through MCP.
- Running version-control commands, project tests, migrations, or browser scenarios during bootstrap.
- Owning enterprise OAuth, TLS termination, registries, or deployment promotion.
