import { apiRequest } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type Meeting = components["schemas"]["MeetingResponse"];
export type MeetingCreate = components["schemas"]["MeetingCreate"];
export type MeetingSpeaker = components["schemas"]["MeetingSpeakerResponse"];
export type MeetingTranscript = components["schemas"]["MeetingTranscriptResponse"];
export type MeetingUploadManifest = components["schemas"]["MeetingUploadManifest"];
type Rename = components["schemas"]["MeetingSpeakerRename"];
const path = (id: string) => `/meetings/${encodeURIComponent(id)}`;

export const MeetingService = {
  list(offset = 0, signal?: AbortSignal) {
    return apiRequest<components["schemas"]["MeetingPage"]>(`/meetings?offset=${offset}&limit=20`, { signal });
  },
  create(request: MeetingCreate, key: string, signal?: AbortSignal) {
    return apiRequest<Meeting>("/meetings", { method: "POST", headers: { "Idempotency-Key": key }, body: JSON.stringify(request), signal });
  },
  get(id: string, signal?: AbortSignal) { return apiRequest<Meeting>(path(id), { signal }); },
  manifest(id: string, signal?: AbortSignal) { return apiRequest<MeetingUploadManifest>(`${path(id)}/upload-parts`, { signal }); },
  uploadPart(id: string, index: number, body: ArrayBuffer, sha256: string, signal?: AbortSignal) {
    return apiRequest<MeetingUploadManifest>(`${path(id)}/upload-parts/${index}`, {
      method: "PUT", headers: { "Content-Type": "application/octet-stream", "X-Chunk-SHA256": sha256 }, body, signal,
    });
  },
  complete(id: string, signal?: AbortSignal) { return apiRequest<Meeting>(`${path(id)}/complete`, { method: "POST", signal }); },
  cancel(id: string, signal?: AbortSignal) { return apiRequest<Meeting>(`${path(id)}/cancel`, { method: "POST", signal }); },
  retry(id: string, signal?: AbortSignal) { return apiRequest<Meeting>(`${path(id)}/retry`, { method: "POST", signal }); },
  remove(id: string, signal?: AbortSignal) { return apiRequest<void>(path(id), { method: "DELETE", signal }); },
  speakers(id: string, offset = 0, signal?: AbortSignal) {
    return apiRequest<components["schemas"]["MeetingSpeakerPage"]>(`${path(id)}/speakers?offset=${offset}&limit=20`, { signal });
  },
  transcript(id: string, offset = 0, signal?: AbortSignal) {
    return apiRequest<components["schemas"]["MeetingTranscriptPage"]>(`${path(id)}/transcript?offset=${offset}&limit=50`, { signal });
  },
  rename(id: string, speakerId: string, request: Rename, signal?: AbortSignal) {
    return apiRequest<MeetingSpeaker>(`${path(id)}/speakers/${encodeURIComponent(speakerId)}`, { method: "PATCH", body: JSON.stringify(request), signal });
  },
};
