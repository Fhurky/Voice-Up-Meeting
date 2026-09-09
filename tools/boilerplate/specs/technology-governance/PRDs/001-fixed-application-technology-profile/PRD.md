# PRD — Fixed application technology profile

Status: Draft

Document version: 0.1.0

Domain: [Technology Governance](../../DOMAIN.md)

Roadmap: [Capability 001](../../roadmap.md)

## Intent

Provide one strict, machine-readable application technology authority so every generated repository
uses the same reviewed architecture and compatibility baseline, while allowing only narrow,
PRD-declared exceptions instead of framework choice by a caller or coding agent.

This retrospective Draft records a profile currently labeled `approved-baseline` in code. That label is
an observed configuration value, not evidence that this PRD has received accountable owner acceptance.

## Actors and outcomes

- An architecture owner can approve and version one baseline rather than adjudicating framework choice
  in every project.
- An application team receives predictable commands, directory structure, tests, deployment, and
  maintenance behavior.
- A Project Factory caller supplies product intent without selecting backend or persistence technology.
- A security/release reviewer can trace package and image changes to the profile and admission evidence.
- A reviewer can detect drift between root authority, generated profile, templates, manifests, and tests.

## Verified baseline and gap

The current schema-version-2 profile fixes separated React/Vite SPA plus Python/FastAPI and async
SQLAlchemy/asyncpg/Alembic on PostgreSQL. It forbids SSR, Next.js, Node/NestJS/Prisma backend choices,
mixed backends, and agent-selected backend frameworks. SSE is allowed, websocket is exception-only,
and a Streamlit full-stack mode is conditionally allowed only for prompt/chat/history-only applications.
The profile also declares security, observability, delivery, dependency maintenance, and optional
vector/embedding boundaries. Strict Pydantic models validate required values and the ordered forbidden
set; the generated project receives a synchronized profile.

The gap is a human-approved lifecycle for profile changes and exceptions, explicit schema migration and
compatibility rules, authoritative owner identities, and evidence that each declared current version is
available and admitted in every supported offline platform matrix.

## Decisions, invariants, and trust boundaries

1. The default mode is a separated React/Vite client-side SPA and Python/FastAPI HTTP API.
2. PostgreSQL with async SQLAlchemy, asyncpg, and Alembic is the only baseline persistence authority.
3. SSR, Next.js, Node backend, NestJS, Prisma, mixed Python/Node backend, and agent-selected backend are
   forbidden.
4. SSE is allowed; websocket requires an accepted capability exception.
5. Streamlit is the only full-stack UI exception and is eligible only when the complete interface is
   prompt input, chat response, and history with no general-purpose business UI.
6. The technology profile constrains implementation; it does not replace a business capability PRD.
7. Declared optional technologies are not active or admitted until their activation contract is met.
8. The caller cannot override fixed profile identity, authority, backend, persistence, or forbidden set.
9. Version pins are governed floors and must pass dependency/artifact admission before release.
10. Root profile, generated profile, schemas, templates, docs, and executable tests change together.

## Functional requirements

1. The profile must have a versioned strict schema and reject unknown properties at every modeled
   object boundary.
2. It must declare application modes, architecture, frontend, backend, persistence, embeddings,
   security, observability, delivery, maintenance, and forbidden technologies.
3. Project Factory input and MCP schemas must not expose backend, ORM, driver, migration tool,
   persistence engine, SSR framework, or vector database selectors.
4. The renderer must validate the source profile before emitting a project and must copy the resolved
   machine-readable profile into the managed tree.
5. Generated code, dependency manifests, commands, container builds, charts, CI, and docs must match the
   resolved profile.
6. Streamlit selection must require an accepted PRD that proves every eligibility condition and records
   the application-mode decision.
7. Websocket, cache adapter, queue/broker, general-purpose full-stack UI, or alternative database use must
   fail unless a separately reviewed profile version defines an exception.
8. Maintenance policy must define release-age floor, urgent security exception, required evidence, and
   the rule that adoption-window policy cannot force a downgrade.
9. Every direct package, workflow action, OCI image, browser, and scanner authority implied by the profile
   must be covered by Delivery Assurance admission.
10. Profile version changes must publish compatibility impact, generated-tree changes, managed update
    behavior, and rollback/migration requirements.
11. Drift checks must reject mismatch among profile identity, answer/manifest facts, templates, schema
    authority, and generated commands.

## Security and authorization

- Only accountable architecture governance may approve a new profile version or exception class.
- A PRD may request an eligible exception but cannot change the machine-readable profile directly.
- Forbidden alternatives must be enforced through schema, renderer, dependency admission, and generated
  gates rather than documentation alone.
- Profile content contains no private registry endpoint, credential, certificate, cluster fact, or
  environment-specific topology.

## Data and migration

- Profile schema versions are explicit. A reader must reject unsupported future versions rather than
  ignore fields.
- Generated projects record profile identity and generator version for compatibility checks.
- Changing persistence authority, application mode, or forbidden technology is an architecture
  migration, not a normal answer override.
- Version and dependency updates require reviewed locks, inventory digest, compatibility tests, and
  generated-project evidence.

## Validation, observability, and evidence

- L1 validates exact required values, forbidden order, unknown-field rejection, root/generated parity,
  input-selector absence, template/manifests alignment, dependency inventory, and negative forbidden
  technology scans.
- Variant tests generate separated-web, eligible Streamlit, ineligible Streamlit, observability-on/off,
  and optional-capability fixtures without changing fixed backend/persistence authority.
- L2 runs a fresh separated-web scaffold through bootstrap, migration, full gate, browser acceptance,
  and deployment rendering using one admitted artifact set.
- Streamlit or other exception admission requires its own live evidence and owner acceptance.

## Risks and open questions

- Who is the accountable profile owner and what maker-checker process changes the baseline?
- What compatibility window is promised for generated projects during a profile schema upgrade?
- Which Streamlit release/runtime pattern is admitted, and what security/browser evidence is required?
- How are unavoidable version conflicts handled without silently weakening the profile?
- Which additional exception categories, if any, are intentionally supported?

## Acceptance criteria

- [ ] Architecture, security, application-platform, and release owners accept the fixed baseline and
  exception policy.
- [ ] Strict source and generated profiles validate identically and reject unknown or reordered fixed
  values.
- [ ] Public CLI/MCP inputs expose no fixed-stack selector or caller-controlled profile identity.
- [ ] Generated dependencies, source structure, scripts, CI, containers, and charts match the profile.
- [ ] Negative tests reject every forbidden technology and ineligible exception.
- [ ] Streamlit can be selected only by an accepted PRD satisfying all eligibility conditions.
- [ ] Every implied direct dependency and executable artifact is present in the admitted inventory.
- [ ] A fresh separated-web project passes the complete offline application and browser gates.
- [ ] Profile change documentation states compatibility, migration, managed update, and rollback impact.
- [ ] Evidence distinguishes configured baseline, generated implementation, live behavior, and owner
  acceptance.

## Delivery flow

Draft -> architecture/security review -> Accepted -> profile/schema reconciliation -> dependency
admission -> generator/template updates -> variant and full-stack evidence -> managed release
