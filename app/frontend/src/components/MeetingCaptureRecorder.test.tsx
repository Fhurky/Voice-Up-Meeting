import { createHash } from "node:crypto";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IntlProvider } from "@/contexts/IntlContext";
import { MeetingCaptureRecorder } from "@/components/MeetingCaptureRecorder";
import type { MeetingCaptureOptions, MeetingCaptureProgress } from "@/lib/meetingCapture";
import { MeetingService } from "@/services/meetings";
import { meeting } from "@/test/meetingFixtures";

const capture = vi.hoisted(() => ({
  start: vi.fn(), stop: vi.fn(), cancel: vi.fn(), setMicrophoneMuted: vi.fn(), create: vi.fn(), support: vi.fn(),
  sampleRate: 16000, options: null as MeetingCaptureOptions | null,
}));
vi.mock("@/lib/meetingCapture", () => ({
  createMeetingCapture: capture.create,
  meetingCaptureSupportError: capture.support,
  MeetingCaptureError: class extends Error { constructor(public code: string) { super(code); } },
}));
vi.mock("@/lib/microphoneCapture", () => ({ listMicrophoneDevices: vi.fn(async () => []) }));

const captured = { ...meeting, status: "uploading" as const, capture_mode: "two_channel" as const, captured_frames: 0, captured_seconds: 0 };
const progress: MeetingCaptureProgress = {
  elapsedSeconds: 61, bufferedBytes: 0, levels: [0.1, 0], silentSeconds: [0, 61],
  microphoneSilent: false, systemSilent: true, echo: false, microphoneLost: false,
};

beforeEach(() => {
  capture.start.mockReset().mockResolvedValue(undefined);
  capture.stop.mockReset(); capture.cancel.mockReset().mockResolvedValue(undefined);
  capture.setMicrophoneMuted.mockReset(); capture.support.mockReset().mockReturnValue(null);
  capture.create.mockReset().mockImplementation((options: MeetingCaptureOptions) => { capture.options = options; return capture; });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function setup() {
  const complete = vi.fn(); const busy = vi.fn();
  const request = () => ({ title: "Teams", language: "tr" as const, participant_count: null, expected_speakers: null,
    auto_enroll: false, participant_profile_ids: [], subject: null, questions: [] });
  render(<IntlProvider><MeetingCaptureRecorder onBeforeStart={() => true} request={request} onBusyChange={busy} onComplete={complete} /></IntlProvider>);
  return { complete, busy };
}
async function startRecording() {
  fireEvent.click(await screen.findByRole("checkbox", { name: "Katılımcıları bu kayıttan haberdar ettim" }));
  fireEvent.click(screen.getByRole("button", { name: "Kaydı başlat" }));
  await screen.findByRole("button", { name: "Bitir" });
}

describe("two-channel Teams capture", () => {
  it("starts only after the participants were informed, streams parts and completes with the chain", async () => {
    const create = vi.spyOn(MeetingService, "createCapture").mockResolvedValue(captured);
    const append = vi.spyOn(MeetingService, "appendCapture").mockImplementation(async (_id, start, body) => ({ received_frames: start + body.byteLength / 4 }));
    const complete = vi.spyOn(MeetingService, "completeCapture").mockResolvedValue({ ...captured, status: "queued" });
    const view = setup();
    expect(await screen.findByRole("button", { name: "Kaydı başlat" })).toBeDisabled();
    await startRecording();
    expect(capture.start).toHaveBeenCalledOnce();
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ title: "Teams", sample_rate: 16000 }), expect.any(String));
    const part = new Uint8Array(8).fill(3).buffer;
    act(() => capture.options!.onPart!({ startFrame: 0, frameCount: 2, data: part }));
    await waitFor(() => expect(append).toHaveBeenCalledWith(captured.public_id, 0, part, createHash("sha256").update(new Uint8Array(part)).digest("hex")));
    const dispose = vi.fn(async () => {});
    capture.stop.mockResolvedValue({ file: new File([new Uint8Array(44), new Uint8Array(part)], "capture.wav"), frameCount: 2, sampleRate: 16000, durationSeconds: 2 / 16000, dispose });
    fireEvent.click(screen.getByRole("button", { name: "Bitir" }));
    const chain = createHash("sha256").update(Buffer.alloc(32)).update(createHash("sha256").update(new Uint8Array(part)).digest()).digest("hex");
    await waitFor(() => expect(complete).toHaveBeenCalledWith(captured.public_id, { frames: 2, chain_sha256: chain }));
    await waitFor(() => expect(view.complete).toHaveBeenCalledWith(expect.objectContaining({ status: "queued" })));
    expect(dispose).toHaveBeenCalledOnce();
  });

  it("creates no meeting when the screen picker is dismissed", async () => {
    const { MeetingCaptureError } = await import("@/lib/meetingCapture");
    capture.start.mockRejectedValue(new MeetingCaptureError("share_cancelled"));
    const create = vi.spyOn(MeetingService, "createCapture");
    setup();
    fireEvent.click(await screen.findByRole("checkbox", { name: "Katılımcıları bu kayıttan haberdar ettim" }));
    fireEvent.click(screen.getByRole("button", { name: "Kaydı başlat" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ekran paylaşımı seçilmedi; kayıt başlamadı.");
    expect(create).not.toHaveBeenCalled();
  });

  it("shows silence warnings and keeps the microphone out of the recording on request", async () => {
    vi.spyOn(MeetingService, "createCapture").mockResolvedValue(captured);
    setup(); await startRecording();
    act(() => capture.options!.onProgress!(progress));
    expect(screen.getByText(/Toplantı sesi gelmiyor/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Mikrofonumu kaydetme" }));
    expect(capture.setMicrophoneMuted).toHaveBeenCalledWith(true);
  });

  it("finishes when the browser's stop sharing control ends the system audio", async () => {
    vi.spyOn(MeetingService, "createCapture").mockResolvedValue(captured);
    const complete = vi.spyOn(MeetingService, "completeCapture").mockResolvedValue({ ...captured, status: "queued" });
    capture.stop.mockResolvedValue({ file: new File([new Uint8Array(44)], "capture.wav"), frameCount: 0, sampleRate: 16000, durationSeconds: 0, dispose: vi.fn(async () => {}) });
    setup(); await startRecording();
    act(() => capture.options!.onShareEnded!());
    await waitFor(() => expect(capture.stop).toHaveBeenCalledOnce());
    await waitFor(() => expect(complete).toHaveBeenCalledOnce());
  });

  it("explains an unsupported browser and keeps the start button disabled", async () => {
    capture.support.mockReturnValue("unsupported");
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("Windows'ta Edge kullanın");
    fireEvent.click(screen.getByRole("checkbox", { name: "Katılımcıları bu kayıttan haberdar ettim" }));
    expect(screen.getByRole("button", { name: "Kaydı başlat" })).toBeDisabled();
  });
});
