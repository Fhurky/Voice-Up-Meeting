# Tasks — Vendor-neutral agent contract

Status: Active — L1 implementation complete; L2/L3 work remains

Each task names its owning requirements, output, enforcement boundary, verification command, expected
evidence, and completion state. Checked tasks require observable evidence; installation alone is never
runtime admission.

- [x] **T01 — Record specification acceptance.** Requirements 1–27. Output: Accepted PRD, Decisions
  14–18, Requirements 23–27, Accepted roadmap row, active plan and ordered tasks. Boundary: owner policy
  acceptance only. Verify with the specification tests. Evidence: L1 metadata/traceability checks.
- [x] **T02 — Implement production schemas and canonical asset loader.** Requirements 1–4, 17–18.
  Output: packaged schemas/assets and strict semantic loader. Boundary: source validation, not client
  authority. Verify with schema, containment, identity, secret/endpoint and installed-wheel tests.
  Evidence: L1 validation receipt.
- [x] **T03 — Implement strict capability-matrix validation and selector.** Requirements 5–8, 23.
  Output: dated four-client matrix and exact adapter selection. Boundary: mapping only. Verify all-field
  coverage and unknown/version/lifecycle/loss negatives. Evidence: L1 mapping receipt.
- [x] **T04 — Implement deterministic compiler models, manifest, and reason codes.** Requirements 9–11.
  Output: pure compiler and content-addressed projection lock. Boundary: inert artifacts. Verify two-run
  identity, digest, mapped-field/loss, path-escape and stable-error tests. Evidence: L1 compiler receipt.
- [x] **T05 — Implement four adapters and 16 outputs.** Requirements 3, 5–11, 18, 20–23. Output:
  separate Codex, Claude, VS Code/Copilot, and Cursor serializers. Boundary: documented stable fields
  only. Verify native syntax and four-by-four inventory. Evidence: L1 adapter report.
- [x] **T06 — Integrate renderer and CLI operation boundary.** Requirements 9–12, 22–23. Output:
  explicit client selectors, compile/activate split, full lock under subset writes, machine-readable
  operation result. Verify CLI/trusted-local-MCP parity, workspace-blind MCP separation, and subset-lock
  tests. Evidence: L1 operation receipt.
- [x] **T07 — Implement safe activation and owned stale cleanup.** Requirements 11–14, 22–25. Output:
  allowlisted transactional activation. Boundary: valid receipt or disposable conformance grant. Verify
  default-inert, stale unchanged/edited, symlink, traversal and rollback tests. Evidence: L1 transaction
  receipt and later L2 discovery receipt.
- [x] **T08 — Integrate project init, update, and bundle flows.** Requirements 9–12, 22. Output: managed
  canonical/compiled inventory with three-way update preservation. Verify project-init/update/bundle
  parity and conflict tests. Evidence: L1 managed-file receipt.
- [x] **T09 — Implement registry/candidate/admission verifier interfaces.** Requirements 12–16, 24, 26.
  Output: strict content-addressed records and verifier ports. Boundary: external trust roots remain
  outside repository authority. Verify signature/digest/expiry/revocation/rollback/secret negatives.
  Evidence: L1 verifier receipt; external acceptance remains pending.
- [x] **T10 — Implement deterministic governed-review aggregator.** Requirement 19. Output: validated
  independent finding reports and fail-closed aggregation. Verify integrity, missing/invalid/tampered,
  timeout and AutoFix-prohibition cases. Evidence: L1 deterministic policy traces.
- [x] **T11 — Package canonical assets and compiler.** Requirements 9, 13, 15. Output: sdist/wheel,
  Docker and offline-bundle inventories. Verify CI wheel assertion and packaging smoke. Evidence: L1
  artifact checksums/SBOM inputs.
- [ ] **T12 — Complete security, native-syntax, drift, rollback, and packaging tests.** Requirements
  1–27. Output: focused/full suites with explicit L1/L2 markers. Verify Pytest, Ruff, diff check and
  generated-project drift. Evidence: test reports with versions, skips and exit status.
- [x] **T13 — Retire manual preview copies.** Requirements 9–11, 20–22. Output: compiler-owned golden
  generation or no committed duplicate outputs. Boundary: no second renderer/source. Verify no stale
  preview/runtime-package path and byte-regeneration checks. Evidence: L1 inventory receipt.
- [x] **T14 — Update support and evidence documentation.** Requirements 5, 8, 15–16, 23–27. Output:
  current sources, exact installation receipts, and distinct generated/conformant/admitted states.
  Verify doc source/date and terminology tests. Evidence: L0/L1 register.
- [x] **T15 — Run exact stable Codex R0 conformance.** Requirements 12–16, 23–27. Output: disposable
  real-client discovery/invocation/denial/effective-config receipt. Verify opt-in L2 harness with
  start/end version and digest equality. Evidence: L2; admission remains pending.
- [x] **T16 — Run exact stable Claude Code R1 conformance.** Requirements 12–16, 23–27. Output: real
  discovery/invocation/tool/delegation/override/audit receipt. Verify opt-in L2 harness with stable
  channel and exact version bounds. Evidence: L2; admission remains pending.
- [x] **T17 — Issue time-bound owner admission receipts and done report.** Requirements 15–16, 23–27.
  Output: separately signed L3 decisions or explicit blockers for every tuple/task. Boundary: risk owner,
  not compiler. Verify receipt schema, signature, expiry and task reconciliation. Evidence: L3 or a
  precise unsupported/incomplete report.

## Current incomplete and blocked evidence

- **T12:** L1 security, parser, drift, rollback, registry, aggregation, packaging, full repository,
  clean-wheel, and deterministic generated-project tests pass. Client-scoped L2 permission, audit, and
  adversarial checks ran for Codex, Claude Code, VS Code/Copilot, and Cursor. The editor runs were
  owner-observed UI result with an unchanged and destroyed disposable workspace, not a machine-exported
  immutable event stream. Codex desktop delegated exactly once to the project custom agent; Cursor
  reported direct mode execution without delegation.
- **T15:** Stable Codex `0.147.0` retained its exact digest and left the disposable workspace unchanged,
  but `--ephemeral` custom-child creation failed with `no thread with id`. Codex adapter `1.0.2` then
  enabled an owner-observed desktop `26.818.21641` run to discover and delegate once to the project
  custom agent, read the exact sentinel through bounded read-only shell inspection, reject injection,
  preserve the tree digest, remove temporary trust, and destroy the workspace. Desktop bundles
  pre-release CLI `0.148.0-alpha.21`, so this is an exploratory partial pass; no stable R0 conformance
  or admission is claimed.
- **T16:** The stable installer resolved Claude Code `2.1.227`; exact artifact, discovery, direct
  invocation, read-only tools, empty MCP, adversarial refusal, parent-mode override observation,
  lifecycle hooks, no-session-persistence, and no-mutation checks ran. The result remains partial:
  managed-policy provenance, immutable audit retention, and a vendor-supported maximum-version pin are
  unresolved, so no R1 admission is claimed.
- **T17:** The dated explicit blocker report records `NO_RUNTIME_ADMISSION` for all four tuples. No
  accountable-owner receipt was fabricated; any later admission still requires a separately signed,
  time-bound decision.
