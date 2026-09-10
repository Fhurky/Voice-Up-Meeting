import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { readUser, STORAGE_KEYS } from "@/lib/authStorage";
import type { AuthenticatedUser, LoginResponse } from "@/types/auth";

const service = vi.hoisted(() => ({
  login: vi.fn<(username: string, password: string) => Promise<LoginResponse>>(),
  loginAsAdmin: vi.fn<() => Promise<LoginResponse>>(),
  me: vi.fn<() => Promise<AuthenticatedUser>>(),
}));
vi.mock("@/services/auth", () => ({ AuthService: service }));
const user: AuthenticatedUser = {
  public_id: "actor-public-id", tenant_id: "tenant-public-id", username: "local-admin",
  is_super_admin: true, roles: ["super_admin"], permissions: ["*:*"],
};
const response: LoginResponse = { access_token: "fixture-token", token_type: "bearer", user };

function Session() {
  const auth = useAuth();
  return <>
    <output aria-label="actor">{auth.user?.username ?? "none"}</output>
    <output aria-label="permission">{String(auth.hasPermission("speaker_profiles:write"))}</output>
    <output aria-label="loading">{String(auth.loading)}</output>
    <button onClick={() => { void auth.loginAsAdmin(); }}>Admin fixture action</button>
    <button onClick={() => { void auth.login("ordinary", "fixture-password"); }}>Normal fixture action</button>
    <button onClick={auth.logout}>Logout fixture action</button>
  </>;
}
function show() { return render(<AuthProvider><Session /></AuthProvider>); }
function preload() {
  localStorage.setItem(STORAGE_KEYS.accessToken, response.access_token);
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user));
}
beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  service.login.mockResolvedValue(response);
  service.loginAsAdmin.mockResolvedValue(response);
  service.me.mockResolvedValue(user);
});
afterEach(() => { cleanup(); localStorage.clear(); });

it.each(["Admin", "Normal"])("stores, authorizes and clears the same session for %s sign-in", async (action) => {
  show();
  expect(service.loginAsAdmin).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: `${action} fixture action` }));
  await waitFor(() => expect(screen.getByLabelText("actor")).toHaveTextContent(user.username));
  expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBe(response.access_token);
  expect(readUser()).toEqual(user);
  expect(screen.getByLabelText("permission")).toHaveTextContent("true");
  fireEvent.click(screen.getByRole("button", { name: "Logout fixture action" }));
  expect(screen.getByLabelText("actor")).toHaveTextContent("none");
  expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBeNull();
  expect(readUser()).toBeNull();
  expect(service.loginAsAdmin).toHaveBeenCalledTimes(action === "Admin" ? 1 : 0);
});

it("restores through me after reload and updates stored permissions without another admin login", async () => {
  const initial = show();
  fireEvent.click(screen.getByRole("button", { name: "Admin fixture action" }));
  await waitFor(() => expect(readUser()).toEqual(user));
  initial.unmount();
  const current = { ...user, is_super_admin: false, roles: [], permissions: [] };
  service.me.mockResolvedValue(current);
  show();
  await waitFor(() => expect(screen.getByLabelText("loading")).toHaveTextContent("false"));
  expect(service.me).toHaveBeenCalledTimes(1);
  expect(readUser()).toEqual(current);
  expect(screen.getByLabelText("permission")).toHaveTextContent("false");
  expect(service.loginAsAdmin).toHaveBeenCalledTimes(1);
});

it("does not restore a delayed me response after logout", async () => {
  preload();
  let finish!: (value: AuthenticatedUser) => void;
  service.me.mockReturnValue(new Promise<AuthenticatedUser>((resolve) => { finish = resolve; }));
  show();
  fireEvent.click(screen.getByRole("button", { name: "Logout fixture action" }));
  await act(async () => finish(user));
  expect(screen.getByLabelText("actor")).toHaveTextContent("none");
  expect(readUser()).toBeNull();
  expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBeNull();
});

it("does not restore a delayed local admin response after logout", async () => {
  let finish!: (value: LoginResponse) => void;
  service.loginAsAdmin.mockReturnValue(new Promise<LoginResponse>((resolve) => { finish = resolve; }));
  show();
  fireEvent.click(screen.getByRole("button", { name: "Admin fixture action" }));
  expect(service.loginAsAdmin).toHaveBeenCalledExactlyOnceWith();
  fireEvent.click(screen.getByRole("button", { name: "Logout fixture action" }));
  await act(async () => finish(response));
  expect(screen.getByLabelText("actor")).toHaveTextContent("none");
  expect(readUser()).toBeNull();
  expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBeNull();
});

it("preserves an existing session when me is temporarily unavailable", async () => {
  preload();
  service.me.mockRejectedValue(new Error("Temporary network failure"));
  show();
  await waitFor(() => expect(screen.getByLabelText("loading")).toHaveTextContent("false"));
  expect(readUser()).toEqual(user);
  expect(localStorage.getItem(STORAGE_KEYS.accessToken)).toBe(response.access_token);
});
