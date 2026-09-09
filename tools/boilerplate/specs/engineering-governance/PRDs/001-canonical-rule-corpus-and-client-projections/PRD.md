# PRD — Canonical rule corpus and client projections

Status: Draft

Document version: 0.1.0

Domain: [Engineering Governance](../../DOMAIN.md)

Roadmap: [Capability 001](../../roadmap.md)

## Intent

Give application teams one schema-validated engineering-rule authority and deterministic,
replaceable projections for each supported repository discovery surface so the same behavior is not
maintained independently in multiple client-specific files.

This is a retrospective Draft. Existing corpus, renderer, generated-project checks, and evaluation
fixtures are observed baseline rather than owner acceptance.

## Actors and outcomes

- A governance owner changes one canonical rule and sees every affected projection deterministically.
- A developer receives relevant instructions, skills, and commands in an approved coding client without
  learning a second policy source.
- A reviewer can detect missing, hand-edited, stale, duplicated, or semantically inconsistent
  projections.
- An application team can express product requirements through accepted PRDs instead of weakening a
  centrally mandatory rule in a generated file.
- An Agent Platform adapter can reference stable rule identifiers without copying rule ownership into a
  custom-agent manifest.

## Verified baseline and gap

The repository contains one `rules/` corpus with schema-validated front matter and bodies. The current
renderer emits repository-level `AGENTS.md`, a Claude import/delta file, path-scoped Claude and Cursor
rules, bilingual Claude/Codex command skills, report skill, Codex project configuration, and a Spec Kit
constitution. Generated projects receive the corpus and projection checker, while source and output
digests are used for drift detection.

The baseline is instruction- and command-oriented. Portable custom-agent manifests, vendor capability
loss, runtime tuple conformance, and external admission are intentionally owned by the Agent Platform
domain. Remaining Engineering Governance gaps include formal owner acceptance, projection-version
compatibility, documented source precedence for every artifact kind, negative semantic drift cases, and
external enforcement expectations.

## Decisions, invariants, and trust boundaries

1. A rule is authored once in the canonical corpus; generated client files are never reverse-imported.
2. Stable rule identity, scope, trigger, applicability, client targets, priority, skill group, authority,
   and gate are machine validated.
3. The renderer maps canonical behavior into each documented native discovery surface rather than
   selecting one vendor format as a universal source.
4. Generated outputs are replaceable and carry a generated banner or equivalent provenance.
5. Drift checks provide detection and recovery. They do not make repository-local files immutable.
6. Effective prevention belongs to external identity, filesystem, network, CI, policy, and deployment
   controls.
7. Mandatory product exceptions require an accepted PRD or centrally reviewed rule change; client-local
   edits are not policy decisions.
8. Client discovery is not runtime adherence, conformance, production support, or certification.
9. Custom-agent compiler behavior remains outside this capability and must not be hidden in the
   instruction renderer.

## Functional requirements

1. Corpus loading must reject duplicate IDs, unknown properties, invalid scopes/triggers/authorities,
   unsafe globs, invalid applicability conditions, normalized duplicate bodies, and malformed Markdown
   front matter.
2. Rule ordering must be deterministic and based on explicit priority and stable identity.
3. Project initialization must copy only admitted source rules and must render only rules applicable to
   the resolved profile and answers.
4. Always-on rules must produce the cross-client contract and constitution surfaces without duplicating
   independent source prose.
5. Path-scoped rules must preserve their canonical path selectors in client-native scoped files.
6. On-demand rule groups and public project commands must produce equivalent bilingual Claude and Codex
   skills from one renderer path.
7. Client command names must use the fixed namespace and fail on reserved-name collision.
8. Generated Claude guidance must remain within its documented context-size contract and move scoped or
   on-demand content to native discovery surfaces.
9. `render --mode check` must report every missing, extra-managed, or content-different expected
   projection without writing.
10. `render --mode write` and scaffold recovery must recreate expected projections deterministically.
11. Source and projection inventories must record digests sufficient to identify drift and the
    generating corpus version.
12. Generated repositories must contain no global MCP credentials, private endpoint, model provider,
    environment topology, or client installation authority.
13. Documentation must distinguish source rules, generated instruction projections, generated command
    skills, and Agent Platform custom-agent projections.

## Security and authorization

- Rule paths and generated destinations must be contained within the selected repository and reject
  symlink escape.
- Projection content must be scanned for secrets, private endpoints, executable policy payloads, and
  prohibited environment-specific material.
- Generated guidance may describe approval requirements but cannot grant tool, identity, secret,
  network, or deployment access.
- A repository user able to edit source or generated policy remains a threat actor addressed by review,
  required checks, code ownership, and external enforcement.

## Data and migration

- Rule IDs are durable references. Rename or removal requires deprecation/alias semantics and update
  guidance.
- Projection paths and formats are versioned adapter decisions; clients may evolve independently.
- Generated lock/inventory data contains rule and output digests, not secrets or user behavior.
- A corpus change must regenerate projections in the same reviewed change and must preserve local
  project-owned artifacts.

## Validation, observability, and evidence

- L1 covers schema validation, duplicate/unsafe rule rejection, deterministic ordering, profile
  applicability, path mapping, bilingual skill parity, reserved-name checks, context-size limits,
  generated banners, tamper detection, and recovery.
- Mutation tests must prove that editing a source rule changes the expected projections and editing a
  projection causes drift failure.
- Client discovery checks may prove only that a file is loaded at a documented path. Runtime adherence
  belongs to Agent Platform conformance evidence.
- Evidence records corpus digest, renderer version, expected output digests, client/version documentation
  date, and test result.

## Risks and open questions

- Which generated output removals are managed automatically versus reported as manual cleanup?
- How long are deprecated rule IDs and client paths supported?
- Which external required checks and code-owner boundaries are necessary for production governance?
- How are client documentation changes detected and reviewed without turning research snapshots into
  support claims?
- Should generated projections include a signed manifest, or is digest-bound release admission the
  owning control?

## Acceptance criteria

- [ ] The governance owner approves the corpus schema, source precedence, and supported projection set.
- [ ] Every canonical rule validates, has a unique stable identity, and maps deterministically to its
  declared surfaces.
- [ ] Every expected projection is reproducible from source rules and carries generated provenance.
- [ ] Claude/Codex bilingual skill pairs are semantically equivalent and no command collides with a
  client-reserved name.
- [ ] Path-scoped rules preserve the canonical selector set in every target that supports scoping.
- [ ] Negative tests reject invalid rules, unsafe globs, secret/private endpoint content, duplicate
  bodies, and unsupported projection mappings.
- [ ] Hand-editing any managed projection fails the local and CI drift check and documented recovery
  recreates it.
- [ ] A rule change and renderer upgrade produce a bounded loss/drift report before rollout.
- [ ] Documentation states that discovery and repository-local drift checks are not runtime conformance
  or immutable enforcement.
- [ ] Agent Platform references the corpus by stable identities without becoming a second rule source.

## Delivery flow

Draft -> governance owner review -> Accepted -> renderer reconciliation plan -> corpus/projection
fixtures -> mutation and drift evidence -> generated-project rollout -> periodic client-format review
