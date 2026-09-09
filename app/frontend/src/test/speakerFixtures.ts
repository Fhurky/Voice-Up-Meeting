import type { SpeakerJob, SpeakerResult, SpeakerProfile } from "@/services/speakers";

export const profileFixture: SpeakerProfile = {
  public_id: "318c1aaa-576a-405c-b391-a8a76a01d3e4", name: "Ada", sample_count: 1,
  model_id: "speechbrain/spkrec-ecapa-voxceleb", model_revision: "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
  created_at: "2026-09-09T10:00:00Z", updated_at: "2026-09-09T10:00:00Z",
};

export const resultFixture: SpeakerResult = {
  decision: "recognized", profile_public_id: profileFixture.public_id, profile_name: "Ada", profile_deleted: false,
  similarity: .84, runner_up_similarity: .53, speech_seconds: 13.5, windows_count: 3,
  model_id: profileFixture.model_id, model_revision: profileFixture.model_revision, device: "cuda:0",
  reason: "matched", policy: { match_threshold: .75, new_threshold: .45, margin: .1 },
};

export const jobFixture: SpeakerJob = {
  public_id: "6d555726-e4d0-48fe-a064-4934fe39c7e8", purpose: "identify", status: "queued",
  recording_public_id: "c0ab36a2-afbc-43b0-976c-11124ad29a4b", created_at: "2026-09-09T10:00:00Z",
  started_at: null, finished_at: null, attempt_count: 0, result: null, error: null,
};
