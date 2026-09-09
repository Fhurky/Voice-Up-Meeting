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

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  authenticated = true,
): Promise<T> {
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
  if (response.status === 204) return undefined as T;
  try { return (await response.json()) as T; }
  catch { throw new ApiError(response.status, "Invalid API response", "invalid_response"); }
}
