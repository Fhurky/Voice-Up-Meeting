import { ApiError } from "@/lib/apiClient";

const knownCodes = new Set([
  "validation_error", "invalid_audio", "unsupported_audio", "audio_limit", "not_found",
  "idempotency_conflict", "recording_expired", "recording_in_use", "sample_limit", "forbidden",
  "insufficient_speech", "inconsistent_audio", "clipped_audio", "target_mismatch",
  "profile_unavailable", "model_mismatch", "inference_unavailable", "job_timeout",
  "worker_interrupted", "recording_unavailable",
]);

export function errorMessageKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (knownCodes.has(error.code)) return `speaker.error.${error.code}`;
    if (error.status === 403) return "speaker.error.forbidden";
    if (error.status === 404) return "speaker.error.not_found";
    if (error.status === 413) return "speaker.error.audio_limit";
    if (error.status === 422) return "speaker.error.validation_error";
  }
  return "speaker.error.unexpected";
}

export function jobErrorKey(code: string): string {
  return knownCodes.has(code) ? `speaker.error.${code}` : "speaker.error.unexpected";
}

export function validateAudioFile(file: File): string | null {
  if (file.size === 0) return "speaker.error.invalid_audio";
  if (file.size > 50 * 1024 * 1024) return "speaker.error.audio_limit";
  if (!/\.(wav|flac)$/i.test(file.name)) return "speaker.error.unsupported_audio";
  return null;
}
