# Implementation plan — meeting transcription and persistent speakers

Source: [Accepted PRD](PRD.md), updated by the user's 2026-09-10 workflow request
and subsequent fragmented Teams speech/local RTX 4060 decision. The latest user
source choice is uploaded recordings; microphone capture moved to Accepted
[007](../007-microphone-meeting-capture/PRD.md). Count input, manual names and the
five-return/sixth-new-person workflow are part of the current 002 delivery.
Profile: `kt-vibecoding-python-web-v2`. This plan is not implementation evidence.

Decisions 19–20 follow the owner's 2026-09-11 accuracy audit request. First freeze
the existing A/B/C reference protocol and identify unused public speakers without
model-based selection. Add bounded, reusable transcription metrics in
`src/voiceup/meeting_metrics.py` and a file-based evaluation script with immutable
source hashes; independently compare small exact-permutation examples and test
50-stream assignment, missing/extra speakers and retained unassigned words.
This research tool adds no runtime dependency, network call, schema or public API.

Audit outcome, recorded separately from planning: Decisions 19–24 are implemented
and the frozen local full gate plus real memory/restart flows passed. The
[evidence report](../../../../docs/evidence/2026-09-11-accuracy-audit/README.md)
records the first fifty-person cpWER improvement, unchanged clean persistent
samples, all 190 controlled clip extractions and correlated nested-gallery
scores. Two ASR candidates, two extra reconciliation heuristics and one bounded
whole-recording Community call were rejected rather than applied after their
predefined regressions failed. The last candidate reduced minority-source time
but increased splitting and complete-reference word errors; it does not justify
a production whole-file API or a threshold change. This audit does not complete
the separate representative-language, fifty-person end-to-end or device/release
acceptance criteria.

Task T19's frozen [corpus protocol](corpus-protocol.md) is implemented by
`scripts/prepare-meeting-identity-evaluation.py` and filesystem-bound tests in
`tests/test_prepare_meeting_identity_evaluation.py`. Reuse the existing admitted
NumPy/SoundFile preparation environment; do not download or run models. Record
selection and source/reference hashes before any evaluator consumes the corpus.
Verify exclusion, chapter independence, deterministic duration-bounded whole
utterances, immutable output, altered-source rejection and failure preservation.

Correct meeting-only centroid accumulation in `domain/meeting_centroid.py` and
`services/meeting_chunks.py`. Store validated per-population resultant magnitude,
evidence weight and legacy provenance in existing private `props`, atomically
with vectors and unique source ranges; no schema migration is necessary. Add
red/green order/permutation and missing-vector-weight regressions plus real
PostgreSQL round-trip, retry and legacy adoption coverage. Replay preserved
provider results before new model runs, then exercise the changed worker through
the real uploaded-recording flow. Keep permanent samples immutable and existing
thresholds unchanged. Record all failed experiments and actual regression counts.

The private `embedding_resultant` and `tracking_resultant` records each contain
exactly `version`, `weight`, `norm` and `origin`. Version 1 records accept only
positive finite magnitude and vector-present unique-source weight, bounded by
the recorded population duration; present malformed state fails the transaction.
Missing legacy state adopts one explicitly marked historical pseudoobservation
only when a real new contribution arrives. A zero contribution preserves the
stored float32 vector and existing metadata exactly. Persisted-vector comparisons
use a numerical tolerance, not a claim of bit-identical permutation invariance.
The Decision 19 [narrow evidence report](../../../../docs/evidence/2026-09-11-accuracy-audit/resultant-report.md)
records unit and PostgreSQL regressions plus an old/new replay of preserved model
outputs; new real-model evaluation and the full gate remain separate evidence.

Investigate same-model ASR decoding against frozen reference text and timing
diagnostics before selecting another production recipe. Do not treat standard VAD
activation as a new candidate: the previous eight GPU comparisons removed no
audio and did not improve words. Record selected behavior in the PRD before
implementation. Run the full fixed-profile gate and applicable security checks
after final edits; unsupported Turkish/50-person/device evidence stays explicit.

Decision 21 adds private, bounded per-population decision provenance in the
meeting memory transaction, with a pure helper and unit/real PostgreSQL tests.
Preserve exact existing fusion output; include no profile identifiers or raw
vectors, and do not backfill historical decisions. Verify public serialization,
idempotency and cleanup. Existing JSON props suffice; schema and public contracts
are unchanged. Capture the 50-person return result with explicit recipe/code
provenance and separate end-to-end coverage from conditional identification.

Decision 22 scopes model residency to the existing exclusive memory request.
Implement the local adapter context and runtime wiring with error/precision/
lock lifecycle regressions before implementation. Keep single-example inference
and window order. Compare admitted-model old/new output and latency on frozen
clean/mixed/threshold-near controls before rebuilding through the existing
offline setup wrapper; never change the currently running experiment's image.

Decision 23 preserves source-native speaker separation across both meeting
reconciliation and persistent identity assignment only with independent usable
ECAPA192 pair evidence below the existing 0.45 new-person bound. The earlier
unconditional native-label constraint failed V8 A (5 to 11) and C (6 to 8) and
must remain a rejected experiment. First replay the fixed V8
and fifty-person A provider checkpoints with existing mapping reproduced before
the candidate rule. Retain every failed result. Add a bounded versioned domain
record for per-core native label/model provenance in existing private props;
reject malformed records and keep absent legacy evidence explicitly absent.
Prevent independently proven different native voices from consuming one global
winner, including source-context reconnection. Missing or ambiguous second-model
evidence does not establish a cannot-link. Keep full-population ambiguity checks.
Use the same qualified shared-core evidence in the existing memory conflict check,
preserve both records' uncertainty and all existing immutable samples, and bind
the evidence into snapshot validation. No schema or public API expansion is
needed: the private peer document is a bounded derived checkpoint-evidence cache,
not a new entity lifecycle or SQL relationship lookup. Name cached references
`meeting_speaker_id`; enforce same-tenant/meeting, symmetry and live peer presence
on use, and scrub with the owning meeting result. Existing relational ownership
foreign keys remain authoritative. Add real PostgreSQL/worker/HTTP regressions for separate sequential
voices, context reconnection, cross-chunk reuse, memory conflicts, retry,
malformed evidence and cleanup. Verify the changed production flow in a new
isolated gallery before return meetings; inspect every retained sample, not
only source-qualified identity bindings. Do not infer model accuracy from the
checkpoint replay or fixture-vector tests.

Decision 24 extends the final retained-PCM secondary-voice veto to an independent
192-dimensional ECAPA evaluation while preserving the existing 256-dimensional
decision. Freeze all 85 old/new source controls and retain failed candidates.
Parameterize the existing pure coherence helper only for admitted dimensions
192/256; preserve window selection, VAD, content deduplication, support and
deterministic clustering. Run the ECAPA veto only after the existing veto allows
the sample, before any final retained output is returned. Add red/green tests
for disagreeing populations, no cross-space mixing, fail-closed encoder errors,
unchanged pure samples and absent outputs on rejection. Validate every fixed
control through production code, the actual unsafe memory request, and paired
GPU latency/memory. No new model, dependency, schema, setting or public contract
is required. Rebuild the selected runtime through the existing offline wrapper
only after the candidate meets its frozen clean/mixed acceptance conditions.

Decision 12 follow-up, derived from the frozen real A failure: add an explicitly
tagged, normalized 256-dimensional Community embedding to the private provider
track contract, with source-observed label ordering and immutable component
identity. Add nullable dedicated meeting-speaker vector/model/revision columns
through a second additive migration; preserve the existing ECAPA192 population.
Use the tracking centroid for meeting-local matching and source-context
compatibility, retaining exact source ownership and overlap exclusions. Weight
updates by unique owned speech, not repeated context. Legacy checkpoints without
the new component keep the existing conservative fallback. Clear the component
with expired meeting results. Test model/dimension mismatches, same/different
local tracks with insufficient enrollment evidence, isolation, cleanup and
checkpoint retry at real PostgreSQL boundaries; regenerate contracts if any
public shape changes. Rerun the unchanged real A/B/D/C protocol and the full gate;
do not claim that better tracking alone completes memory quality.

Existing patterns inspected: `src/voiceup/backends.py` has a research Community-1
adapter and `src/voiceup/pipeline.py` has clean-evidence and overlap-aware identity
logic. Neither is the deployed web pipeline; the research loader downloads at
load time and its SQLite registry is not a product persistence substitute. Reuse
verified algorithmic behavior only through the accepted offline provider and
PostgreSQL application boundaries. See [discovery evidence](../../../../docs/evidence/2026-09-10-meeting-workflow/README.md).

1. Decisions 2, 9 / Open Questions 1, 3: verify authorized Community-1 access and retrieve
   the exact selected provider configuration and model artifacts through an
   explicit build-time provisioner. Record official license/release metadata,
   SHA-256 inventory, Python 3.13/ARM64/CUDA dependency closure, decoder support
   and native compatibility before changing the admitted runtime. Keep existing
   ECAPA and model populations intact; never expose token values.
   Add `scripts/prepare-diarization-model.py` and a reviewed
   `scripts/diarization-model-manifest.json`, following the existing speaker model
   preparation pattern. Use real temporary filesystem tests in
   `tests/test_prepare_diarization_model.py` for fixed revisions, safe paths,
   exact sizes/hashes, incomplete/corrupt packages, offline reuse and secret-safe
   failures. Tokens are setup-only inputs; do not place them in manifests,
   downloaded configurations, URLs, logs or inference runtime environments.
   Publish a completed package only after the selected inventory is verified.
   A successful model preparation step does not admit new dependency pins.
   The ASR artifact is `Systran/faster-whisper-large-v3` at
   `edaa852ec7e145841d8ffdb056a99866b5f0a478`, with independently admitted
   `faster-whisper 1.2.1` / `ctranslate2 4.8.1` dependencies. Preserve the earlier
   upstream Whisper revision as provenance only. Freeze artifact hashes,
   MIT model card/license and offline runtime loading before activation; do not
   alter dependency authorities merely to make the candidate install.
   Implement `scripts/prepare-asr-model.py`, `scripts/asr-model-manifest.json`
   and `tests/test_prepare_asr_model.py` using the verified Community-1 package
   publication pattern. This public artifact requires no token read or bearer
   forwarding. Test exact inventory, bounded streaming, incomplete/corrupt
   preservation and offline reuse before retrieving the real model package.
2. Decisions 2–6, 8–10 / Requirements 3–5, 8: exercise the real provider on bounded public
   audio, including a speaker change and overlap. Freeze `contracts.md` against
   observed input/output shapes, error codes, time units, channels, model identity,
   word/turn alignment and clean enrollment evidence. Include source participant,
   acoustic track and persistent profile as independent identities, plus source
   clock/sample ranges, discontinuities and nullable identity information. An
   explicitly selected Python 3.13/local RTX 4060 provider can establish local
   development evidence; record Spark ARM64 evidence independently. A separate
   Python 3.12 CPU research probe cannot certify either application runtime.
   This precedes creating a
   mock-backed vertical that could only agree with an invented provider shape.
   The 2026-09-10 real Community-1 probe returned end=18.96471875 for an
   18.8-second source. Protect source-time intersection in the existing research
   `src/voiceup/backends.py` adapter and `tests/test_backends.py`, preserving
   invalid non-finite/reversed interval failures. This bounded regression does
   not install the provider into the application or complete the ASR contract.
   Freeze optional participant-count upper bound separately from an exact
   actually-speaking count. Observe model behavior with no hints and supported
   global hints; do not force a meeting-wide exact count into every chunk.
   Record mismatch semantics without inventing merges to satisfy the requested count.
   Exercise ASR batch 1, CUDA `int8_float16` and CPU `int8` independently, using
   native 30-second transcription windows inside a source-bounded <=310-second
   provider request. Run diarization and ASR stages sequentially on the GPU.
   Word timestamps and speaker/text alignment remain unverified until the real
   provider emits the frozen output contract.
3. Requirements 2–10: add meeting schema authority under
   `app/backend/app/domain/models/`, register models, and generate an additive
   Alembic migration in `schema/alembic/versions/`. Cover tenant-qualified
   references, lifecycle, upload idempotency, fenced chunks and unique enrollment
   provenance, count settings, meeting-local display names and stable profile
   references with a disposable real PostgreSQL database. Do not alter the
   meaning of existing `SpeakerJob.purpose` or make sample provenance nullable.
4. Requirements 2–4: implement a bounded meeting file adapter, repository,
   typed provider port, orchestration service and scheduled/on-demand worker.
   Preserve source channels, optional platform participant/source identifiers,
   original time ranges, gaps, reconnects, upload hashes, checkpoints and safe cancellation;
   connect private Spark transfer/analyze endpoints using the existing HTTP and
   authentication architecture. Both Spark proxy allowlists must change together.
   Check the pinned private meeting readiness before claiming queued work in the
   production worker composition. Bound the authenticated HTTP probe to five
   seconds and 16 KiB, preserve pilot/cleanup/heartbeat execution, and exercise
   connection refusal, transient 503, recovery and real post-admission inference
   failure against persisted attempt/fencing state. Keep this admission concern
   outside the core provider protocol so existing service adapters remain valid.
5. Decisions 6, 8, 10–11 / Requirements 5–10: implement timeline ownership and meeting speaker identity
   reconciliation. Reuse `speaker_identity` domain decisions and repository
   exact cosine search, then atomically recheck the gallery under the tenant lock
   before eligible unknown enrollment. Persist a real short Recording and
   enrollment SpeakerJob/SpeakerSample; test retries and simultaneous meetings.
   Accumulate the union of distinct clean, non-overlapping sample ranges assigned
   confidently to the same meeting acoustic track. Require strictly more than
   20 seconds for meeting automatic enrollment; exactly 20 seconds remains
   `profile_pending`. Duration never bypasses consistency, quality or unknown
   decisions. Keep short-speaker transcript output and independent source
   attribution even when a persistent voice profile is unavailable. Do not infer
   biometric identity from a display name or force a short turn to the nearest
   known profile. Repeated context, retry, overlap and gaps cannot add evidence.
   Preserve 001 API thresholds and read-only identification semantics.
   Preserve a frozen source-frame manifest when selecting the deterministic
   first at most 60 seconds of a meeting sample. Keep the original rate, source
   frame bounds and selected disjoint source ranges alongside the bounded WAV
   bytes and their SHA-256. A pure domain mapper translates verified 16 kHz
   integer-frame ranges back through the packed sample to original source
   ranges using inward integer ceil/floor. Reject malformed, duplicated,
   overlapping or out-of-bounds manifests/provider intervals. Existing sample
   callers retain source union, bounded selection and byte output behavior.
   This provenance helper does not admit a new quality gate or processing
   lineage. Verify mapping, gap ownership, exact 20-second duration, truncation
   and malformed boundaries with pure tests and real WAV/FLAC filesystem tests.
   Reconcile chunk identities with acoustic evidence instead of blind nearest-pair
   merging. Persist manual names without altering embeddings or stable profile
   IDs; pending names remain meeting-local until eligible enrollment. Duplicate
   names do not merge identities, and concurrent edits return an explicit conflict
   or current-version result. Recheck names/identities after refresh and restart.
6. Requirements 2, 5–10: implement typed meeting API and permission dependencies,
   export OpenAPI offline and generate frontend API types. Add meeting read/run
   permissions and verify the additional profile-write guard for automatic memory
   and canonical profile naming. Test count validation and idempotency conflicts
   when the same key arrives with changed analysis settings. No meeting endpoint
   can rename or read another tenant's profile.
7. Requirements 1, 5, 8–9 / Decisions 3, 5, 10–11: implement meeting
   list/source/detail routes with a bounded file upload queue through the shared
   API client. Use at most 4 MiB `File.slice` chunks, per-chunk SHA-256 and ordered
   acknowledgements for byte progress; never load the whole recording into browser
   memory. After refresh, require source reselection and match accepted server
   hashes before resuming. Add paginated transcript/speaker lists, optional count
   inputs and mismatch display, manual names, route/menu permissions and both flat
   locale catalogs. Test final chunk, cancellation, conflict, refresh and errors.
   Show `profile_pending` separately from a saved person and from analysis failure;
   a short utterance remains visible with its meeting speaker label. Explain a
   pending meeting name separately from a persistent profile name. Microphone UI
   belongs to 007 and is not a condition for the uploaded-recording flow.
8. Decision 7: implement reference-aware meeting cleanup, bounded temporary Spark
   staging and distinct source/transcript/profile deletion behavior. Test that
   one persisted short profile sample never retains an entire meeting recording.
9. Decision 9 / Deployment section: wire settings, environment examples, Compose, Helm,
   storage, decoder/model inventory, resource requests and readiness. Extend
   existing provision/start wrappers; normal cable/startup must remain offline.
   Keep explicit local RTX 4060 and Spark provider selection; do not silently
   fall back when Spark is disconnected or change the Python 3.13/FastAPI profile.
   For explicitly enabled Local meeting mode, withhold the ready URL until the
   private `/meeting-ready` endpoint confirms CUDA and all three pinned model
   identities. Probe from inside the inference container using its existing key,
   with a bounded startup deadline, bounded response and secret-safe failures.
   Test delayed readiness, wrong model/device/shape, terminal failure and intact
   standalone Local/Spark behavior using native Windows PowerShell 5.1 processes.
   A successful shell-wrapper restart of backend/frontend or all services must
   validate and reload the existing active Nginx configuration in the same mode.
   Preserve the exact Spark private configuration and reject ambiguous/symlink
   paths; unrelated commands and failed restarts must not reload. Exercise the
   shell wrapper with an inert Docker boundary and real isolated stale-IP recovery.
   Teams transport is not implemented here; 003 remains Draft, and the .NET
   requirement of Teams raw media does not authorize another backend in this repo.
10. Requirement 10 / Acceptance criteria: test the explicitly selected local
    provider over real HTTP/browser with independent
    public speech and repeat participants, both locales and ordinary permissions.
    Commit scenarios in `e2e/speaker-identity/`, update `QUALITY_MANIFEST.md`, and
    run 1/2/4-hour resource/resume tests separately from model accuracy claims.
    Add strict 20-second boundary, separated short-turn accumulation, mixed
    evidence over 20 seconds, duplicate context, late chunks, source-name
    collisions and short-speaker transcript regression cases. Add A: five people
    create five profiles and receive manual names; B: different recordings of
    those same people resolve to the same five IDs/names; C: a sixth independent
    speaker creates exactly one new profile. Repeat jobs and restart services;
    assert 5/5/6 active profile totals and stable existing identities. Include a
    short sixth person remaining pending and a five-person meeting chunk with
    fewer actual voices. Drive ordinary-role TR/EN browser flows. Local RTX 4060
    observations do not replace the required Spark or 50-speaker measurements.
11. Handoff: run narrow suites and `scripts/quality-gate.sh all`, schema validation,
    configuration sync, chart/security and the admitted browser entrypoint. Record
    every failure/skip and the highest observed tier using `53-test-run-report.md`.
    Representative Turkish quality and owner acceptance remain distinct from a
    successful synthetic or public technical integration flow.

    Use `scripts/prepare-meeting-evaluation.py` to assemble deterministic local
    fixtures from the already prepared calibration manifest: the first six
    recorded gallery identities, disjoint enrollment/query utterances, bounded
    round-robin excerpts, a short unknown sixth person before full enrollment,
    and immutable input hashes/source intervals. Do not choose speakers using
    current model outcomes or publish audio. The script prepares evidence only;
    it does not make a model-accuracy claim or modify application profiles.

Current delivery ownership: 002 owns uploaded recording → speaker/text → manual
name → persistent identity and five-return/sixth-new-person behavior. The earlier
microphone capture requirement remains Accepted and incomplete in 007; automatic
Teams capture is not requested for this delivery. Actual provider/ASR contracts
must be observed and frozen before transport/UI code claims full completion.

Initial discovery: the prepared Spark inference container had neither the
selected diarization/transcription dependencies nor these model bundles. The
Community-1 repository is gated; the user was asked to grant model read access
through `HF_TOKEN` in the ignored root `.env`, without sharing it in chat. No
provider-dependent implementation or live feature completion was claimed then.

2026-09-10 access update: the user's local token returned HTTP 200 for the fixed
Community-1 revision configuration. This resolves the authenticated-access
prerequisite, not the complete package, dependency admission or provider output
contract. The subsequent offline package passed 8/8 artifact checks and 78 tests
on each of Windows and Linux. Local RTX 4060 is the
explicitly selected development target; product and Spark readiness stay separate.

The real local GPU probe completed 12 inputs using Linux Python 3.13.14,
Torch 2.8.0+cu128 and the selected Community-1 revision. Its temporary offline
research dependency prefix added 62 hash-verified packages from the existing
research lock while preserving all 63 base pins. Actual wheel metadata and
`pip check` passed; no dependency authority or running application was changed.
The input was predecoded PCM; FFmpeg/WebM/TorchCodec decoder readiness and
production dependency admission are still unproven. The small diagnostic set
also exposed a single-speaker split and transition confusion, so automatic
enrollment and 50-person quality are not certified by this probe.

A separate compatibility gap was found: pyannote.audio 4.0.7 requires
TorchCodec >=0.7; the TorchCodec 0.7 line matches the existing Torch 2.8 but the
inspected official package indexes did not provide Linux aarch64/cp313 wheels.
T02 must review a native source build or a separately admitted compatible runtime
before claiming Spark readiness; access to model weights alone does not solve this. Do not
skip dependencies or rewrite the existing offline lock to force installation.

Decision 13 implementation maps to the existing meeting application port,
inference adapter, candidate checkpoint fields, source-frame manifest, fenced
memory transaction and SpeakerProfile schema authority. Add nullable 256-vector
population metadata and a reviewed additive migration; preserve the 192-vector
population and explicit new processing lineage. Verify final retained audio
hashes, accepted context indices, original voiced frame subsets, three distinct
contexts and strict >20-second enrollment. Keep model rejection fail-closed and
known profiles immutable. Regenerate OpenAPI/types for the new trace lineage and
test both legacy and current populations with real tenant-scoped PostgreSQL.

T12 implementation details: `meeting_memory_ports.py` freezes native PCM frame
coordinates and exact model metadata; `meeting_memory_inference.py` transports
bounded JSON with no fallback. `meeting_memory_samples.py` keeps natural source
contexts, maps accepted voiced subsets and independently checks distinct PCM
hashes. `MeetingMemory` snapshots and fingerprints candidate evidence, performs
quality work outside the tenant transaction, then rechecks the live fence,
authorization, source, evidence and both model populations before one atomic
Recording/Profile/Sample/Job write. The additive profile authority and migration
`9cf5f2d22daf` attach the nullable 256-dimensional population to a same-tenant
Recording while preserving all existing profile IDs and 192-dimensional fields.
The separate worker composes both the legacy and meeting-only ports. Tests in
`test_meeting_context_memory.py` exercise actual HTTP uploads, owned files and
migrated disposable PostgreSQL; transport/schema tests pin malformed, missing,
oversized and source-mismatched responses. These fixture-vector tests establish
transaction and provenance behavior, not model accuracy.

Decision 14 changes core/context bounds together: 300-second cores and maximum
310-second private windows, source byte limits, transport/schema validators and
worker checkpoint tests. Keep memory samples <=60 seconds. The independent full
182-second A observation justifies exploration of the larger bounded context;
Persist `props.window_core_seconds=300` at creation; missing legacy metadata
selects the original 60-second cores in both public progress and worker claims.
Preserve the historical 0–239 checkpoint index domain. Widen its database check
through an additive migration rather than rewriting an applied revision. Test
new and legacy retry/restart with exact source ownership, then
repeat the real 310-second GPU and 1/2/4-hour filesystem/resource checks before
claiming the new bounds verified. Preserve all earlier failed A and quality
control runs. Final acceptance remains the unchanged A/B/D/C sources and normal
user API/browser flow, followed by the complete fixed-profile quality gate.

Both Spark proxy allowlists retain exact GET `/meeting-ready`, widen only POST
`/v1/meeting-chunks` to 120 MiB, and add exact POST `/v1/meeting-memory` with a
36 MiB JSON body limit. Preserve forwarded internal/job/tenant headers, bounded
timeouts, disabled buffering/retries and no public listener exposure. Update the
private-template origin replacement count and the prepared Spark starter's
reviewed static template hash together.
Keep runtime tamper rejection before Docker and retain the unchanged Compose and
image identities; do not self-admit a runtime template or rewrite remote files.
Exercise both actual nginx configurations with disposable transport fixtures;
this cannot certify ARM64
models or meeting-memory quality. Regenerate OpenAPI/frontend types for the
accepted `meeting-natural-context-v1` trace literal and run frontend checks.

Decision 15 backend work keeps the existing acoustic matching policy and adds
the exact optional private VAD identity/range contract in `meeting_ports.py`.
New VAD-bearing results require the recorded diarization recipe. In
`meeting_chunks.py`, finish all native-label mappings before converting raw
turns and VAD intervals inward into original source frames. The pure
`domain/meeting_candidates.py` helper uses mapped speaker IDs, retains raw
native overlap and competing/unmapped turns as barriers, and emits only
unqualified 3–8-second contexts. Preserve source-core ownership, the existing
quarter-second tail guard, explicit empty new-route lists and the first 256
chronological nonoverlapping contexts. Legacy provider candidates remain only
for VAD-absent historical results. No schema/public API change is needed.
Verify strict identity/recipe/order/source rejection, pure interval behavior,
and actual worker/HTTP/PostgreSQL wiring at 8 and 44.1 kHz. These tests prove
the boundary, not provider accuracy; frozen A/B/D/C and mixed-source controls
remain separate acceptance evidence under Decisions 15–16.

Decision 15 applies the immutable `community-vbx-fa015-v1` recipe in the local
model constructor and returns that provenance in the private model identity.
Transport validated Silero source VAD ranges separately from already qualified
voice; build natural candidates only after the existing application acoustic
mapping has completed. Protect adjacent short native fragments, unmapped rivals,
raw overlap, source-frame ownership, old checkpoints and bounded manifests.

Decision 16 adds an independent, deterministic two-center coherence veto on the
final retained PCM before either persistent embedding is produced. Its 2-second
probes, unique content, nonoverlap support and existing 0.55/0.10 identity bounds
must match the frozen research recipe. Preserve the failed 0.45 experiment;
repeat all 48 source-hash-bound controls through the production implementation,
including the two actual previously unsafe retained samples. Check the narrow
critical-case margin on the real GPU. Then rebuild through the existing offline
setup wrapper, restart the selected local stack, and run unchanged A/B/D/C with
ordinary tenant permissions, real names, real service restart and idempotency.

Decision 18 corrects source-time attribution in the pure meeting timeline
domain. Add regression coverage for a stretched ASR token spanning sequential
speakers, a clearly dominant boundary word, preserved simultaneous overlap,
and a missing-word gap that contains a different speaker. Keep every observed
token and expose ambiguous ownership rather than assigning by exclusive
majority. Replay the unchanged four-recording protocol in a new empty tenant;
retain the earlier six-profile but failed transcript acceptance result.

Decision 17 closes the deployment surface without claiming native ARM64 meeting
support. Extend the inference chart with existing typed runtime-profile settings
and an explicit meeting flag, defaulting to the current pilot behavior. Keep one
pre-created Secret reference; enable Linux/amd64 scheduling, readonly model PVC
subpaths and meeting startup/readiness only for the admitted x86_64 CUDA profile.
Reuse the image-baked immutable manifests and existing 50 MiB/120-second pilot
limits. The meeting API already owns its separate request/decode bounds.

Add the same `inference.runtimeProfile` and `inference.meetingEnabled` selection
shape to both real and both fixture overlays without resolving real environment
placeholders. The renderer maps those values, validates rendered runtime/model
mount/probe contracts, and rejects unsupported enabled ARM64 or unsafe mutated
workloads. Develop off/on/ARM64-negative Helm cases before implementation, then
run render/self-test, configuration sync and the complete fixed-profile gate.
Document offline model PVC population and image selection in the deployment
guide; model files and secret values do not enter Helm values or Git.
