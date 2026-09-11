import type { Meeting, MeetingSpeaker, MeetingTranscript } from "@/services/meetings";

export const meeting: Meeting = {
  public_id: "d7ef4c2c-5b52-4d11-91c2-bf2c6a64f610", title: "Weekly meeting",
  status: "succeeded", format: "WAV", size_bytes: 100, uploaded_bytes: 100,
  upload_part_bytes: 4194304, next_upload_index: 1, sha256: "a".repeat(64),
  duration_seconds: 60, processed_seconds: 60, completed_chunks: 1, total_chunks: 1,
  language: "tr", participant_count: 5, expected_speakers: null, auto_enroll: true,
  observed_speakers: 1, count_mismatch: false, error_code: null, source_available: true,
  created_at: "2026-09-10T10:00:00Z", started_at: "2026-09-10T10:01:00Z", finished_at: "2026-09-10T10:02:00Z",
};
export const meetingSpeaker: MeetingSpeaker = {
  public_id: "32b625b1-51ab-44da-920c-c6849c7b1fd1", ordinal: 0, display_name: null,
  profile_public_id: null, profile_name: null, profile_deleted: false, decision: "profile_pending",
  reason: "insufficient_speech", speech_seconds: 12, version: 1, profile_updated_at: null,
};
export const transcript: MeetingTranscript = {
  public_id: "f0f7bb41-15d2-4f36-a97a-9a5a1b991211", ordinal: 0,
  speaker_public_id: meetingSpeaker.public_id, speaker_ordinal: 0, speaker_name: null, profile_public_id: null,
  source_participant_id: null, start_seconds: 1.2, end_seconds: 5.8,
  text: "Toplantıya başlayabiliriz.", language: "tr", overlap: false, uncertain: false,
};
