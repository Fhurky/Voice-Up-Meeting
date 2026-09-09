# PRD — Safe managed scaffold update

Status: Draft

Document version: 0.1.0

Domain: [Project Factory](../../DOMAIN.md)

Roadmap: [Capability 002](../../roadmap.md)

## Intent

Allow an application team to advance the centrally managed scaffold baseline to an admitted
`kt-scaffold` release while preserving every project-owned edit, failing atomically on conflicts, and
making removals and incompatible version transitions explicit.

This retrospective Draft records an existing local update mechanism; it does not accept the current
implementation or authorize destructive migration.

## Actors and outcomes

- An application maintainer can preview and apply an admitted baseline update without reconstructing
  the project.
- A developer keeps local modifications intact and receives a bounded diff preview for each conflict.
- A release maintainer can evolve generated files while preserving version compatibility rules.
- A reviewer can distinguish local managed-file replay from central governance reconciliation.

## Verified baseline and gap

The current implementation reloads recorded answers, advances only to the installed tool-owned
version, renders a complete prospective tree beside the project, compares current files with the
recorded managed digests, and prepares one transaction. Any edited or unexpected managed path becomes
a conflict. Removed corpus paths become manual steps and are not deleted automatically.

Current gaps include a formally accepted compatibility policy across release families, durable
release-note linkage, evidence for a real N-to-N+1 generated project, and an explicit product decision
for files that move, split, or change authority class.

## Invariants and boundaries

1. Update runs locally against an explicit scaffolded project root.
2. Recorded generator version and managed-file digests are inputs; ambient chat history is not.
3. A caller cannot override generator version.
4. An older installed generator refuses a project recorded by a newer release.
5. Any conflict prevents all generated writes, answer changes, and manifest changes.
6. Project-owned or locally edited content is never overwritten silently.
7. Paths no longer emitted are reported for manual review and never auto-deleted.
8. Update does not run migrations, project code, VCS commands, or quality gates implicitly.
9. Central governance reconciliation remains a separate Engineering Governance capability.

## Functional requirements

1. The operation must verify scaffold markers, answer schema, managed-manifest schema, root containment,
   and regular-file/symlink safety before rendering.
2. It must render the complete prospective tree in an isolated sibling stage using the installed
   profile and corpus.
3. A missing previously unmanaged destination may be created only when the new release declares it as
   managed.
4. An existing path absent from the prior managed manifest must conflict rather than be adopted.
5. A managed path whose current digest differs from the recorded digest must conflict and remain
   untouched.
6. Unchanged paths must be reported without rewrite; clean changed paths may update transactionally.
7. Answer overrides must pass the current strict answer schema and must not change fixed backend,
   persistence, or generator authority.
8. The result must list creates, updates, unchanged paths, conflicts, warnings, and manual removal
   steps without exposing secrets.
9. A retry after conflict resolution must be deterministic and idempotent.
10. Release notes or an equivalent versioned record must identify managed behavior changes, required
    local decisions, and validation expectations.

## Security and authorization

- Update requires explicit local invocation by an actor authorized to modify the repository.
- Root, home, broad paths, traversal, and symlink escapes must be rejected before comparison or write.
- Conflict previews must be bounded and must not be sent automatically to remote MCP.
- Update must never inherit arbitrary project execution authority merely because the target is a
  scaffolded repository.

## Data and migration

- Successful update advances recorded answers, tool version, and managed digests in one transaction.
- Failed or conflicting update leaves the complete project and all manifests unchanged.
- Managed path removal, rename, or ownership transfer requires explicit migration semantics; implicit
  deletion is forbidden.
- Schema/data migrations are project capability work and remain outside this operation.

## Validation and evidence

- L1 covers clean replay, no-op replay, edited managed file, unexpected existing path, new file,
  changed file, removed file, invalid version direction, invalid overrides, symlink path, and injected
  mid-write failure.
- L2 covers a real project generated at release N, updated with an admitted N+1 package, followed by the
  complete generated-project gate and browser acceptance.
- Evidence records from/to generator versions, changed paths, conflicts, manual steps, and post-update
  gate provenance.

## Risks and open questions

- What compatibility window is guaranteed across minor and major releases?
- How are path renames and ownership-class changes represented without unsafe delete-and-create logic?
- Which answer changes are supported after bootstrap, and which require a new architecture decision?
- Where is the approved release-note and migration advisory stored and signed?

## Acceptance criteria

- [ ] The owner approves the supported version window and answer-mutation policy.
- [ ] No-op update writes no file and returns a stable result.
- [ ] A clean managed change updates answers and manifests atomically.
- [ ] Any edited or unexpected destination produces a bounded conflict and zero writes.
- [ ] Removed managed paths are listed as manual work and remain present.
- [ ] An older tool refuses to update a newer project, and callers cannot impersonate a version.
- [ ] Injected failure restores every affected byte and manifest.
- [ ] A real N-to-N+1 update passes the full project gate without weakening project-owned behavior.
- [ ] Documentation distinguishes scaffold update from governance reconciliation and business migration.

## Delivery flow

Draft -> owner review -> Accepted -> compatibility matrix -> implementation reconciliation -> N/N+1
fixtures -> atomicity and conflict evidence -> staged release
