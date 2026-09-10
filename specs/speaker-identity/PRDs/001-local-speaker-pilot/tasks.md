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
- [ ] T09 Meet the specified cross-session quality and measure 4060 warm p95 on 20 jobs. Timing passed; the public Spark experiment measured insufficient recognition coverage and a failed held-out return. Representative Turkish recordings and quality acceptance remain incomplete.

Only mark complete after corresponding evidence exists; retain partial work and external blockers in this list and the handoff report.

## Current evidence

- T03/T04: 59 backend tests (44 unit, 15 real PostgreSQL integration), final contract regression report and JUnit in `docs/evidence/2026-09-08-local-speaker-pilot/`.
- T08: full application gate passed with 21 frontend tests, schema/config/contracts/governance/charts. The separate security gate was attempted and failed because the admitted scanner environment is absent; the permanent Playwright harness lacks its admitted bundle. Both are explicitly recorded and do not count as passed acceptance gates.
- T02/T05/T07: hash-verified 62-wheel CUDA cache, successful offline Docker build, and 12 genuine CUDA/network-none HTTP checks passed on RTX 4060. Compose /ready reports cuda:0 and remains healthy. T06: actual CUA verified enrollment/append, wrong-target rejection, recognized/unknown/ambiguous decisions, silence rejection, rename/delete and deleted-history display; the frontend report records technical fixture scope. The 20-job measurement completed: all20 single-attempt CUDA recognized outcomes; execution p95 0.868519s, queue p95 1.951230s, servertotal p95 2.720627s. It is a repeated public fixture with one persisted technical profile, not accuracy/capacity evidence.
- The requested separate-session user dataset has not been supplied. T09 quality remains incomplete even if the technical GPU/latency checks pass.

### T09 remaining evidence

- [x] T10 / Decision 6: prepared licensed public audio with deterministic source-separated development/test manifests and file/hash validation: 140 selected people, 604 WAV clips.
- [x] T11 / Decision 6: ran the real Spark application with isolated galleries, known/unknown probes, enrollment and later return; all 302 calibration and 707 held-out operations reached terminal outcomes. Failures remain in denominators. Held-out return failed quality checks; execution completion is not quality acceptance.
- [x] T12 / Decision 6: protected three launcher defects and reporting boundaries with regression tests; 819 unique automated tests, 16 actual browser checks, and the final 90-test full profile gate passed. The missing security/browser admission bundles remain explicit.
- [x] T13 / Decision 7: delivered the calibration-selected 0.55 pilot acceptance threshold with typed/default/environment consistency, boundary tests and real application calibration/test evidence. Preserved historical results; no test-set tuning or relaxation of quality guards.

Public experiment evidence: [2026-09-09 report](../../../../docs/evidence/2026-09-09-public-speaker-evaluation/README.md).
Calibration enrolled 40/50 and correctly identified 109/150 probes. Held-out testing
enrolled 29/50 and correctly identified 77/150 probes; 26 known queries failed
quality checks. No wrong identities were observed, but 20/100 unknown queries
failed quality checks. The quality target and held-out new-person return are not
met. Investigate discarded short speech regions and inconsistent-window rejection
on calibration data before admitting a preprocessing/model change; retain a fresh
untouched evaluation set and representative Turkish acceptance.

- [x] Warm 30-second / 20-job RTX4060 latency: target passed; `docs/evidence/2026-09-08-local-speaker-pilot/4060-benchmark.json` and `4060-environment.json`.
- [x] T09 dataset preparation kit: read-only manifest/audio validator, 32-recording template and collection guide. [Focused evidence](../../../../docs/evidence/2026-09-09-dataset-readiness/dataset-kit-run-report.md); readiness is not recognition accuracy.
- [ ] Five known participants, separate-session queries, unknown participants and later return: user recordings unavailable. No quality success claimed.

Formal acceptance also retains the separately documented missing admitted security scanner environment and permanent Playwright bundle. Local software gates and actual CUA evidence do not replace these external inputs.

## Decision 8 — recover fragmented speech conservatively

- [x] T14 Freeze and run calibration-only candidate/compatibility/negative diagnostics; publish aggregate selection evidence against the previous 40/50 and 109/150 baseline. Guarded candidate: 40/50 and 111/150, no additional negative accepts; see `docs/evidence/2026-09-09-speech-recovery/calibration-diagnostic-report.md`.
- [x] T15 Add the tested inference fallback and typed preprocessing provenance with old-result compatibility; preserve existing successful evidence and inconsistency rejections. Regenerate changed contracts/types. Inference 96 tests and metadata/API integration passed; actual recovered browser query recognized the expected profile.
- [x] T16 Prepare a fresh, deterministic 50-known/20-unknown public holdout, excluding all previously inspected development/test speakers; test archive and manifest boundaries. New 302-WAV manifest and exact replay passed; original 604 selections preserved, all 146 old speakers excluded.
- [x] T17 Build/deploy the admitted source-only Spark update with the previous image retained; run actual calibration, historical regression and fresh holdout including failed jobs and newcomer return. All 906 jobs terminal: 780 succeeded, 126 quality failures; results and source/image identity in `docs/evidence/2026-09-09-speech-recovery/README.md`.
- [x] T18 Run final relevant automated/live/full-profile checks, verify original data and one-click readiness, document every unavailable acceptance point and the observed improvement or rejection of the candidate. 552 unique automated cases, 11 browser flows, final full gate and both PowerShell launchers passed; 31 final preservation/access checks passed. Missing security/browser admission and unmet accuracy/representative-data criteria remain explicitly open above and in the report; this task does not mark the whole capability accepted.

## Decision 9 — explicit speaker quality metrics

- [x] T19 Define the versioned identity/unknown F1 and project score protocol, failure accounting, zero-denominator policy and worked example in `docs/SPEAKER_METRICS.md`. Decision 9 records the user's metric request; standard formulas and the distinct project score are documented before re-scoring.
- [x] T20 Extend the existing reporter with manifest-bound, anonymous deterministic metrics; prove exact formulas, wrong identities, failed enrollment, abstentions, missing work, malformed/duplicate data and legacy compatibility through red/green tests. 92 new metrics cases plus 13 unchanged reporter and 59 evaluator cases passed on offline Linux Python 3.13.14; Windows repeated 105 of the same cases. See `docs/evidence/2026-09-09-speaker-metrics/native-tests-report.md`.
- [x] T21 Re-score the three immutable prior runs, independently verify results and privacy, run the relevant automated/full-profile gates, and record scope and unavailable evidence in a new report without claiming a new live model experiment. Three offline CLI runs succeeded; 1,304 independent checks matched all metrics, 98 preserved files remained unchanged, and the new evidence content review found no private identity/credential disclosure. 270 unique automated tests and the final full profile gate passed; the unavailable security scanner and representative-data acceptance remain open. Source hashes and evidence were rechecked on 10 September without repeating model/tests; see `docs/evidence/2026-09-09-speaker-metrics/README.md`.

## Decision 10 — at most 50 active speaker profiles

Historical scope superseded by the user's clarification in Decision 11; its
recorded test evidence remains immutable and does not define the current target.

- [x] T22 Enforce the tenant-scoped 50-profile invariant at service admission and atomic worker completion; add real PostgreSQL boundary and concurrency regression tests. Eleven new cases cover 49/50/51, concurrent admission/completion, replay, append/identify, deletion and tenant/model scope; the final gate passed all 96 backend tests. See `docs/evidence/2026-09-10-speaker-capacity/backend-report.md`.
- [x] T23 Deliver required API capacity metadata, generated contracts, localized capacity/form/error behavior and committed browser scenario; verify both locales through the real UI. Generated contracts are current; 37 frontend tests passed. Eight live CUA acceptance points cover both locales, pagination, append/identify availability and terminal messages. The permanent Playwright scenario exists but its admitted bundle is unavailable; it is not counted as run. See `docs/evidence/2026-09-10-speaker-capacity/live-browser-report.md`.
- [x] T24 Bound new evaluator galleries and record capacity-limited newcomer outcomes honestly; run focused/full gates and live deployment checks, document all evidence and unavailable inputs without claiming improved model accuracy. The actual CLI full-gallery regression and 184 evaluator/metrics/legacy cases passed on offline Python 3.13.14; Windows repeats are not double-counted. The full profile gate passed, Windows services were restarted, and real HTTP rejected a new profile at 50 without a new job. Missing security/browser admission and representative-data acceptance remain open in `docs/evidence/2026-09-10-speaker-capacity/README.md`.

## Decision 11 — 50-person quality target without a profile quota

- [x] T25 Remove the product quota across service/worker/API/UI while preserving tenant, idempotency, sample and historical-job behavior; protect enrollment beyond 50 and 200 with real-boundary tests and regenerate contracts. Evidence: [backend](../../../../docs/evidence/2026-09-10-speaker-quality-target/backend-report.md), [frontend](../../../../docs/evidence/2026-09-10-speaker-quality-target/frontend-green-report.md), and the full gate's 97 backend/39 frontend passes.
- [x] T26 Align evaluator/metrics manifest support through 200 without changing formulas or old results; document measured enrollment failure contributions and compare model candidates using primary sources. Evidence: [234 Python 3.13 passes/1 platform skip](../../../../docs/evidence/2026-09-10-speaker-quality-target/evaluator-run-report.md), [diagnosis](../../../../docs/evidence/2026-09-10-speaker-quality-target/diagnosis-report.md), [research proposal](../../../../plans/SPEAKER_QUALITY_50.md); no new model or threshold selected.
- [x] T27 Update current docs/scenario, deploy the coordinated local change, run focused/full gates and both-locale browser checks, and record unavailable evidence without claiming new model accuracy. Evidence: [handoff](../../../../docs/evidence/2026-09-10-speaker-quality-target/README.md), including real Spark enrollment 50→51, six TR/EN browser acceptance points and the unchanged historical job. Security tooling and admitted Playwright bundle remain unavailable; representative quality and L3 acceptance remain open.
