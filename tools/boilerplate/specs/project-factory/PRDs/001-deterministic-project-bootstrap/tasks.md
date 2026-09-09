# Tasks — Deterministic project bootstrap

Status: Active

- [x] **T01 — Persist Agent Platform client selection.** Requirements 1, 5, 11. Add strict answer and
  CLI/MCP input validation; render only selected inert clients; prove update replay.
- [x] **T02 — Implement trusted local creation operation.** Requirements 2–8. Bind a safe startup root,
  call installed `project_init` in-process, support exact retry and emit a local observed receipt.
- [x] **T03 — Split local and remote MCP surfaces.** Requirements 8–10, 12. Local stdio exposes
  creation plus governance; HTTP remains workspace-blind and carries no executable delivery.
- [x] **T04 — Replace start-prompt choreography.** Requirement 9. Remove archive, applicator, Python,
  shell and target-selection instructions; retain business questions and one confirmation.
- [x] **T05 — Add L1 and L2 regressions.** Requirements 1–12. Cover strict schemas, unsafe roots,
  exact retry, digest parity, real stdio session, HTTP discovery and no-download/no-shell behavior.
- [x] **T06 — Run complete quality gates.** Acceptance criterion 7. Run Ruff, format, mypy and full
  Pytest; retain exact results.
- [x] **T07 — Verify LAB governance deployment.** Acceptance criterion 8. Build/deploy only after
  local gates, then prove immutable image, HTTP MCP initialization and workspace-independent tools.
