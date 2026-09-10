import { afterEach, expect, it, vi } from "vitest";
import { AuthService } from "@/services/auth";
import { STORAGE_KEYS } from "@/lib/authStorage";

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

it("reads public options without a stored actor or tenant", async () => {
  localStorage.setItem(STORAGE_KEYS.accessToken, "existing-token");
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify({ tenant_id: "existing-tenant" }));
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ local_admin_login_enabled: true })));
  vi.stubGlobal("fetch", fetch);
  await expect(AuthService.options()).resolves.toEqual({ local_admin_login_enabled: true });
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, request] = fetch.mock.calls[0] as [string, RequestInit];
  expect(url).toMatch(/\/auth\/options$/);
  expect(request.method).toBe("GET");
  expect(request.cache).toBe("no-store");
  const headers = new Headers(request.headers);
  expect(headers.has("Authorization")).toBe(false);
  expect(headers.has("X-Tenant-ID")).toBe(false);
});

it("posts no credentials or actor selection and returns the existing session contract", async () => {
  localStorage.setItem(STORAGE_KEYS.accessToken, "existing-token");
  const response = { access_token: "fixture-token", token_type: "bearer", user: {
    public_id: "actor", tenant_id: "tenant", username: "admin", is_super_admin: true,
    roles: ["super_admin"], permissions: ["*:*"],
  } };
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(response)));
  vi.stubGlobal("fetch", fetch);
  await expect(AuthService.loginAsAdmin()).resolves.toEqual(response);
  const [url, request] = fetch.mock.calls[0] as [string, RequestInit];
  expect(url).toMatch(/\/auth\/local-admin$/);
  expect(request.method).toBe("POST");
  expect(request.body).toBeUndefined();
  expect(request.cache).toBe("no-store");
  const headers = new Headers(request.headers);
  expect(headers.has("Authorization")).toBe(false);
  expect(headers.has("X-Tenant-ID")).toBe(false);
});

it("preserves the stable local admin error code without displaying server account details", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: { code: "local_admin_unavailable", message: "private account detail" },
  }), { status: 503 })));
  await expect(AuthService.loginAsAdmin()).rejects.toMatchObject({
    status: 503, code: "local_admin_unavailable", message: "API request failed",
  });
});
