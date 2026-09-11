import { ApiError } from "@/lib/apiClient";

const codes = new Set([
  "validation_error", "invalid_audio", "unsupported_audio", "audio_limit", "not_found", "forbidden",
  "idempotency_conflict", "recording_expired", "recording_unavailable", "upload_limit", "storage_limit",
  "source_mismatch", "upload_ack_invalid", "upload_incomplete", "upload_order_conflict", "chunk_hash_mismatch",
  "meeting_state_conflict", "name_conflict", "inference_unavailable", "job_timeout", "worker_interrupted",
]);
export function meetingErrorKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (codes.has(error.code)) return `meeting.error.${error.code}`;
    if (error.status === 403) return "meeting.error.forbidden";
    if (error.status === 404) return "meeting.error.not_found";
    if (error.status === 413) return "meeting.error.audio_limit";
    if (error.status === 422) return "meeting.error.validation_error";
  }
  return "meeting.error.unexpected";
}
export function validateMeetingFile(file: File): string | null {
  if (file.size === 0) return "meeting.error.invalid_audio";
  if (file.size > 2 * 1024 ** 3) return "meeting.error.audio_limit";
  if (!/\.(wav|flac)$/i.test(file.name)) return "meeting.error.unsupported_audio";
  return null;
}
export function recordingTime(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  return [Math.floor(total / 3600), Math.floor(total / 60) % 60, total % 60].map((part) => String(part).padStart(2, "0")).join(":");
}
