import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IntlProvider } from "@/contexts/IntlContext";
import { MeetingMicrophoneRecorder } from "@/components/MeetingMicrophoneRecorder";
import type { MicrophoneCaptureOptions } from "@/lib/microphoneCapture";
import { meeting } from "@/test/meetingFixtures";

const capture = vi.hoisted(() => ({ start: vi.fn(), stop: vi.fn(), cancel: vi.fn(), create: vi.fn(), support: vi.fn() }));
vi.mock("@/lib/microphoneCapture", () => ({
  createMicrophoneCapture: capture.create,
  microphoneSupportError: capture.support,
  listMicrophoneDevices: vi.fn(async () => []),
  MicrophoneCaptureError: class extends Error { constructor(public code: string) { super(code); } },
}));

beforeEach(() => {
  capture.start.mockReset().mockResolvedValue(undefined);
  capture.stop.mockReset(); capture.cancel.mockReset().mockResolvedValue(undefined);
  capture.create.mockReset().mockReturnValue(capture); capture.support.mockReset().mockReturnValue(null);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done; }); return { promise, resolve }; }
function setup(analyze = vi.fn(async () => meeting), beforeStart = () => true) {
  const complete = vi.fn(); const busy = vi.fn();
  const view = render(<IntlProvider><MeetingMicrophoneRecorder onBeforeStart={beforeStart} onBusyChange={busy} onAnalyze={analyze} onComplete={complete} /></IntlProvider>);
  return { ...view, analyze, complete, busy };
}
async function start() { fireEvent.click(await screen.findByRole("button", { name: "Kaydı başlat" })); await screen.findByRole("button", { name: "Durdur ve analiz et" }); }

describe("meeting microphone recording", () => {
  it("waits for the sealed source, retains it throughout upload, and releases it before completion", async () => {
    const stopped = deferred<{ file: File; durationSeconds: number; dispose: () => Promise<void> }>();
    const uploaded = deferred<typeof meeting>();
    capture.stop.mockReturnValue(stopped.promise);
    const analyze = vi.fn(() => uploaded.promise); const dispose = vi.fn(async () => {});
    const { complete } = setup(analyze); await start();
    expect(analyze).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Durdur ve analiz et" }));
    expect(analyze).not.toHaveBeenCalled();
    const file = new File([new Uint8Array(100)], "microphone.wav");
    await act(async () => stopped.resolve({ file, durationSeconds: 20, dispose }));
    expect(analyze).toHaveBeenCalledWith(file, expect.any(AbortSignal), expect.any(Function));
    expect(dispose).not.toHaveBeenCalled();
    await act(async () => uploaded.resolve(meeting));
    expect(dispose).toHaveBeenCalledOnce(); expect(complete).toHaveBeenCalledWith(meeting);
  });

  it("retries the same sealed file after an upload failure without restarting the microphone", async () => {
    const file = new File(["wav"], "microphone.wav"); const dispose = vi.fn(async () => {});
    capture.stop.mockResolvedValue({ file, durationSeconds: 20, dispose });
    const analyze = vi.fn<(...args: unknown[]) => Promise<typeof meeting>>().mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(meeting);
    setup(analyze); await start(); fireEvent.click(screen.getByRole("button", { name: "Durdur ve analiz et" }));
    fireEvent.click(await screen.findByRole("button", { name: "Analizi yeniden dene" }));
    await waitFor(() => expect(dispose).toHaveBeenCalledOnce());
    expect(analyze.mock.calls.map((call) => call[0])).toEqual([file, file]); expect(capture.start).toHaveBeenCalledOnce();
  });

  it("cancels an outstanding permission request and ignores its late success", async () => {
    const pending = deferred<void>(); capture.start.mockReturnValue(pending.promise);
    const { analyze } = setup(); fireEvent.click(await screen.findByRole("button", { name: "Kaydı başlat" }));
    fireEvent.click(await screen.findByRole("button", { name: "Kaydı iptal et" }));
    await act(async () => pending.resolve());
    expect(capture.cancel).toHaveBeenCalled(); expect(analyze).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Kaydı başlat" })).toBeEnabled();
  });

  it("aborts the upload and disposes its source on navigation", async () => {
    const dispose = vi.fn(async () => {}); capture.stop.mockResolvedValue({ file: new File(["wav"], "microphone.wav"), durationSeconds: 1, dispose });
    const pending = deferred<typeof meeting>(); const analyze = vi.fn<(...args: unknown[]) => Promise<typeof meeting>>(() => pending.promise);
    const { unmount, complete } = setup(analyze); await start(); fireEvent.click(screen.getByRole("button", { name: "Durdur ve analiz et" }));
    await waitFor(() => expect(analyze).toHaveBeenCalledOnce()); unmount();
    expect((analyze.mock.calls[0]?.[1] as AbortSignal).aborted).toBe(true);
    await act(async () => pending.resolve(meeting));
    expect(dispose).toHaveBeenCalled(); expect(complete).not.toHaveBeenCalled();
  });

  it("prevents capture before meeting options are valid and explains unavailable browser support", async () => {
    const { unmount } = setup(undefined, () => false);
    fireEvent.click(await screen.findByRole("button", { name: "Kaydı başlat" }));
    expect(capture.create).not.toHaveBeenCalled(); unmount();
    capture.support.mockReturnValue("unsupported"); setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("tarayıcı");
    expect(screen.getByRole("button", { name: "Kaydı başlat" })).toBeDisabled();
  });

  it("shows microphone interruption and never analyzes incomplete audio", async () => {
    const { analyze } = setup(); await start();
    const options = capture.create.mock.calls[0]?.[0] as MicrophoneCaptureOptions;
    await act(async () => options.onError?.({ code: "device_interrupted" } as Parameters<NonNullable<MicrophoneCaptureOptions["onError"]>>[0]));
    expect(await screen.findByRole("alert")).toHaveTextContent("bağlantısı kesildi");
    expect(capture.cancel).toHaveBeenCalled(); expect(analyze).not.toHaveBeenCalled();
  });

  it("keeps cancellation pending until old resources close, including repeated clicks", async () => {
    const closing = deferred<void>(); capture.cancel.mockReturnValue(closing.promise);
    setup(); await start(); const cancel = screen.getByRole("button", { name: "Kaydı iptal et" });
    fireEvent.click(cancel); fireEvent.click(cancel);
    expect(screen.queryByRole("button", { name: "Kaydı başlat" })).not.toBeInTheDocument();
    expect(cancel).toBeDisabled();
    await act(async () => closing.resolve());
    expect(screen.getByRole("button", { name: "Kaydı başlat" })).toBeEnabled();
    expect(capture.cancel).toHaveBeenCalledOnce();
  });

  it("seals and analyzes the complete recording automatically at the duration limit", async () => {
    capture.stop.mockResolvedValue({ file: new File(["wav"], "microphone.wav"), durationSeconds: 14400, dispose: vi.fn(async () => {}) });
    const { analyze, complete } = setup(); await start();
    const options = capture.create.mock.calls[0]?.[0] as MicrophoneCaptureOptions;
    await act(async () => options.onLimit?.());
    expect(capture.stop).toHaveBeenCalledOnce(); expect(analyze).toHaveBeenCalledOnce();
    expect(complete).toHaveBeenCalledWith(meeting);
  });

  it("releases a sealed file and aborts transfer on pagehide even without React unmount", async () => {
    const dispose = vi.fn(async () => {}); capture.stop.mockResolvedValue({ file: new File(["wav"], "microphone.wav"), durationSeconds: 1, dispose });
    const pending = deferred<typeof meeting>(); const analyze = vi.fn<(...args: unknown[]) => Promise<typeof meeting>>(() => pending.promise);
    const { complete } = setup(analyze); await start(); fireEvent.click(screen.getByRole("button", { name: "Durdur ve analiz et" }));
    await waitFor(() => expect(analyze).toHaveBeenCalledOnce());
    fireEvent(window, new Event("pagehide"));
    expect((analyze.mock.calls[0]?.[1] as AbortSignal).aborted).toBe(true);
    await waitFor(() => expect(dispose).toHaveBeenCalled());
    await act(async () => pending.resolve(meeting)); expect(complete).not.toHaveBeenCalled();
  });
});
