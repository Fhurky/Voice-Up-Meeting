# PRD — Authority-aware governance reconciliation

Status: Draft

Document version: 0.1.0

Domain: [Engineering Governance](../../DOMAIN.md)

Roadmap: [Capability 002](../../roadmap.md)

## Intent

Allow a scaffolded project to discover centrally changed governance artifacts using bounded metadata,
retrieve only selected canonical bodies, record authority-aware local decisions, and validate an
integrity-bound reconciliation receipt without sending source or granting remote workspace authority.

This retrospective Draft documents an implemented intent-level flow. It does not claim remote
application proof or production control-plane admission.

## Actors and outcomes

- A governance owner can publish versioned mandatory or recommended behavior with stable identity.
- An application team can see only relevant additions and changes and adapt them to accepted local
  product needs.
- A local coding agent can help compare and apply artifacts while remaining bounded by local approval
  and filesystem authority.
- A reviewer can verify that mandatory behaviors were preserved and that every decision has rationale.
- A security reviewer can prove that central operations receive metadata rather than workspace content.

## Verified baseline and gap

The current MCP catalog exposes metadata without bodies, retrieves only explicitly selected artifact
bodies, compares a bounded `ProjectMetadata` inventory with canonical rules/skills/guidance, and emits a
deterministic update proposal. Artifact authority is modeled as mandatory, recommended, or
project-owned. Reconciliation validates proposal integrity, decision completeness, and preservation of
mandatory behaviors, then emits a `local-agent-attested` receipt with an explicit warning that it is not
workspace verification.

The current implementation is repository-local design and test evidence. It lacks a signed central
publication model, authenticated production caller identity, durable audit store, fleet rollout and
revocation policy, time-bound exceptions, and independent application attestation.

## Decisions, invariants, and trust boundaries

1. The central service publishes canonical desired intent and never requests a repository snapshot.
2. Project metadata is bounded, secret-free, and exported from one known manifest rather than by walking
   the workspace.
3. Catalog listing excludes bodies; retrieval is explicit by artifact identity.
4. Mandatory behavior may be accepted or adapted only when all required behaviors remain explicit.
5. Recommended behavior may be accepted, adapted, deferred, or rejected with rationale.
6. Project-owned artifacts are preserved and never replaced by central content.
7. Unknown non-project-owned artifact identities fail closed.
8. Proposal identity binds the complete deterministic proposal content.
9. A reconciliation receipt attests decision structure. It does not prove local bytes, tests, runtime
   behavior, or owner acceptance.
10. Local filesystem mutation, execution, and evidence remain under the application team's authority.

## Functional requirements

1. The canonical catalog must expose stable artifact ID, kind, authority, version, scope, digest, title,
   and required-behavior metadata without returning the body.
2. Artifact retrieval must require an explicit bounded list, reject duplicates/unknown IDs, and return
   content whose digest matches catalog metadata.
3. Project metadata must contain only blueprint/governance identity, resolved non-secret profile facts,
   locales, and canonical artifact inventory.
4. Update comparison must be deterministic and classify missing or changed mandatory artifacts as
   alignment work and changed recommended artifacts as review work.
5. Local project-owned inventory entries must be preserved; unknown central-authority entries must fail.
6. Proposals must identify from/to versions, target inventory digest, unchanged count, artifact actions,
   required behaviors, and local instructions.
7. Each proposed artifact must receive exactly one decision with rationale; adapted mandatory artifacts
   must enumerate preserved required behaviors.
8. Proposal alteration, duplicate decisions, unknown decisions, missing decisions, and weakened mandatory
   behavior must fail receipt validation.
9. The resulting receipt must identify unresolved items and label provenance as local-agent-attested.
10. English and Turkish MCP names must share strict schemas and equivalent results over stdio and HTTP.
11. No operation may accept target paths, workspace bodies, patches, commands, execution flags, VCS data,
    environment variables, secrets, or database content.
12. Application guidance must require local comparison, approval, gates, and persistence of the decision
    record after successful application.

## Security and authorization

- Production publication requires an external authenticated and authorized governance owner; repository
  possession alone cannot publish mandatory policy.
- Canonical bundles or manifests require content identity and, for a production control plane, an
  organization-approved signature and revocation model.
- MCP transport relies on external OAuth/TLS and scopes; no token or private endpoint belongs in project
  metadata.
- Artifact bodies and metadata must be size bounded, secret scanned, and path/format safe before local
  application.
- The local applicator/agent must confine writes, protect symlinks, preserve project-owned paths, apply
  atomically where practical, and run independent drift/quality checks.

## Data and migration

- Artifact IDs and authority classes are durable. Authority downgrade/upgrade requires reviewed migration
  semantics and must not be inferred from absence.
- Project metadata and receipts exclude source, prompts, credentials, personal data, and environment
  topology.
- Receipt retention, immutability, access, and deletion policy belong to the production audit design and
  remain unresolved in this Draft.
- Old proposals must be rejected or revalidated after catalog version, artifact digest, or exception
  expiry changes.

## Validation, observability, and evidence

- L1 covers deterministic inventory/proposal identity, changed/unchanged cases, all authority classes,
  explicit retrieval, duplicate/unknown/tampered input, required-behavior preservation, alias parity, and
  strict transport schemas.
- L2 covers a real stdio/HTTP update check, local semantic application to a generated repository,
  regenerated projections, full local gate, and a receipt tied to the observed resulting inventory.
- Production evidence separately covers signer identity, gateway authorization, audit persistence,
  revocation, exception expiry, staged rollout, and rollback.
- Telemetry must record operation identity, authenticated actor, catalog version, proposal/receipt digest,
  status, and latency without artifact bodies or project content.

## Risks and open questions

- Which trusted component signs canonical desired state and verifies local application receipts?
- Where are immutable receipts, exceptions, approvals, and revocations retained?
- How does a fleet discover urgent revocation without sending excessive project metadata?
- What is the maker-checker boundary for mandatory rule publication?
- Can local semantic adaptation be attested strongly enough for higher-risk projects without source
  disclosure?

## Acceptance criteria

- [ ] The governance owner approves artifact authority, publication, exception, and revocation semantics.
- [ ] Catalog, retrieval, proposal, decision, and receipt schemas reject unknown and oversized input.
- [ ] Only bounded project metadata crosses the MCP boundary; source/workspace/secret negative tests pass.
- [ ] Proposals are deterministic and bind all artifact actions and target inventory identity.
- [ ] Mandatory weakening, missing decisions, duplicate/unknown decisions, and proposal tampering fail
  closed.
- [ ] Recommended and project-owned decisions follow their distinct authority rules.
- [ ] Stdio and HTTP English/Turkish pairs expose equivalent schemas and results.
- [ ] A real generated project completes local application, drift checks, full gate, and receipt recording
  without central workspace access.
- [ ] Documentation and API responses state that the receipt is decision attestation, not remote execution
  or conformance proof.
- [ ] Production promotion includes external identity, signing, durable audit, staged rollout, rollback,
  and revocation evidence.

## Delivery flow

Draft -> governance/security review -> Accepted -> signed publication and applicator plan -> schema and
negative tests -> real local reconciliation -> staged fleet rollout -> periodic audit and revocation test
