# Plan — local-speaker-pilot

Status: Implementation delivered; external validation incomplete

Authority: [Accepted PRD](PRD.md), accepted 8 September 2026. Evidence: [tasks.md](tasks.md).

1. Prepare the isolated VoiceUp runtime on port 8081, preserving other applications. Verify admitted package/image sources, PostgreSQL 17 with pgvector and separate Python 3.13 CUDA inference. Package pinned ECAPA for offline runtime; explicit readiness/device errors precede inference.
2. Implement tenant-scoped SQLAlchemy recordings/profiles/samples/jobs, reviewed Alembic migration, typed HTTP inference port, permissions and bounded uploads (requirements 1–8). Include exact ranking over all eligible profiles, guarded enrollment, idempotency, leases with fencing, two-attempt retry and reference-aware cleanup.
3. Add localized profile, analysis and resumable job pages using existing authentication and generated OpenAPI types. Display unknown/ambiguous outcomes and raw similarity honestly; identification never enrolls.
4. Verify with unit and real PostgreSQL tests for isolation, duplicate submission, transactions, deletion, stale workers and wrong-person append. Regenerate API/types and synchronize configuration/charts. Exercise actual browser/API and genuine GPU inference; run the full quality gate and record all failures.
5. Measure GPU performance separately from identity quality. The20-job real4060 experiment is now complete (p95execution0.868519s); the5-person cross-session dataset remains unavailable. Repeated public speech can satisfy the technical timing protocol, but cannot establish recognition accuracy. See tasks.md and the evidence report for external validation still missing.

6. Prepare T09 data with `scripts/validate-speaker-dataset.py`, the pseudonymous manifest template and `docs/DATA_COLLECTION.md`. Check real files, phase roles, cross-session/source separation, duplicates and pilot upload limits without running inference. A ready dataset is not an accuracy result; the API evaluation runner and representative recordings remain required.

Ownership: backend agent owns backend/domain/schema and tests; frontend agent owns frontend workflow/tests; inference agent owns inference service/package/tests; main agent owns integration, dependency/runtime preparation, deployment surfaces and final evidence. API/inference contracts are shared before dependent implementation.

Earlier observations: [4060 foundation note](../../../../plans/RTX_4060_FOUNDATION.md).
