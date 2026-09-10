# Tasks — meeting transcription and persistent speakers

Source: [PRD](PRD.md) and [plan](plan.md). Profile: `kt-vibecoding-python-web-v2`.

- [x] T01 Record the user's file/microphone → speaker transcript → new-speaker memory workflow, its separation from 001/003, model roles and the real missing runtime/access prerequisites; output: PRD, plan, roadmap and `docs/MEETING_WORKFLOW.md`. Evidence: local source inspection and official model metadata, not executable feature evidence.
- [ ] T02 Verify authorized Community-1 access; record exact model configuration/license/hash inventory and independently reviewed dependency/decoder admission. Output: reproducible offline provisioner/manifests and native Spark compatibility report.
- [ ] T03 Exercise real diarization/transcription on a small public recording with multiple speakers; freeze provider/API contract and alignment policy. Output: `contracts.md` plus source-bound real provider evidence and negative cases.
- [ ] T04 Add tenant-scoped meeting schema and additive migration. Evidence: real PostgreSQL integrity, lifecycle, migration desired-state/history/drift tests.
- [ ] T05 Implement bounded source upload/storage, chunk checkpoint/worker, private Spark port and both proxy allowlists. Evidence: real disk/HTTP retry, interruption, fencing, size, duration, channel and cancellation tests.
- [ ] T06 Implement transcript ownership, speaker reconciliation and idempotent automatic enrollment with short retained samples. Evidence: known/new/ambiguous/overlap/short cases, two-meeting return and concurrent enrollment tests.
- [ ] T07 Implement typed public API and permissions, export OpenAPI and generate client types. Evidence: normal-user authorization, tenant isolation and committed-contract drift checks.
- [ ] T08 Implement localized meeting/source/detail UI and microphone lifecycle with bounded streaming upload. Evidence: frontend tests and real file/microphone flows in TR/EN; no fake capture or token injection counted as live evidence.
- [ ] T09 Wire retention, cleanup, settings, offline startup and deployment. Evidence: source/short-profile retention separation, configuration sync, readiness and chart checks.
- [ ] T10 Run real Spark multi-speaker transcript and newcomer-return tests, permanent browser scenario and 1/2/4-hour resource/resume cases; record model accuracy separately.
- [ ] T11 Run complete profile/security/browser gates and publish a fixed-format local report listing every unsupported tier; representative Turkish L3 acceptance remains explicit.

Current blockers: T02 model-owner access conditions and a corresponding local read
token are pending; TorchCodec/native ARM64 dependency admission also remains open.
T03 depends on the selected real provider; its output contract
must not be invented and then certified by mocks. T04–T11 remain incomplete,
not removed from the accepted capability. The existing pilot remains functional.
