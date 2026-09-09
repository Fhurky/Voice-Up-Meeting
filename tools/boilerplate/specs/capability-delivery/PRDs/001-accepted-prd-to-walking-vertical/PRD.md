# PRD — Accepted PRD to walking vertical

Status: Draft

Document version: 0.1.0

Domain: [Capability Delivery](../../DOMAIN.md)

Roadmap: [Capability 001](../../roadmap.md)

## Intent

Provide a traceable delivery workflow that starts from one human-accepted domain capability PRD and
creates the smallest real-data vertical across desired state, tenant-safe backend, protected typed API,
localized frontend behavior, and executable browser acceptance.

This retrospective Draft describes generator behavior that already exists in part. It does not accept
any business capability or authorize generated placeholders to be treated as complete implementation.

## Actors and outcomes

- A product owner can trace every delivered behavior to one accepted actor outcome and acceptance
  criterion.
- A domain developer receives a structurally valid starting vertical rather than generic CRUD detached
  from domain language.
- A reviewer sees the same `spec_path` in persistence, backend, frontend, and browser artifacts.
- An evidence reviewer can tell whether files were generated, implemented, executed, and accepted.

## Verified baseline and gap

The current CLI creates Draft PRD/plan/task shells under an existing domain and adds a roadmap row.
Business generators reject missing or non-Accepted PRDs. The backend generator creates a domain model,
tenant-aware active-record repository query, application service, response schema, protected endpoint,
and registry updates. The frontend generator creates a typed service and a protected route with
loading, error, empty, and list states. Schema preparation records the accepted spec and returns the
profile-native Alembic command instead of forging a migration. Browser scenario generation records
acceptance points and deliberately throws until executable assertions are implemented.

The gap is that the current generator shapes and tests predate an accepted product-level PRD for this
workflow. The exact plan/tasks derivation contract, multi-capability interaction, update/rollback
semantics, permission seeding, and real L2 evidence require owner review.

## Decisions, invariants, and boundaries

1. A resource or route name is never implementation authority.
2. Every business generator requires a repository-contained
   `specs/<domain>/PRDs/<nnn>-<capability>/PRD.md` with `Status: Accepted`.
3. The accepted PRD remains the requirements authority; generated plan/tasks and code may not add or
   weaken requirements silently.
4. One vertical uses one stable spec path across all layers.
5. Desired SQLAlchemy models are persistence authority; migrations are generated and reviewed from
   that authority.
6. Tenant scoping, active-tenant lifecycle, soft delete, public identifiers, and permission checks are
   data-path behavior rather than documentation-only rules.
7. UI completion includes loading, error, empty, success, authorization, and localization behavior.
8. A generated browser scenario is intentionally L0 until its failing guard is replaced and executed.

## Functional requirements

1. PRD creation must require an existing domain context, safe capability slug, non-empty intent, and
   independently numbered roadmap entry.
2. New PRDs begin as Draft; no command may self-accept them.
3. Plan and task derivation must trace every task to a PRD acceptance criterion, affected layer, and
   verification gate.
4. Backend generation must create a real persistence model, repository boundary, application service,
   response contract, protected endpoint, and deterministic registry changes.
5. Tenant-scoped generation must require active, non-deleted tenant and record predicates in the
   repository query.
6. Permission identifiers must use one validated `resource:action` form and be traced to seed or
   administration work.
7. Schema preparation must record the accepted PRD, desired-state authority, change summary, and
   reviewed generator command; it must not emit an empty or prose-derived migration.
8. Frontend generation must use the shared typed API client, protected routing, and explicit UI states.
9. Generated strings and labels must use the configured localization catalog rather than hard-coded
   client text.
10. Browser generation must add the scenario runner and quality-manifest row, preserve acceptance
    points, and fail until executable assertions exist.
11. Repeated generation with identical inputs must be idempotent; collisions or incompatible registry
    state must fail without partial writes.
12. Multiple accepted capabilities must coexist without import, route, migration, permission, or
    manifest-order drift.

## Security and authorization

- `spec_path` and every output path must be repository-contained and symlink-safe.
- Endpoint and route generation must default to least-privilege read permission, never public access.
- Application super-admin remains a testing/bootstrap identity; restricted-role scenarios are required
  when the capability acceptance criteria include authorization behavior.
- Generated input values must be escaped per Python, TypeScript, JSON, YAML, route, and identifier
  context.

## Data and migration

- Domain models use required audit, soft-delete, public-identifier, and tenant fields where applicable.
- References remain inside the owning application database and use reviewed integrity behavior.
- Migration names and change records are deterministic metadata, not executable schema authority.
- Backfill, rollback, destructive changes, and data retention must be defined by the business PRD and
  reviewed migration plan.

## Validation, observability, and evidence

- L1 requires model/repository/service/API unit and PostgreSQL integration behavior, migration/drift
  validation, frontend tests, type/contract alignment, permission behavior, and generator idempotency.
- L2 requires a running stack and real browser assertions through the UI, including important loading,
  error, empty, success, and authorization paths.
- Capability-specific metrics and traces belong to the business PRD; the generator may not invent them.
- Evidence records the accepted spec path and observed tests, not merely generated-file existence.

## Risks and open questions

- Should plan/tasks generation remain a scaffold shell or become a stricter acceptance-criterion
  compiler?
- How are permission seed changes represented and reviewed across multiple verticals?
- What deterministic behavior is required when two capabilities touch the same aggregate or route?
- Which schema changes are too complex for generator assistance and must remain fully project-owned?
- How should a capability rollback retain evidence and migration lineage?

## Acceptance criteria

- [ ] Draft or missing PRDs fail every business generator without writing files.
- [ ] An accepted PRD produces one traceable backend, schema-intent, frontend, and browser starting
  vertical with the same spec path.
- [ ] The generated repository query enforces tenant lifecycle and soft-delete behavior with real
  PostgreSQL integration evidence.
- [ ] The protected API and frontend route enforce the declared permission and typed contract.
- [ ] The frontend has localized loading, error, empty, and success states.
- [ ] Schema preparation emits no fake migration and the reviewed Alembic path passes drift validation.
- [ ] Browser generation cannot pass before executable acceptance assertions are implemented.
- [ ] Two long-named accepted capabilities coexist and pass deterministic formatting, imports, routes,
  type checking, and full project gates.
- [ ] L2 evidence exercises the real HTTP/UI/data path; API-only or prose-only checks are reported
  separately.
- [ ] The product owner accepts representative behavior before any L3 claim.

## Delivery flow

Draft -> domain review -> Accepted -> criterion-linked plan -> ordered tasks -> generated starting
vertical -> project implementation -> L1 -> L2 -> product-owner L3
