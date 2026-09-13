import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiBlob, apiRequest } from "@/lib/apiClient";
import { MeetingService } from "@/services/meetings";

vi.mock("@/lib/apiClient", () => ({ apiRequest: vi.fn(), apiBlob: vi.fn() }));
beforeEach(() => vi.clearAllMocks());

describe("meeting HTTP contract", () => {
  it("lists installed models without allowing a client-selected server", async () => {
    const signal = new AbortController().signal;
    await MeetingService.reviewModels(signal);
    expect(apiRequest).toHaveBeenCalledWith("/meetings/review-models", { cache: "no-store", signal });
  });
  it("sends only the selected model identity for a visible suggestion", async () => {
    const signal = new AbortController().signal;
    const selected = { model_name: "qwen3.5:27b", model_digest: "a".repeat(64) };
    await MeetingService.correctionSuggestion("meeting/id", "turn/id", selected, signal);
    expect(apiRequest).toHaveBeenCalledWith("/meetings/meeting%2Fid/transcript/turn%2Fid/correction-suggestion", { method: "POST", cache: "no-store", body: JSON.stringify(selected), signal });
  });
  it("saves exactly the server-issued proof without invented replacement text", async () => {
    const signal = new AbortController().signal;
    await MeetingService.saveCorrection("meeting/id", "turn/id", { save_token: "signed-proof" }, signal);
    expect(apiRequest).toHaveBeenCalledWith("/meetings/meeting%2Fid/transcript/turn%2Fid/corrections", { method: "POST", cache: "no-store", body: JSON.stringify({ save_token: "signed-proof" }), signal });
  });
  it("reviews a stored transcript through path identities without sending text or a prompt", async () => {
    const signal = new AbortController().signal;
    await MeetingService.correctionPreview("meeting/id", "transcript/id", signal);
    expect(apiRequest).toHaveBeenCalledWith("/meetings/meeting%2Fid/transcript/transcript%2Fid/correction-preview", {
      method: "POST", cache: "no-store", signal,
    });
  });
  it("requests a bounded source preview using the generated query shape", async () => {
    const signal = new AbortController().signal;
    await MeetingService.audioPreview("meeting/id", { start_seconds: 1.25, end_seconds: 31.25 }, signal);
    expect(apiBlob).toHaveBeenCalledWith("/meetings/meeting%2Fid/audio-preview?start_seconds=1.25&end_seconds=31.25", { mediaType: "audio/wav", maxBytes: 11_520_128 }, { signal });
  });
  it("sends bounded binary parts with their digest through the shared client", async () => {
    const body = new ArrayBuffer(8);
    const signal = new AbortController().signal;
    await MeetingService.uploadPart("meeting/id", 2, body, "a".repeat(64), signal);
    expect(apiRequest).toHaveBeenCalledWith("/meetings/meeting%2Fid/upload-parts/2", {
      method: "PUT", body, signal,
      headers: { "Content-Type": "application/octet-stream", "X-Chunk-SHA256": "a".repeat(64) },
    });
  });

  it.each(["complete", "cancel", "retry"] as const)("posts %s without an invented JSON body", async (action) => {
    await MeetingService[action]("meeting");
    expect(apiRequest).toHaveBeenCalledWith(`/meetings/meeting/${action}`, { method: "POST", signal: undefined });
  });

  it("renames with both concurrency guards", async () => {
    const request = { name: "Person", version: 3, profile_updated_at: "2026-09-10T10:00:00Z" };
    await MeetingService.rename("meeting", "speaker", request);
    expect(apiRequest).toHaveBeenCalledWith("/meetings/meeting/speakers/speaker", {
      method: "PATCH", body: JSON.stringify(request), signal: undefined,
    });
  });
});
