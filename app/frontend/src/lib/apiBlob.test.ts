import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBlob } from "@/lib/apiClient";
import { STORAGE_KEYS } from "@/lib/authStorage";

describe("bounded authenticated binary responses", () => {
  beforeEach(() => {
    localStorage.setItem(STORAGE_KEYS.accessToken, "test-token");
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify({ tenant_id: "tenant-a" }));
  });
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });
  const options = { mediaType: "audio/wav", maxBytes: 8 };
  it("uses the shared bearer and tenant headers and returns the exact bounded bytes", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(new Uint8Array([1, 2, 3]), { headers: { "Content-Type": "audio/wav", "Content-Length": "3" } }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await apiBlob("/preview", options);
    expect(result.type).toBe("audio/wav"); expect(Array.from(new Uint8Array(await result.arrayBuffer()))).toEqual([1, 2, 3]);
    const init = fetchMock.mock.calls[0][1]; const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-token"); expect(headers.get("x-tenant-id")).toBe("tenant-a");
    expect(headers.get("Accept")).toBe("audio/wav"); expect(init?.cache).toBe("no-store");
  });
  it.each([
    ["text/html", "3", "abc"], ["audio/wav", "9", "abc"], ["audio/wav", "3", ""], ["audio/wav", "2", "abc"],
  ])("rejects a malformed response (%s, %s)", async (type, length, body) => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(body, { headers: { "Content-Type": type, "Content-Length": length } })));
    await expect(apiBlob("/preview", options)).rejects.toMatchObject({ code: "invalid_response" });
  });
  it("bounds chunked responses even without Content-Length and cancels overflow", async () => {
    const cancel = vi.fn();
    const body = new ReadableStream<Uint8Array>({ start(controller) { controller.enqueue(new Uint8Array(5)); controller.enqueue(new Uint8Array(5)); }, cancel });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(body, { headers: { "Content-Type": "audio/wav" } })));
    await expect(apiBlob("/preview", options)).rejects.toMatchObject({ code: "invalid_response" });
    expect(cancel).toHaveBeenCalledOnce();
  });
  it("preserves the session on an unrelated upstream 401", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response("upstream", { status: 401 })));
    await expect(apiBlob("/preview", options)).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBe("test-token");
  });
  it("clears a rejected application bearer session and retains only the safe error code", async () => {
    const assign = vi.spyOn(window.location, "assign").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response('{"detail":{"code":"token_expired","message":"private"}}', { status: 401, headers: { "WWW-Authenticate": "Bearer" } })));
    await expect(apiBlob("/preview", options)).rejects.toMatchObject({ status: 401, code: "token_expired", message: "API request failed" });
    expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBeNull(); expect(assign).toHaveBeenCalledWith("/login");
  });
  it("refuses a late body after caller cancellation", async () => {
    const controller = new AbortController();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockImplementation(async () => { controller.abort(); return new Response("abc", { headers: { "Content-Type": "audio/wav" } }); }));
    await expect(apiBlob("/preview", options, { signal: controller.signal })).rejects.toMatchObject({ name: "AbortError" });
  });
  it("cancels a pending streamed body when the caller aborts", async () => {
    const cancel = vi.fn(); const controller = new AbortController();
    const body = new ReadableStream<Uint8Array>({ start(stream) { stream.enqueue(new Uint8Array([1])); }, cancel });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(body, { headers: { "Content-Type": "audio/wav" } })));
    const pending = apiBlob("/preview", options, { signal: controller.signal });
    await new Promise((resolve) => setTimeout(resolve, 0)); controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" }); expect(cancel).toHaveBeenCalledOnce();
  });
  it("accepts exactly the byte bound across arbitrarily small chunks", async () => {
    const body = new ReadableStream<Uint8Array>({ start(stream) { for (let i = 0; i < 8; i++) { stream.enqueue(new Uint8Array()); stream.enqueue(new Uint8Array([i])); } stream.close(); } });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(body, { headers: { "Content-Type": "audio/wav" } })));
    const result = await apiBlob("/preview", options);
    expect(Array.from(new Uint8Array(await result.arrayBuffer()))).toEqual([0, 1, 2, 3, 4, 5, 6, 7]);
  });
});
