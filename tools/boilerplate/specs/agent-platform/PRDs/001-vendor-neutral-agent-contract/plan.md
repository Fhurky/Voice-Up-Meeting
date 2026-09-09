# Plan — Vendor-neutral agent contract

Status: Active

The adjacent [PRD](PRD.md) is `Status: Accepted`. This plan authorizes implementation but does not
promote any generated projection to runtime admission. Generation, activation, conformance, and
time-bound owner admission remain separate evidence states.

## Delivery slices

### S0 — Acceptance record

- Requirements: 1–27 and the first two acceptance criteria.
- Files: PRD, roadmap, this plan, tasks, specification regression tests.
- Verification: `pytest -q tests/test_agent_platform_contract.py tests/test_product_spec_catalog.py`.
- Evidence: L1 metadata and traceability checks.

### S1 — Canonical assets, schemas, and loader

- Requirements: 1–4, 17–18.
- Files: `agent-platform/`, installed asset resolver, contract/policy/catalog schemas and validators.
- Controls: strict unknown-field rejection, package containment, identity/policy binding, secret and
  endpoint rejection, repository/install asset parity.
- Verification: focused schema/semantic tests plus wheel asset inspection.
- Evidence: L1 validation reports and asset digests.

### S2 — Capability matrix and adapter selection

- Requirements: 5–8, 23.
- Files: capability matrix schema/data and exact adapter selector.
- Controls: dated primary sources, stable versus volatile lifecycle, exact client/surface/adapter
  selection, and fail-closed unknown/unmapped/forbidden/material-loss handling.
- Verification: matrix coverage and negative selection tests.
- Evidence: L1 mapping report; documentation mapping is not runtime support.

### S3 — Deterministic compiler and manifest

- Requirements: 9–11.
- Files: compiler models, reason codes, adapters, projection manifest/lock.
- Controls: canonical and output digests, explicit mapped fields/losses/external bindings, byte-stable
  output, strict path ownership, no timestamp in deterministic payloads.
- Verification: two-run byte identity, native parse, path escape, and semantic-loss tests.
- Evidence: L1 compiler receipt and content-addressed projection manifest.

### S4 — Four native adapters

- Requirements: 3, 5–11, 18, 20–23.
- Targets: Codex, Claude Code, VS Code/GitHub Copilot, and Cursor.
- Controls: separate native serialization per client; no compatibility copy; only documented stable
  fields; required unsupported semantics fail closed or remain explicit external requirements.
- Verification: four canonical agents times four clients equals 16 deterministic native outputs.
- Evidence: L1 syntax, mapping, and loss reports. Hosted ChatGPT Work remains unmapped for repository
  discovery.

### S5 — Renderer, CLI, project, and update integration

- Requirements: 9–12, 22–23.
- Files: renderer, CLI/operation boundary, project initialization, bundle and update flows.
- Controls: compile versus activate mode, explicit client ownership instead of path-prefix inference,
  complete locks under subset rendering, machine-readable results, CLI/trusted-local-MCP parity, and no
  implicit workspace authority in the global MCP service.
- Verification: init/render/update/bundle tests including subset-lock regression, CLI/trusted-local-MCP
  parity, and the intentional workspace-blind global MCP separation.
- Evidence: L1 managed-inventory and conflict-preservation receipts.

### S6 — Safe activation and stale retirement

- Requirements: 11–14, 22–25.
- Files: activation transaction, ownership lock, allowlisted discovery roots.
- Controls: receipt or disposable-conformance grant, unchanged-owned stale deletion only, edited/unowned
  stale fail-closed, symlink/path-escape rejection, rollback on partial failure.
- Verification: activation, stale, tamper, rollback, and default-inert scaffold tests.
- Evidence: L1 transaction receipt; L2 client discovery only in an admitted or ephemeral workspace.

### S7 — Registry, signature, receipt, and revocation boundary

- Requirements: 12–16, 24, 26.
- Files: strict candidate/admission receipt models and verifier interfaces; no embedded trust authority.
- Controls: signature/digest/expiry/revocation verification, bounded freshness, effective live-config
  capture, no workspace fallback or secret passthrough.
- Verification: unknown key, bad signature, rollback, expiry, stale revocation and secret-leak negatives.
- Evidence: L1 verifier tests; external registry and signer evidence remains deployment-owned.

### S8 — Governed orchestration

- Requirements: 19.
- Files: independent worker report schemas and deterministic aggregation implementation.
- Controls: integrity checking, no raw source at aggregator, `MANUAL_REVIEW` for missing/invalid/tampered
  evidence, no AutoFix.
- Verification: deterministic aggregation and fail-closed negative suite.
- Evidence: L1 policy traces; thresholds require later representative L2/L3 calibration.

### S9 — Packaging, offline, and supply chain

- Requirements: 9, 13, 15.
- Files: wheel/sdist data, Docker image, offline bundle, CI asset verifier and SBOM/provenance inputs.
- Controls: one canonical asset source, exact packaged inventory, digest equality, no preview fixtures in
  runtime packages.
- Verification: wheel/sdist/offline/Docker smoke and inventory tests.
- Evidence: L1 artifact inventory, checksums and build reports.

### S10 — L1 tests, documentation, and duplicate cleanup

- Requirements: 1–11, 17–23.
- Files: native parser/golden/negative/drift tests, support-level docs, evidence register.
- Controls: remove hand-maintained projection previews after compiler equivalence is proven; keep no
  stale or second canonical renderer.
- Verification: focused and full test suites, Ruff, diff check, generated-project drift check.
- Evidence: L1 test receipts with skips and unsupported states reported explicitly.

### S11 — L2/L3 conformance and admission

- Requirements: 12–16, 23–27.
- Scope: exact stable Codex R0 and Claude Code R1 candidates first; other clients remain generated but
  not admitted until separate exact tuples pass the same gate.
- Verification: real discovery/invocation/precedence, effective permissions, denial, injection,
  exfiltration, delegation, audit, drift, rollback, start/end version and digest capture.
- Evidence: L2 conformance receipts followed by separate, time-bound L3 owner admission receipts.

## Completion rule

Every slice reports completed, incomplete, blocked, and deliberately unsupported evidence separately.
No adapter-generation result, client installation, documentation mapping, or green mock is treated as
runtime admission.
