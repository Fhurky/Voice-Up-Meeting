import { clearAuth, readUser, STORAGE_KEYS } from "@/lib/authStorage";
import { config } from "@/lib/config";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
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
  headers.set("Content-Type", "application/json");
  if (authenticated) {
    const token = localStorage.getItem(STORAGE_KEYS.accessToken);
    if (token) headers.set("Authorization", "Bearer " + token);
    const tenantId = readUser()?.tenant_id;
    if (tenantId && !headers.has(config.tenantHeader))
      headers.set(config.tenantHeader, tenantId);
  }
  const response = await fetch(config.apiPrefix + path, { ...init, headers });
  if (response.status === 401) {
    clearAuth();
    if (window.location.pathname !== "/login") window.location.assign("/login");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: string;
      message?: string | string[];
    };
    const message = Array.isArray(body.message)
      ? body.message.join(", ")
      : body.message;
    throw new ApiError(
      response.status,
      body.detail || message || "Request failed",
    );
  }
  return (await response.json()) as T;
}
