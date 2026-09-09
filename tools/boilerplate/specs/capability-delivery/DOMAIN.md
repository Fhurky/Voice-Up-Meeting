# Capability Delivery domain

Status: Draft

## Purpose

Capability Delivery owns traceability from one accepted domain capability PRD to a reviewable,
tenant-safe walking vertical across desired state, backend, authorization, typed API/UI, localization,
and browser acceptance evidence.

## Actors

- Product owner — accepts actor outcomes, boundaries, and measurable behavior.
- Domain developer — implements the smallest end-to-end capability without bypassing domain rules.
- Reviewer — traces generated and handwritten behavior back to one accepted PRD.
- Evidence reviewer — distinguishes generated placeholders from executed acceptance behavior.

## Ubiquitous language

- **Capability PRD** — one independently deliverable actor outcome within a bounded context.
- **Spec path** — the repository-relative `PRD.md` identity supplied to every capability generator.
- **Walking vertical** — real data movement from persistence through protected API to observable UI.
- **Desired state** — domain model authority from which reviewed migrations are generated.
- **Failing-first scenario** — generated browser acceptance shell that cannot pass until executable
  assertions replace its guard.

## Invariants

1. Business generation requires a repository-contained PRD whose status is `Accepted`.
2. The same spec path traces schema, backend, frontend, and browser artifacts.
3. A walking vertical moves real tenant-scoped data; a constant response is not complete.
4. Migration prose records intent but never fabricates an empty or handwritten migration.
5. Authorization, loading, error, empty, and success behavior are explicit parts of the vertical.
6. Generated acceptance prose is not executable evidence.

## Owned data and artifacts

- Domain capability PRD identity and delivery trace links.
- Capability generator contracts for desired state, backend, frontend, and browser scenario shells.
- Capability-level authorization and acceptance-manifest integration.

## Upstream boundaries

- Domain owner acceptance and domain-specific invariants.
- Application Foundation layer and security contracts.
- Technology Governance profile and persistence authority.

## Downstream boundaries

- Project-owned implementation, migration review, tests, and browser assertions.
- Delivery Assurance evidence collection and completion reporting.

## Explicit non-responsibilities

- Accepting PRDs automatically or deriving requirements from a resource name.
- Owning generic application bootstrap, deployment promotion, or supply-chain admission.
- Claiming completion merely because generator output exists.
