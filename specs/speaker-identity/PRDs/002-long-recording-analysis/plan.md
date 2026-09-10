# Implementation plan — meeting transcription and persistent speakers

Source: [Accepted PRD](PRD.md), updated by the user's 2026-09-10 workflow request.
Profile: `kt-vibecoding-python-web-v2`. This plan is not implementation evidence.

Existing patterns inspected: `src/voiceup/backends.py` has a research Community-1
adapter and `src/voiceup/pipeline.py` has clean-evidence and overlap-aware identity
logic. Neither is the deployed web pipeline; the research loader downloads at
load time and its SQLite registry is not a product persistence substitute. Reuse
verified algorithmic behavior only through the accepted offline provider and
PostgreSQL application boundaries. See [discovery evidence](../../../../docs/evidence/2026-09-10-meeting-workflow/README.md).

1. Decision 2 / Open Question 1: verify authorized Community-1 access and retrieve
   the exact selected provider configuration and model artifacts through an
   explicit build-time provisioner. Record official license/release metadata,
   SHA-256 inventory, Python 3.13/ARM64/CUDA dependency closure, decoder support
   and native compatibility before changing the admitted runtime. Keep existing
   ECAPA and model populations intact; never expose token values.
2. Decisions 2–5 / Requirements 3–5: exercise the real provider on bounded public
   audio, including a speaker change and overlap. Freeze `contracts.md` against
   observed input/output shapes, error codes, time units, channels, model identity,
   word/turn alignment and clean enrollment evidence. This precedes creating a
   mock-backed vertical that could only agree with an invented provider shape.
3. Requirements 2–7: add meeting schema authority under
   `app/backend/app/domain/models/`, register models, and generate an additive
   Alembic migration in `schema/alembic/versions/`. Cover tenant-qualified
   references, lifecycle, upload idempotency, fenced chunks and unique enrollment
   provenance with a disposable real PostgreSQL database. Do not alter the
   meaning of existing `SpeakerJob.purpose` or make sample provenance nullable.
4. Requirements 2–4: implement a bounded meeting file adapter, repository,
   typed provider port, orchestration service and scheduled/on-demand worker.
   Preserve source channels, upload hashes, checkpoints and safe cancellation;
   connect private Spark transfer/analyze endpoints using the existing HTTP and
   authentication architecture. Both Spark proxy allowlists must change together.
5. Requirements 5–7: implement timeline ownership and meeting speaker identity
   reconciliation. Reuse `speaker_identity` domain decisions and repository
   exact cosine search, then atomically recheck the gallery under the tenant lock
   before eligible unknown enrollment. Persist a real short Recording and
   enrollment SpeakerJob/SpeakerSample; test retries and simultaneous meetings.
6. Requirements 2, 5–7: implement typed meeting API and permission dependencies,
   export OpenAPI offline and generate frontend API types. Add meeting read/run
   permissions and verify the additional profile-write guard for automatic memory.
7. Requirement 1 / Decisions 3, 5: implement meeting list/source/detail/transcript
   pages, a microphone lifecycle hook and bounded upload queue through the shared
   API client. Use native browser recording only with an admitted server codec;
   stop explicitly on unsupported capture or upload backpressure. Add menu/routes,
   both locales and tests for late permission, final chunk, cancellation and errors.
8. Decision 7: implement reference-aware meeting cleanup, bounded temporary Spark
   staging and distinct source/transcript/profile deletion behavior. Test that
   one persisted short profile sample never retains an entire meeting recording.
9. Deployment section: wire settings, environment examples, Compose, Helm,
   storage, decoder/model inventory, resource requests and readiness. Extend
   existing provision/start wrappers; normal cable/startup must remain offline.
10. Acceptance criteria: test the real Spark/HTTP/browser workflow with independent
    public speech and repeat participants, both locales and ordinary permissions.
    Commit scenarios in `e2e/speaker-identity/`, update `QUALITY_MANIFEST.md`, and
    run 1/2/4-hour resource/resume tests separately from model accuracy claims.
11. Handoff: run narrow suites and `scripts/quality-gate.sh all`, schema validation,
    configuration sync, chart/security and the admitted browser entrypoint. Record
    every failure/skip and the highest observed tier using `53-test-run-report.md`.
    Representative Turkish quality and owner acceptance remain distinct from a
    successful synthetic or public technical integration flow.

Current discovered gap: the prepared Spark inference container has neither the
selected diarization/transcription dependencies nor these model bundles. The
Community-1 repository is gated; the user was asked to grant model read access
through `HF_TOKEN` in the ignored root `.env`, without sharing it in chat. No
provider-dependent implementation or live feature completion is claimed yet.

A separate compatibility gap was found: pyannote.audio 4.0.7 requires
TorchCodec >=0.7; the TorchCodec 0.7 line matches the existing Torch 2.8 but the
inspected official package indexes did not provide Linux aarch64/cp313 wheels.
T02 must review a native source build or a separately admitted compatible runtime
before proceeding; access to model weights alone does not solve this. Do not
skip dependencies or rewrite the existing offline lock to force installation.
