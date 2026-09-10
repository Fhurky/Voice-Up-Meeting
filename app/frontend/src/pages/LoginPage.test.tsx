import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import LoginPage from "@/pages/LoginPage";
import { ApiError } from "@/lib/apiClient";
import type { AuthOptions } from "@/types/auth";

const auth = vi.hoisted(() => ({
  login: vi.fn<(username: string, password: string) => Promise<void>>(),
  loginAsAdmin: vi.fn<() => Promise<void>>(),
}));
const options = vi.hoisted(() => vi.fn<() => Promise<AuthOptions>>());
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ user: null, ...auth }) }));
vi.mock("@/services/auth", () => ({ AuthService: { options } }));

beforeEach(() => {
  vi.clearAllMocks();
  options.mockResolvedValue({ local_admin_login_enabled: true });
  auth.login.mockResolvedValue(undefined);
  auth.loginAsAdmin.mockResolvedValue(undefined);
});
afterEach(cleanup);

async function show(locale = "tr") {
  render(<IntlProvider><MemoryRouter initialEntries={["/login"]}><Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/" element={<h1>Fixture home</h1>} />
  </Routes></MemoryRouter></IntlProvider>);
  await screen.findByLabelText("Kullanıcı adı");
  if (locale === "en") {
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    await screen.findByLabelText("Username");
  }
}

const labels = {
  tr: { admin: "Admin olarak giriş yap", submit: "Giriş yap", username: "Kullanıcı adı", password: "Parola" },
  en: { admin: "Sign in as admin", submit: "Sign in", username: "Username", password: "Password" },
} as const;

it.each(["tr", "en"] as const)("offers explicit admin sign-in with empty credentials in %s", async (locale) => {
  await show(locale);
  const text = labels[locale];
  const button = await screen.findByRole("button", { name: text.admin });
  expect(screen.getByLabelText(text.username)).toHaveValue("");
  expect(screen.getByLabelText(text.password)).toHaveValue("");
  expect(auth.loginAsAdmin).not.toHaveBeenCalled();
  fireEvent.click(button);
  await screen.findByRole("heading", { name: "Fixture home" });
  expect(auth.loginAsAdmin).toHaveBeenCalledExactlyOnceWith();
  expect(auth.login).not.toHaveBeenCalled();
  expect(options).toHaveBeenCalledTimes(1);
});

it.each(["disabled", "failed", "loading"])("keeps password sign-in usable when options are %s", async (state) => {
  if (state === "disabled") options.mockResolvedValue({ local_admin_login_enabled: false });
  if (state === "failed") options.mockRejectedValue(new ApiError(503, "Unavailable"));
  if (state === "loading") options.mockReturnValue(new Promise(() => {}));
  await show();
  expect(screen.queryByRole("button", { name: labels.tr.admin })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText(labels.tr.username), { target: { value: "ordinary" } });
  fireEvent.change(screen.getByLabelText(labels.tr.password), { target: { value: "fixture-password" } });
  fireEvent.click(screen.getByRole("button", { name: labels.tr.submit }));
  await screen.findByRole("heading", { name: "Fixture home" });
  expect(auth.login).toHaveBeenCalledExactlyOnceWith("ordinary", "fixture-password");
  expect(auth.loginAsAdmin).not.toHaveBeenCalled();
});

it.each(["admin", "password"])("disables both actions while %s sign-in is pending", async (action) => {
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => { finish = resolve; });
  (action === "admin" ? auth.loginAsAdmin : auth.login).mockReturnValue(pending);
  await show();
  const admin = await screen.findByRole("button", { name: labels.tr.admin });
  const normal = screen.getByRole("button", { name: labels.tr.submit });
  fireEvent.click(action === "admin" ? admin : normal);
  expect(admin).toBeDisabled();
  expect(normal).toBeDisabled();
  fireEvent.submit(screen.getByLabelText(labels.tr.password).closest("form")!);
  fireEvent.click(admin);
  expect(auth.login.mock.calls.length + auth.loginAsAdmin.mock.calls.length).toBe(1);
  await act(async () => finish());
  await screen.findByRole("heading", { name: "Fixture home" });
});

it.each(["tr", "en"] as const)("localizes unavailable local administrator in %s", async (locale) => {
  auth.loginAsAdmin.mockRejectedValue(new ApiError(503, "private account detail", "local_admin_unavailable"));
  await show(locale);
  fireEvent.click(await screen.findByRole("button", { name: labels[locale].admin }));
  expect(await screen.findByRole("alert")).toHaveTextContent(locale === "tr"
    ? "Yerel yönetici hesabı hazır değil. Yönetici kurulumunu tamamlayın veya kullanıcı adı ve parolanızla giriş yapın."
    : "The local administrator account is not ready. Complete administrator setup or sign in with your username and password.");
  expect(screen.queryByText("private account detail")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: labels[locale].admin })).toBeEnabled();
});

it.each(["tr", "en"] as const)("localizes disabled endpoint without blocking password sign-in in %s", async (locale) => {
  auth.loginAsAdmin.mockRejectedValue(new ApiError(404, "Not found"));
  await show(locale);
  fireEvent.click(await screen.findByRole("button", { name: labels[locale].admin }));
  expect(await screen.findByRole("alert")).toHaveTextContent(locale === "tr"
    ? "Yerel yönetici girişi bu adreste etkin değil. Kullanıcı adı ve parolanızla giriş yapın."
    : "Local administrator sign-in is not enabled at this address. Sign in with your username and password.");
  expect(screen.getByRole("button", { name: labels[locale].submit })).toBeEnabled();
});

it("updates a visible login error when the locale changes", async () => {
  auth.login.mockRejectedValue(new ApiError(401, "Invalid credentials"));
  await show();
  fireEvent.click(screen.getByRole("button", { name: "Giriş yap" }));
  await screen.findByText("Kullanıcı adı veya parola geçersiz.");
  fireEvent.click(screen.getByRole("button", { name: "English" }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("The username or password is invalid."));
});
