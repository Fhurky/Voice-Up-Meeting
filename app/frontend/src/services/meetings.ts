import { apiBlob, apiRequest } from "@/lib/apiClient";
import type { components, paths } from "@/types/api";

export type Meeting = components["schemas"]["MeetingResponse"];
export type MeetingCreate = components["schemas"]["MeetingCreate"];
export type MeetingSpeaker = components["schemas"]["MeetingSpeakerResponse"];
export type MeetingTranscript = components["schemas"]["MeetingTranscriptResponse"];
export type MeetingUploadManifest = components["schemas"]["MeetingUploadManifest"];
export type MeetingCorrectionPreview = paths["/api/voiceup/v1/meetings/{public_id}/transcript/{transcript_id}/correction-preview"]["post"]["responses"][200]["content"]["application/json"];
export type ReviewModelList = paths["/api/voiceup/v1/meetings/review-models"]["get"]["responses"][200]["content"]["application/json"];
export type ReviewModel = ReviewModelList["items"][number];
export type CorrectionSelection = paths["/api/voiceup/v1/meetings/{public_id}/transcript/{transcript_id}/correction-suggestion"]["post"]["requestBody"]["content"]["application/json"];
export type CorrectionSuggestion = paths["/api/voiceup/v1/meetings/{public_id}/transcript/{transcript_id}/correction-suggestion"]["post"]["responses"][200]["content"]["application/json"];
export type CorrectionSave = paths["/api/voiceup/v1/meetings/{public_id}/transcript/{transcript_id}/corrections"]["post"]["requestBody"]["content"]["application/json"];
export type SavedCorrection = NonNullable<MeetingTranscript["correction"]>;
type Rename = components["schemas"]["MeetingSpeakerRename"];
type AudioPreviewQuery = paths["/api/voiceup/v1/meetings/{public_id}/audio-preview"]["get"]["parameters"]["query"];
const path = (id: string) => `/meetings/${encodeURIComponent(id)}`;

export const MeetingService = {
  reviewModels(signal?: AbortSignal) { return apiRequest<ReviewModelList>("/meetings/review-models", { cache: "no-store", signal }); },
  correctionSuggestion(id: string, transcriptId: string, body: CorrectionSelection, signal?: AbortSignal) {
    return apiRequest<CorrectionSuggestion>(`${path(id)}/transcript/${encodeURIComponent(transcriptId)}/correction-suggestion`, { method: "POST", cache: "no-store", body: JSON.stringify(body), signal });
  },
  saveCorrection(id: string, transcriptId: string, body: CorrectionSave, signal?: AbortSignal) {
    return apiRequest<SavedCorrection>(`${path(id)}/transcript/${encodeURIComponent(transcriptId)}/corrections`, { method: "POST", cache: "no-store", body: JSON.stringify(body), signal });
  },
  correctionPreview(id: string, transcriptId: string, signal?: AbortSignal) {
    return apiRequest<MeetingCorrectionPreview>(`${path(id)}/transcript/${encodeURIComponent(transcriptId)}/correction-preview`, {
      method: "POST", cache: "no-store", signal,
    });
  },
  audioPreview(id: string, query: AudioPreviewQuery, signal?: AbortSignal) {
    const parameters = new URLSearchParams({ start_seconds: String(query.start_seconds), end_seconds: String(query.end_seconds) });
    return apiBlob(`${path(id)}/audio-preview?${parameters}`, { mediaType: "audio/wav", maxBytes: 11_520_128 }, { signal });
  },
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
