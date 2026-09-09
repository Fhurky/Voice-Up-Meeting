import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import LoginPage from "@/pages/LoginPage";
import { ApiError } from "@/lib/apiClient";

vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ user: null, login: () => Promise.reject(new ApiError(401, "Invalid credentials")) }) }));
afterEach(cleanup);
it("updates a visible login error when the locale changes", async () => {
  render(<IntlProvider><MemoryRouter><LoginPage /></MemoryRouter></IntlProvider>);
  fireEvent.click(await screen.findByRole("button", { name: "Giriş yap" }));
  await screen.findByText("Kullanıcı adı veya parola geçersiz.");
  fireEvent.click(screen.getByRole("button", { name: "English" }));
  await screen.findByText("The username or password is invalid.");
});
