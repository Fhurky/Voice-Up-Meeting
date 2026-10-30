import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import { ApiError } from "@/lib/apiClient";
import SettingsPage from "@/pages/SettingsPage";
import { MeetingService } from "@/services/meetings";

vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ user: { display_name: "Yönetici", username: "admin", is_super_admin: true }, logout: vi.fn(), hasPermission: () => true }) }));
const state = { device: "gpu", gpu_available: true, cpu_available: true, switching: false, last_error: null } as const;
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });
beforeEach(() => { vi.spyOn(MeetingService, "processingMode").mockResolvedValue({ processing_device: "gpu" }); });
function setup() { render(<IntlProvider><MemoryRouter><SettingsPage /></MemoryRouter></IntlProvider>); }
const button = (name: string) => screen.findByRole("button", { name });

describe("settings page", () => {
  it("shows the running processor and marks it as selected", async () => {
    vi.spyOn(MeetingService, "processor").mockResolvedValue(state);
    setup();
    expect(await button("GPU")).toHaveAttribute("aria-pressed", "true");
    expect(await button("CPU")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText(/yeniden başlayınca/)).toBeInTheDocument();
  });

  it("switches, follows the progress and shows the new processor", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const read = vi.spyOn(MeetingService, "processor").mockResolvedValueOnce(state).mockRejectedValueOnce(new ApiError(503, "Starting", "inference_unavailable")).mockResolvedValueOnce({ ...state, device: "cpu", switching: true });
    const change = vi.spyOn(MeetingService, "changeProcessor").mockResolvedValue({ ...state, switching: true });
    setup();
    fireEvent.click(await button("CPU"));
    await waitFor(() => expect(change).toHaveBeenCalledWith({ device: "cpu" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Modeller yükleniyor");
    expect(screen.queryByText(/da işleniyor/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CPU" })).toBeDisabled();
    read.mockResolvedValue({ ...state, device: "cpu" });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
    expect(await screen.findByRole("status")).toHaveTextContent("Modeller yükleniyor");
    await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
    expect(await button("CPU")).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByText(/CPU'da işleniyor/)).toBeInTheDocument();
  });

  it("explains that the GPU is not available and keeps it disabled", async () => {
    vi.spyOn(MeetingService, "processor").mockResolvedValue({ ...state, device: "cpu", gpu_available: false });
    const change = vi.spyOn(MeetingService, "changeProcessor");
    setup();
    expect(await button("GPU")).toBeDisabled();
    expect(screen.getByText(/GPU görülmüyor/)).toBeInTheDocument();
    expect(change).not.toHaveBeenCalled();
  });

  it("does nothing when the current processor is chosen", async () => {
    vi.spyOn(MeetingService, "processor").mockResolvedValue(state);
    const change = vi.spyOn(MeetingService, "changeProcessor");
    setup();
    fireEvent.click(await button("GPU"));
    expect(change).not.toHaveBeenCalled();
  });

  it("says a running job blocks the change", async () => {
    vi.spyOn(MeetingService, "processor").mockResolvedValue(state);
    vi.spyOn(MeetingService, "changeProcessor").mockRejectedValue(new ApiError(409, "Busy", "inference_busy"));
    setup();
    fireEvent.click(await button("CPU"));
    expect(await screen.findByRole("alert")).toHaveTextContent("toplantı işleniyor");
    expect(await button("GPU")).toHaveAttribute("aria-pressed", "true");
  });

  it("reports a failed switch and the processor it returned to", async () => {
    vi.spyOn(MeetingService, "processor").mockResolvedValue({ ...state, last_error: "processor_switch_failed" });
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("geri dönüldü");
  });

  it("shows an error while the state cannot be read and recovers by itself", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.spyOn(MeetingService, "processor").mockRejectedValueOnce(new ApiError(503, "Down", "inference_unavailable")).mockResolvedValue(state);
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("okunamadı");
    await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
    expect(await button("GPU")).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
