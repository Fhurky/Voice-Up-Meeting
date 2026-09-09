import { apiRequest } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type SpeakerProfile = components["schemas"]["SpeakerProfileResponse"];
export type SpeakerJob = components["schemas"]["SpeakerJobResponse"];
export type SpeakerResult = components["schemas"]["SpeakerResult"];
export type JobCreate = components["schemas"]["SpeakerJobCreate"];
type Recording = components["schemas"]["RecordingResponse"];

export const SpeakerService = {
  profiles(offset = 0, signal?: AbortSignal) {
    return apiRequest<components["schemas"]["SpeakerProfilePage"]>(`/speaker-profiles?offset=${offset}&limit=20`, { signal });
  },
  rename(publicId: string, name: string, signal?: AbortSignal) {
    return apiRequest<SpeakerProfile>(`/speaker-profiles/${encodeURIComponent(publicId)}`, {
      method: "PATCH", body: JSON.stringify({ name }), signal,
    });
  },
  remove(publicId: string, signal?: AbortSignal) {
    return apiRequest<void>(`/speaker-profiles/${encodeURIComponent(publicId)}`, { method: "DELETE", signal });
  },
  upload(file: File, key: string, signal?: AbortSignal) {
    const body = new FormData();
    body.set("file", file);
    return apiRequest<Recording>("/recordings", { method: "POST", headers: { "Idempotency-Key": key }, body, signal });
  },
  createJob(request: JobCreate, key: string, signal?: AbortSignal) {
    return apiRequest<SpeakerJob>("/speaker-jobs", {
      method: "POST", headers: { "Idempotency-Key": key }, body: JSON.stringify(request), signal,
    });
  },
  job(publicId: string, signal?: AbortSignal) {
    return apiRequest<SpeakerJob>(`/speaker-jobs/${encodeURIComponent(publicId)}`, { signal });
  },
  jobs(offset = 0, signal?: AbortSignal) {
    return apiRequest<components["schemas"]["SpeakerJobPage"]>(`/speaker-jobs?offset=${offset}&limit=20`, { signal });
  },
};
