# PRD — Deterministic project bootstrap

Status: Accepted

Document version: 1.0.0

Acceptance date: 2026-08-18

Acceptance record: Explicit owner authorization to complete the trusted-local MCP refactor and run
the end-to-end workflow in the project delivery thread.

Domain: [Project Factory](../../DOMAIN.md)

Roadmap: [Capability 001](../../roadmap.md)

## Intent

Enable an application team to turn validated product intent into the complete canonical
`kt-scaffold` project tree from an empty workspace without asking a model to synthesize hundreds of
files or download and execute runtime code.

The supported interactive bootstrap is a preinstalled, trusted local stdio MCP process whose
workspace root is fixed by client registration. The internal Streamable HTTP MCP remains a
workspace-blind governance plane. The ordinary CLI remains a first-class unattended alternative.

## Actors and outcomes

- A product initiator supplies purpose, domain and product identity without choosing the fixed stack.
- A developer opens an explicit empty workspace and receives one complete deterministic repository.
- A platform operator installs one approved package usable through CLI or local stdio MCP.
- A governance operator may expose the HTTP knowledge plane without granting it workstation access.
- An evidence reviewer can compare observed tree digests across CLI and local stdio creation.

## Decisions, invariants, and trust boundaries

Decision 1: `project_init` is the single canonical renderer and transactional publisher for CLI and
local stdio MCP creation.

Decision 2: The local stdio MCP receives its workspace root only at process startup. The model-facing
tool schema never accepts a target path, overwrite flag, arbitrary command, URL, archive, or secret.

Decision 3: The local MCP must execute no downloaded Python, shell, package manager, migration,
generated project code, or VCS command. It invokes the installed generator in-process.

Decision 4: Streamable HTTP is a governance and metadata plane. It cannot create, inspect, download
into, validate, or mutate a caller workspace and does not expose a workspace-creation tool.

Decision 5: Workspace publication is create-only and transactional. Filesystem root, user home,
symlink roots, non-directories and non-empty unowned roots fail closed. An exact completed retry may
return `unchanged`; partial, edited or divergent trees fail.

Decision 6: Successful local creation emits a `local-mcp-observed` receipt containing the installed
generator version, status, file and entry counts, and expected/observed tree digest. Tool success is
not runtime, deployment, client-conformance or production-admission evidence.

Decision 7: The selected Agent Platform clients are persisted in `Answers` and replayed by update.
Initialization compiles only those inert projections. Live client discovery still requires the
separate Agent Platform activation/admission boundary.

Decision 8: A preinstalled CLI `apply-bundle` capability may remain for controlled offline import,
but no MCP prompt, tool result or HTTP route distributes an executable applicator.

## Verified baseline and gap

The canonical renderer, transactional `project_init`, CLI, governance catalog and Agent Platform
compiler already existed. The former interactive MCP path prepared downloadable bundle, descriptor
and Python-applicator references, leaving the coding client to retrieve and execute another program.
VS Code correctly treated that as untrusted downloaded code, produced extra approval boundaries and
could not complete creation when the HTTP artifact route was unavailable. The accepted gap is a
trusted local stdio operation that calls the already installed renderer directly, while preserving a
separate workspace-blind HTTP governance plane.

## Functional requirements

Requirement 1: Bootstrap input requires project intent and primary domain and validates product name,
slug, locales, tenant header, observability and selected Agent Platform client identifiers.

Requirement 2: The fixed profile derives environment and API prefixes when omitted. Caller-visible
inputs expose no stack selector, target path, overwrite/delete flag, VCS operation, arbitrary
execution field, bundle transport detail or secret.

Requirement 3: Local MCP startup validates one explicit absolute workspace root and binds every
creation call to it. HTTP transport rejects a workspace-root configuration.

Requirement 4: One local creation call invokes the existing installed `project_init` operation
in-process and creates the full scaffold transactionally.

Requirement 5: The renderer emits the application baseline, specifications, rules, selected inert
agent projections, technology profile, scripts, manifests, schema, deployment assets and evidence
harness expected by the resolved profile.

Requirement 6: Identical answers, selected clients and installed version produce identical bytes and
tree digests through CLI and local stdio MCP.

Requirement 7: The local result contains no source bodies. It reports only a bounded receipt, counts,
digests and normal next steps.

Requirement 8: English and Turkish local creation aliases share one strict argument schema and one
implementation. Unknown inputs fail validation.

Requirement 9: The start prompt asks only the bounded business questions and one business
confirmation, then calls the local creation tool. It contains no download, applicator, Python,
terminal or target-path choreography.

Requirement 10: HTTP tool discovery remains workspace-independent and excludes local creation.
Local stdio discovery includes the same governance operations plus local creation.

Requirement 11: Agent-client selection is persisted as immutable project desired state for ordinary
updates. Changing it requires a future explicit migration operation, not an update override.

Requirement 12: Generated projects contain no Project Factory implementation and no project-local MCP
registration. Client registration remains user/organization managed.

## Security and authorization

- The trusted local package and client MCP registration are installation-time authorities; the model
  cannot choose a different executable or workspace root at call time.
- Root validation occurs at startup and again immediately before publication.
- Creation refuses user home, filesystem root, symlinks, partial targets, edited completed targets and
  environment-prefix collisions.
- The remote service receives no target path, source tree, workspace snapshot, secret, database
  content, VCS state or caller-authored patch.
- HTTP identity, TLS/mTLS, OAuth audience/scopes, rate limits and audit remain external gateway duties.

## Data and migration

- Answers contain no secrets and persist selected Agent Platform client IDs.
- Existing projects without `agent_clients` load with all four supported clients for backward compatibility.
- This release removes executable-applicator references from MCP discovery and prompt contracts. The
  low-level offline CLI is retained without a compatibility promise for remote artifact delivery.
- Managed update continues to preserve project-owned edits and fails transactionally on conflicts.

## Validation, observability, and evidence

- L1: strict schemas, safe-root negatives, no-download/no-shell contract, alias parity, deterministic
  digest, exact retry, partial-target rejection, transaction rollback and update replay.
- L2: a real MCP `ClientSession` starts the installed stdio server against a disposable empty root,
  calls local creation once, observes the receipt and verifies the resulting tree independently.
- L2: a real Streamable HTTP session proves the remote surface excludes local creation and remains
  workspace-blind.
- L2 client discovery and L3 runtime admission remain separate Agent Platform evidence.

## Deployment and operations

- VS Code and other approved clients register the same installed command over stdio with an explicit
  workspace-root argument and a client sandbox allow-write scoped to that root.
- The Rancher/RKE2 deployment remains governance-only and must not advertise applicator downloads.
- Rollback may revert the installed/server version but must not remotely alter created repositories.

## Acceptance criteria

- [x] The accountable owner accepts the trusted-local versus remote-governance boundary.
- [x] Local stdio creation writes a fresh empty workspace without terminal or runtime download.
- [x] CLI and local stdio produce byte-identical trees and equal observed digests.
- [x] Exact completed retry is unchanged; unsafe, partial, edited and divergent targets fail closed.
- [x] Selected client IDs persist and update regenerates the same inert projection inventory.
- [x] HTTP discovery contains no workspace creation or executable-applicator delivery surface.
- [x] Full repository quality gates pass.
- [x] The immutable Rancher/RKE2 image exposes only the governance plane and passes MCP readiness.

## Delivery flow

Accepted -> implementation plan -> ordered tasks -> L1 gates -> local stdio L2 -> LAB governance L2
