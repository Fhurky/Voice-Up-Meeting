import { clearAuth, readUser, STORAGE_KEYS } from "@/lib/authStorage";
import { config } from "@/lib/config";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code = "request_failed",
  ) {
    super(message);
  }
}

async function requestResponse(
  path: string,
  init: RequestInit = {},
  authenticated = true,
): Promise<{ response: Response; signal: AbortSignal }> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (authenticated) {
    const token = localStorage.getItem(STORAGE_KEYS.accessToken);
    if (token) headers.set("Authorization", "Bearer " + token);
    const tenantId = readUser()?.tenant_id;
    if (tenantId && !headers.has(config.tenantHeader))
      headers.set(config.tenantHeader, tenantId);
  }
  const timeout = AbortSignal.timeout(120_000);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  const response = await fetch(config.apiPrefix + path, { ...init, headers, signal });
  if (authenticated && response.status === 401 && /^Bearer(?:\s|$)/i.test(response.headers.get("WWW-Authenticate") ?? "")) {
    clearAuth();
    if (window.location.pathname !== "/login") window.location.assign("/login");
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const envelope = body !== null && typeof body === "object" ? body as Record<string, unknown> : {};
    const detail = envelope.detail !== null && typeof envelope.detail === "object" && !Array.isArray(envelope.detail)
      ? envelope.detail as Record<string, unknown> : envelope;
    const code = typeof detail.code === "string" ? detail.code : "request_failed";
    throw new ApiError(
      response.status,
      "API request failed",
      code,
    );
  }
  return { response, signal };
}

export async function apiRequest<T>(path: string, init: RequestInit = {}, authenticated = true): Promise<T> {
  const { response } = await requestResponse(path, init, authenticated);
  if (response.status === 204) return undefined as T;
  try { return (await response.json()) as T; }
  catch { throw new ApiError(response.status, "Invalid API response", "invalid_response"); }
}

/** Read a bounded binary body through the same authenticated request boundary. */
export async function apiBlob(
  path: string,
  limits: { mediaType: string; maxBytes: number },
  init: RequestInit = {},
): Promise<Blob> {
  const headers = new Headers(init.headers);
  headers.set("Accept", limits.mediaType);
  const { response, signal } = await requestResponse(path, { ...init, headers, cache: "no-store" });
  const invalid = () => new ApiError(response.status, "Invalid API response", "invalid_response");
  const lengthHeader = response.headers.get("Content-Length");
  const length = lengthHeader === null ? null : Number(lengthHeader);
  if (response.status !== 200 || !response.body || response.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase() !== limits.mediaType ||
    !Number.isSafeInteger(limits.maxBytes) || limits.maxBytes <= 0 ||
    (lengthHeader !== null && (!/^\d+$/.test(lengthHeader) || !Number.isSafeInteger(length) || length! <= 0 || length! > limits.maxBytes))) {
    await response.body?.cancel().catch(() => undefined);
    throw invalid();
  }
  const reader = response.body.getReader();
  const buffer = new Uint8Array(length ?? limits.maxBytes);
  let bytes = 0;
  const abort = () => { void reader.cancel().catch(() => undefined); };
  signal.addEventListener("abort", abort, { once: true });
  try {
    for (;;) {
      signal.throwIfAborted();
      const { done, value } = await reader.read();
      signal.throwIfAborted();
      if (done) break;
      if (value.byteLength > buffer.byteLength - bytes) throw invalid();
      buffer.set(value, bytes);
      bytes += value.byteLength;
    }
    if (bytes === 0 || (length !== null && bytes !== length)) throw invalid();
    return new Blob([buffer.subarray(0, bytes)], { type: limits.mediaType });
  } catch (error) {
    await reader.cancel().catch(() => undefined);
    throw error;
  } finally {
    signal.removeEventListener("abort", abort);
    reader.releaseLock();
  }
}
