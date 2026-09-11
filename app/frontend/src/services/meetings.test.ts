import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest } from "@/lib/apiClient";
import { MeetingService } from "@/services/meetings";

vi.mock("@/lib/apiClient", () => ({ apiRequest: vi.fn() }));
beforeEach(() => vi.clearAllMocks());

describe("meeting HTTP contract", () => {
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
