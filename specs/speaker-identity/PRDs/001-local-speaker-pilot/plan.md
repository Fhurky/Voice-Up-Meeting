# Plan — local-speaker-pilot

Status: Implementation delivered; external validation incomplete

Authority: [Accepted PRD](PRD.md), accepted 8 September 2026. Evidence: [tasks.md](tasks.md).

1. Prepare the isolated VoiceUp runtime on port 8081, preserving other applications. Verify admitted package/image sources, PostgreSQL 17 with pgvector and separate Python 3.13 CUDA inference. Package pinned ECAPA for offline runtime; explicit readiness/device errors precede inference.
2. Implement tenant-scoped SQLAlchemy recordings/profiles/samples/jobs, reviewed Alembic migration, typed HTTP inference port, permissions and bounded uploads (requirements 1–8). Include exact ranking over all eligible profiles, guarded enrollment, idempotency, leases with fencing, two-attempt retry and reference-aware cleanup.
3. Add localized profile, analysis and resumable job pages using existing authentication and generated OpenAPI types. Display unknown/ambiguous outcomes and raw similarity honestly; identification never enrolls.
4. Verify with unit and real PostgreSQL tests for isolation, duplicate submission, transactions, deletion, stale workers and wrong-person append. Regenerate API/types and synchronize configuration/charts. Exercise actual browser/API and genuine GPU inference; run the full quality gate and record all failures.
5. Measure GPU performance separately from identity quality. The 20-job real RTX 4060 experiment is complete (execution p95 0.868519s). The representative five-person Turkish cross-session dataset remains unavailable. The Decision 6 public-data evaluation adds a disjoint English identity baseline on Spark; it does not replace that acceptance input. See tasks.md and the evidence report for the observed denominators and remaining validation.

6. Prepare representative T09 data with `scripts/validate-speaker-dataset.py`, the pseudonymous manifest template and `docs/DATA_COLLECTION.md`. Check real files, phase roles, cross-session/source separation, duplicates and pilot upload limits without running inference. A ready dataset is not an accuracy result. Decision 6 now provides the separate public-data API evaluator; representative recordings remain required.

Ownership: backend agent owns backend/domain/schema and tests; frontend agent owns frontend workflow/tests; inference agent owns inference service/package/tests; main agent owns integration, dependency/runtime preparation, deployment surfaces and final evidence. API/inference contracts are shared before dependent implementation.

Decision 7 delivery: change the application MatchPolicy and typed Settings defaults,
backend environment example and local Compose worker/backend environment together.
Keep the research reference's historical policy explicit and unchanged. Add decision
boundary tests for the calibrated threshold, unknown cutoff and margin; prove selected
policy propagation in live API results. No schema, model revision, API shape or UI
string changes are required. The evaluator accepts an explicit frozen policy file
bound into resume state. Preserve the old calibration run; execute the selected
policy through the real application in new calibration and untouched test tenants.
Run the full gate after configuration changes. Report unresolved quality rejections.

7. Decision 6 / T09: prepare the official LibriSpeech development and test archives
through `scripts/prepare-public-speaker-dataset.py`, recording licenses, archive
checksums, disjoint speakers and source chapters in a deterministic manifest. Run
`scripts/evaluate-public-speakers.py` through the public upload/job/profile API in
dedicated evaluation tenants on Spark. Measure all planned known/unknown probes,
quality failures, confidence intervals and gallery sizes 5/10/20/50 when eligible
data permits. Freeze the calibration-selected policy before test model results; do not tune on test.
Use development data only for calibration diagnostics. Record unknown enrollment
and a disjoint return probe separately after the frozen gallery experiment. Cover
runner failure/denominator/idempotency contracts, actual browser workflows, the full
quality gate and unavailable security/browser admission checks. Public data evidence
does not complete the representative Turkish separate-session acceptance criterion.

Earlier observations: [4060 foundation note](../../../../plans/RTX_4060_FOUNDATION.md).

8. Decision 8: freeze the calibration-only diagnostic before running its scores.
Compare the continuous baseline with chronological voiced packing and the
insufficient-only fallback; retain all original thresholds. Measure enrollment,
known/unknown outcomes, original-profile compatibility and fixed mixed/wrong-person
negative cases. Keep raw audio/vectors and diagnostic programs under ignored
evaluation output; publish only aggregate evidence and algorithm/source hashes.
After the first two candidates failed gapped mixed-speaker negatives, freeze the
guarded candidate separately: minimum 1.5-second original blocks, per-block
quality and pairwise/pooled-vector consistency guards at the unchanged 0.55.
9. Decision 8: derive and test a bounded inference-side speech preparation helper
from the selected fallback, leaving the research reference's continuous semantics
intact. Real HTTP tests cover fragmented speech, sample accounting, exact successful
baseline preservation, insufficient total speech, inconsistency, silence/clipping,
partial-anchor disagreement and error recovery. Add strictly typed preprocessing
provenance through the existing HTTP adapter, result contract and job JSON where
required; old stored job results remain readable. Regenerate contracts/types if
the public result shape changes. UI navigation and database schema are unchanged
unless discovery establishes an actual need, recorded before implementation.
10. Decision 8: extend the existing public-data preparer with an explicit fresh
holdout mode, reviewed official archive sizes/checksums and bounded extraction.
Exclude every speaker in the four prior splits. Preserve existing manifests and
add deterministic provenance/isolation/limit regression tests. No fresh holdout
inference runs before the selected candidate is frozen.
11. Decision 8: build the source-only Spark image offline from the unchanged pinned
dependencies, retain the prior immutable image for rollback and deploy only after
calibration gates pass. Verify genuine application calibration, historical
regression and untouched holdout in isolated tenants; check old profiles remain
unchanged and cross-tenant isolation, wrong-person append and newcomer return.
Run the relevant inference/API/data tests, full profile gate, actual browser/API
flows and one-click readiness. Report unmet accuracy and security admission inputs.

12. Decision 9: define `docs/SPEAKER_METRICS.md` before computing new scores. Extend
the existing public reporter with an explicit versioned protocol and manifest-bound
validation; preserve its legacy invocation/output. Derive identity micro and macro
F1, unknown-class F1, the documented harmonic project score and enrollment coverage
from planned operations. Reject duplicate/malformed/mismatched data; expose incomplete
work and undefined denominators. Add red/green boundary and exact worked-example
tests without dependencies. Re-score the three immutable private reports into a new
anonymous evidence directory and independently verify counts, formulas and privacy.
Keep old reports unchanged; run the relevant reporter/evaluator tests and full
`kt-vibecoding-python-web-v2` gate. API, UI, persistence, runtime and deployment
layers are N/A because only offline evidence generation changes.

13. Decision 10: introduce a shared domain maximum of 50 active profiles per tenant
and an adapter-owned count across model revisions. Check new enrollment after
idempotent replay at request admission and under the existing tenant transaction
lock immediately before worker profile creation. Preserve append/identify/delete,
rollback and fenced-worker semantics. Add real PostgreSQL/HTTP/worker boundary
tests for 49/50/51, concurrency, replay and tenant/lifecycle/model scope.
14. Decision 10: expose required `max_profiles` in the existing profile page response,
regenerate OpenAPI/types and consume that field in the localized profile capacity
display and enrollment guard. Add HTTP/job error localization and browser scenario
coverage in both locales, with real UI verification using isolated test fixtures.
15. Decision 10: restrict new evaluator galleries to at most 50; retain honest terminal
`profile_limit` outcomes when the full gallery cannot enroll a newcomer, without
discarding completed main-gallery metrics. Test the producer/metrics boundary,
document the capacity target and keep old datasets/evidence unchanged. Run the
focused suites, final full profile gate, security/browser entrypoints and local
deployment/readiness checks. No schema migration, new settings or Spark model build.

16. Decision 11 supersedes the historical capacity work in steps 13–15. Remove
profile-count admission/completion guards and required capacity metadata; retain
tenant locks, idempotency, fencing, quality and sample limits. Red/green real
PostgreSQL tests prove enrollment at 50 and 200, two distinct completions at 49,
and unchanged same-job retry behavior. Regenerate API/types; remove frontend
capacity state/guards and retain localized historical profile_limit errors.
17. Decision 11: remove the evaluator-only 50 limit and admit 200-person manifests
consistently within existing recording/operation resource bounds; preserve old
capacity outcomes and scores. Update current docs and browser scenario; test both
locales against the running application. Record the enrollment failure diagnosis
and primary-source model comparison as exploration, not an implemented accuracy
improvement. Run focused suites and final full-profile/security/browser gates.
