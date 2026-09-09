import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest, ApiError } from "@/lib/apiClient";
import { STORAGE_KEYS } from "@/lib/authStorage";

describe("shared API boundary", () => {
  beforeEach(() => localStorage.setItem(STORAGE_KEYS.accessToken, "test-token"));
  afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

  it("lets the browser provide the multipart boundary", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response('{"public_id":"r1"}'));
    vi.stubGlobal("fetch", fetchMock);
    const body = new FormData();
    body.set("file", new Blob(["voice"]), "voice.wav");
    await apiRequest("/recordings", { method: "POST", body });
    const options = fetchMock.mock.calls[0][1];
    expect(new Headers(options?.headers).has("Content-Type")).toBe(false);
    expect(new Headers(options?.headers).get("Authorization")).toBe("Bearer test-token");
  });

  it("preserves the bearer session for an unrelated upstream 401", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response("upstream", { status: 401 })));
    await expect(apiRequest("/speaker-profiles")).rejects.toBeInstanceOf(ApiError);
    expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBe("test-token");
  });

  it("does not parse an empty successful DELETE response as JSON", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(apiRequest<void>("/speaker-profiles/p1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("retains stable error codes without exposing raw server detail to callers", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "sample_limit", message: "internal path" } }), { status: 409 })));
    await expect(apiRequest("/speaker-jobs")).rejects.toMatchObject({ status: 409, code: "sample_limit" });
  });
});
