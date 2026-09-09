# Tasks — local-speaker-pilot

Status: Implementation delivered; external validation incomplete

Authority: [Accepted PRD](PRD.md); order: [plan](plan.md).

- [x] T01 Record scope acceptance and derive implementation plan.
- [x] T02 Prepare/verify Python 3.13, PostgreSQL 17, pgvector and CUDA dependencies and isolated configuration. Record runtime checks and admission evidence.
- [x] T03 Define API/inference contracts and implement lifecycle/tenant authority plus reviewed migration. Requirements 1–8; real database schema tests.
- [x] T04 Implement bounded uploads, retention, idempotent jobs, fenced worker and guarded enrollment/matching. Requirements 2–8; unit/integration tests include races and wrong-person append.
- [x] T05 Implement offline ECAPA/VAD inference with explicit readiness/device and audio quality checks. Inference tests and genuine 4060 result are separate evidence.
- [x] T06 Implement TR/EN profiles, analysis and durable job pages with auth/permissions/generated types. Requirements 1–5,7; frontend checks and actual browser evidence.
- [x] T07 Wire worker/inference, volumes, typed configuration and charts. Verify 8081 stack without affecting existing applications.
- [x] T08 Run full quality gate; retain exact output and report every failed/skipped/blocked check in docs/evidence.
- [ ] T09 Measure specified cross-session quality and 4060 warm p95 on 20 jobs. Missing user recordings leave quality explicitly incomplete.

Only mark complete after corresponding evidence exists; retain partial work and external blockers in this list and the handoff report.

## Current evidence

- T03/T04: 59 backend tests (44 unit, 15 real PostgreSQL integration), final contract regression report and JUnit in `docs/evidence/2026-09-08-local-speaker-pilot/`.
- T08: full application gate passed with 21 frontend tests, schema/config/contracts/governance/charts. The separate security gate was attempted and failed because the admitted scanner environment is absent; the permanent Playwright harness lacks its admitted bundle. Both are explicitly recorded and do not count as passed acceptance gates.
- T02/T05/T07: hash-verified 62-wheel CUDA cache, successful offline Docker build, and 12 genuine CUDA/network-none HTTP checks passed on RTX 4060. Compose /ready reports cuda:0 and remains healthy. T06: actual CUA verified enrollment/append, wrong-target rejection, recognized/unknown/ambiguous decisions, silence rejection, rename/delete and deleted-history display; the frontend report records technical fixture scope. The 20-job measurement completed: all20 single-attempt CUDA recognized outcomes; execution p95 0.868519s, queue p95 1.951230s, servertotal p95 2.720627s. It is a repeated public fixture with one persisted technical profile, not accuracy/capacity evidence.
- The requested separate-session user dataset has not been supplied. T09 quality remains incomplete even if the technical GPU/latency checks pass.

### T09 remaining evidence

- [x] Warm 30-second / 20-job RTX4060 latency: target passed; `docs/evidence/2026-09-08-local-speaker-pilot/4060-benchmark.json` and `4060-environment.json`.
- [x] T09 dataset preparation kit: read-only manifest/audio validator, 32-recording template and collection guide. [Focused evidence](../../../../docs/evidence/2026-09-09-dataset-readiness/dataset-kit-run-report.md); readiness is not recognition accuracy.
- [ ] Five known participants, separate-session queries, unknown participants and later return: user recordings unavailable. No quality success claimed.

Formal acceptance also retains the separately documented missing admitted security scanner environment and permanent Playwright bundle. Local software gates and actual CUA evidence do not replace these external inputs.
