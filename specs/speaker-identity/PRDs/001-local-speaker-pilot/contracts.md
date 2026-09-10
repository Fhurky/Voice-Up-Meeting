# Pilot HTTP contracts

Derived from the Accepted PRD. Public API prefix: `/api/voiceup/v1`.
All resources require JWT, active tenant context and the listed permission.
Errors use `{"detail":{"code":"stable_code","message":"safe explanation"}}`.
UUIDs are opaque strings. Times are UTC ISO-8601. Embeddings never cross public API.

## Public API

- `POST /recordings`, permission `speaker_analysis:run`, multipart field `file`, required
  `Idempotency-Key` (8–128 visible ASCII characters). Returns 201 `RecordingResponse`:
  `{public_id, sha256, size_bytes, format: "WAV"|"FLAC", duration_seconds, created_at}`.
- `POST /speaker-jobs`, permission `speaker_analysis:run`; enroll additionally requires
  `speaker_profiles:write`. Required `Idempotency-Key`. JSON `SpeakerJobCreate`:
  `{recording_public_id, purpose: "enroll"|"identify", name?: string|null, profile_public_id?: string|null}`.
  Enroll requires exactly one nonempty normalized name or existing profile UUID;
  identify forbids both. Returns 202 `SpeakerJobResponse` (also on idempotent replay).
- `GET /speaker-jobs/{public_id}`, permission `speaker_analysis:read`, returns `SpeakerJobResponse`.
- `GET /speaker-jobs?offset=0&limit=20`, same permission, returns `SpeakerJobPage`:
  `{items: SpeakerJobResponse[], total, offset, limit}`; newest first; limit 1–100.
- `GET /speaker-profiles?offset=0&limit=20`, permission `speaker_profiles:read`, returns
  `SpeakerProfilePage`: `{items: SpeakerProfileResponse[], total, offset, limit}`;
  newest first. `total` counts all active profiles in the current tenant, across
  model revisions, independently of page size. There is no profile-count quota.
- `PATCH /speaker-profiles/{public_id}`, permission `speaker_profiles:write`, JSON
  `SpeakerProfileRename` `{name}`; returns `SpeakerProfileResponse`.
- `DELETE /speaker-profiles/{public_id}`, permission `speaker_profiles:write`, returns 204.
- `DELETE /recordings/{public_id}`, permission `speaker_analysis:run`, returns 204;
  active job or profile sample reference returns 409 `recording_in_use`.

`SpeakerProfileResponse`:
`{public_id, name, sample_count, model_id, model_revision, created_at, updated_at}`.

`SpeakerJobResponse`:
`{public_id, purpose, status: "queued"|"running"|"succeeded"|"failed", recording_public_id,
created_at, started_at: string|null, finished_at: string|null, attempt_count,
result: SpeakerResult|null, error: JobError|null}`.

`SpeakerResult`:
`{decision: "enrolled"|"recognized"|"unknown"|"ambiguous", profile_public_id: string|null,
profile_name: string|null, profile_deleted: boolean, similarity: number|null,
runner_up_similarity: number|null, speech_seconds, windows_count, model_id, model_revision,
device, preprocessing_version: "vad-windows-v1"|"vad-packed-fallback-v1"|null,
reason, policy: {match_threshold, new_threshold, margin}}`.
Deleted profiles redact `profile_name`, retain historical ID, and set `profile_deleted: true`.
Old results without preprocessing provenance expose `null`; this field follows
the existing seven-day job retention and does not claim permanent sample provenance.
`JobError`: `{code, message}`. Similarities are raw cosine values, never probabilities.

Fifty speakers is the primary accuracy evaluation target, not a product quota.
New enrollment beyond 50 or 200 is subject to the same quality, authorization,
tenant and idempotency rules as any other enrollment. Existing-profile append
retains the 20-sample limit. The previous `max_profiles` response field was removed
with its only local UI consumer in Decision 11; refresh the UI after deployment.
Historical failed jobs may still expose `error.code: "profile_limit"`; their saved
status is preserved and the safe message describes the former rule. The current
service and worker do not produce this error based on the profile count.

Error codes: `validation_error` (422), `invalid_audio` (400), `unsupported_audio` (415),
`audio_limit` (413), `not_found` (404), `idempotency_conflict` (409),
`recording_expired` (410), `recording_in_use` (409), `sample_limit` (409),
`forbidden` (403). Terminal job codes also include `insufficient_speech`, `inconsistent_audio`,
`clipped_audio`, `target_mismatch`, `profile_unavailable`, `model_mismatch`,
`inference_unavailable`, `job_timeout`, `worker_interrupted`, `recording_unavailable`,
historical `profile_limit`.

## Internal inference API

`GET /ready` returns 200 `{ready: true, model_id, model_revision, dimensions: 192, device}`
or 503 typed error. No download or CPU fallback is allowed at runtime.

`POST /v1/embeddings?purpose=enroll|identify` accepts raw WAV/FLAC bytes (maximum
50 MiB) with `Content-Type: application/octet-stream`, `X-Job-Id: <job UUID>`,
`X-Tenant-Id: <tenant UUID>` and `X-Inference-Key: <internal secret, at least 32 bytes>`.
It returns 200 `{embedding: number[192], speech_seconds, windows_count, model_id,
model_revision, dimensions: 192, device}`. The vector is finite and L2 normalized;
`device` matches `^cuda:[0-9]+$`.
Inference owns 16 kHz mono conversion, VAD, independent 3–8 second windows, clipping,
consistency checks and minimum usable speech (enroll >=10 seconds and >=2 windows;
identify >=3 seconds and >=1 window), with a `1e-6` second tolerance at the minimum
duration boundary in both the producer and consumer. Decode errors return 400/415, size/duration
limits return 413, and quality errors return 422 with the typed envelope.
Unavailable model/device or occupied inference slot returns 503. A single process
serializes inference requests. An optional `quality` object carries producer diagnostics;
its optional `preprocessing_version` must be exactly `vad-windows-v1` or
`vad-packed-fallback-v1`. The guarded recovery path follows Decision 8: original
blocks must be at least 1.5 seconds, independently usable, mutually consistent and
consistent with pooled and any original partial evidence. The profile windows
and minimum durations remain unchanged. The public result contains only the
fields listed above; arbitrary diagnostics are not forwarded.
