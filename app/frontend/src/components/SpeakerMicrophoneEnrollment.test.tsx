import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import { ENROLLMENT_MAX_SECONDS, SpeakerMicrophoneEnrollment } from "@/components/SpeakerMicrophoneEnrollment";
import { ApiError } from "@/lib/apiClient";
import type { MicrophoneCaptureOptions } from "@/lib/microphoneCapture";
import { SpeakerService, type SpeakerProfile } from "@/services/speakers";
import { jobFixture, profileFixture, resultFixture } from "@/test/speakerFixtures";

const capture = vi.hoisted(() => ({ start: vi.fn(), stop: vi.fn(), cancel: vi.fn(), create: vi.fn(), support: vi.fn() }));
vi.mock("@/lib/microphoneCapture", () => ({
  createMicrophoneCapture: capture.create,
  microphoneSupportError: capture.support,
  listMicrophoneDevices: vi.fn(async () => []),
  MicrophoneCaptureError: class extends Error { constructor(public code: string) { super(code); } },
}));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: () => true, logout: vi.fn() }) }));

const recordingResponse = { public_id: jobFixture.recording_public_id, sha256: "b".repeat(64), created_at: "2026-10-29T10:00:00Z", duration_seconds: 48, format: "WAV" as const, size_bytes: 4_608_044 };
const enrollJob = { ...jobFixture, purpose: "enroll" as const };
const enrolled = { ...resultFixture, decision: "enrolled" as const, reason: "enrolled", similarity: null, runner_up_similarity: null };

beforeEach(() => {
  capture.start.mockReset().mockResolvedValue(undefined);
  capture.stop.mockReset(); capture.cancel.mockReset().mockResolvedValue(undefined);
  capture.create.mockReset().mockReturnValue(capture); capture.support.mockReset().mockReturnValue(null);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function recording(durationSeconds: number) {
  return { file: new File([new Uint8Array(100)], "owned.wav", { type: "audio/wav" }), durationSeconds, dispose: vi.fn(async () => {}) };
}
function options(): MicrophoneCaptureOptions { return capture.create.mock.calls.at(-1)![0] as MicrophoneCaptureOptions; }
function setup(profile?: SpeakerProfile) {
  const enrolledCallback = vi.fn(); const busy = vi.fn();
  render(<IntlProvider><MemoryRouter><SpeakerMicrophoneEnrollment profile={profile} onEnrolled={enrolledCallback} onBusyChange={busy} /></MemoryRouter></IntlProvider>);
  return { enrolledCallback, busy };
}
async function record(level = 0.08) {
  fireEvent.click(await screen.findByRole("button", { name: "Kaydı başlat" }));
  await screen.findByRole("button", { name: "Durdur ve doğrula" });
  options().onProgress?.({ elapsedSeconds: 30, bufferedBytes: 0, level });
}

describe("microphone profile enrollment", () => {
  it("requires a name before opening the microphone for a new profile", async () => {
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Kaydı başlat" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Bir ad veya takma ad girin.");
    expect(capture.create).not.toHaveBeenCalled();
  });

  it("guides the speaker, records up to the API limit, and creates a new profile from the sealed file", async () => {
    const take = recording(48); capture.stop.mockResolvedValue(take);
    const upload = vi.spyOn(SpeakerService, "upload").mockResolvedValue(recordingResponse);
    const create = vi.spyOn(SpeakerService, "createJob").mockResolvedValue(enrollJob);
    const job = vi.spyOn(SpeakerService, "job").mockResolvedValue({ ...enrollJob, status: "succeeded", result: enrolled });
    const { enrolledCallback, busy } = setup();
    expect(await screen.findByText(/kayıt başlayınca okunacak metin görünür/)).toBeInTheDocument();
    expect(screen.queryByText("Sesli okunacak metin")).toBeNull();
    fireEvent.change(screen.getByLabelText("Konuşmacı adı veya takma adı"), { target: { value: "  Ayşe   Demir " } });
    await record();
    expect(screen.getByText("Sesli okunacak metin")).toBeInTheDocument();
    expect(screen.getByText(/Bugün güne erkenden başladım/)).toBeInTheDocument();
    expect(options().maxSeconds).toBe(ENROLLMENT_MAX_SECONDS);
    fireEvent.click(screen.getByRole("button", { name: "Durdur ve doğrula" }));
    expect(await screen.findByRole("heading", { name: "Ses profili kaydedildi" })).toBeInTheDocument();
    expect(upload).toHaveBeenCalledWith(take.file, expect.any(String), expect.any(AbortSignal));
    expect(create).toHaveBeenCalledWith({ recording_public_id: recordingResponse.public_id, purpose: "enroll", name: "Ayşe Demir" }, expect.any(String), expect.any(AbortSignal));
    expect(create.mock.calls[0][0]).not.toHaveProperty("profile_public_id");
    expect(job).toHaveBeenCalledWith(enrollJob.public_id, expect.any(AbortSignal));
    expect(take.dispose).toHaveBeenCalled();
    expect(enrolledCallback).toHaveBeenCalledTimes(1);
    expect(busy).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole("button", { name: "Yeni kayıt al" })).toBeInTheDocument();
  });

  it("adds a sample to the selected profile without sending a name", async () => {
    capture.stop.mockResolvedValue(recording(50));
    vi.spyOn(SpeakerService, "upload").mockResolvedValue(recordingResponse);
    const create = vi.spyOn(SpeakerService, "createJob").mockResolvedValue(enrollJob);
    vi.spyOn(SpeakerService, "job").mockResolvedValue({ ...enrollJob, status: "succeeded", result: enrolled });
    setup(profileFixture);
    expect(await screen.findByText("Ada")).toBeInTheDocument();
    expect(screen.queryByLabelText("Konuşmacı adı veya takma adı")).not.toBeInTheDocument();
    await record();
    fireEvent.click(screen.getByRole("button", { name: "Durdur ve doğrula" }));
    await screen.findByRole("heading", { name: "Ses profili kaydedildi" });
    expect(create.mock.calls[0][0]).toEqual({ recording_public_id: recordingResponse.public_id, purpose: "enroll", profile_public_id: profileFixture.public_id });
  });

  it.each([
    ["a silent microphone", 0, 48, "Mikrofondan ses alınamadı."],
    ["a recording shorter than ten seconds", 0.08, 8.6, "Kayıt çok kısa (8 sn)"],
  ])("does not upload %s and offers a new recording", async (_case, level, seconds, message) => {
    const take = recording(seconds); capture.stop.mockResolvedValue(take);
    const upload = vi.spyOn(SpeakerService, "upload");
    setup(profileFixture);
    await record(level);
    fireEvent.click(screen.getByRole("button", { name: "Durdur ve doğrula" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(upload).not.toHaveBeenCalled();
    expect(take.dispose).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Yeniden kaydet" })).toBeEnabled();
  });

  it("explains a quality rejection from the verification job and allows recording again", async () => {
    capture.stop.mockResolvedValue(recording(45));
    vi.spyOn(SpeakerService, "upload").mockResolvedValue(recordingResponse);
    vi.spyOn(SpeakerService, "createJob").mockResolvedValue(enrollJob);
    vi.spyOn(SpeakerService, "job").mockResolvedValue({ ...enrollJob, status: "failed", error: { code: "clipped_audio", message: "private diagnostic" } });
    const { enrolledCallback } = setup(profileFixture);
    await record();
    fireEvent.click(screen.getByRole("button", { name: "Durdur ve doğrula" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Seste aşırı kırpılma var.");
    expect(screen.getByText("Kayıt kabul edilmedi")).toBeInTheDocument();
    expect(screen.queryByText("private diagnostic")).not.toBeInTheDocument();
    expect(enrolledCallback).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Yeniden kaydet" }));
    await screen.findByRole("button", { name: "Durdur ve doğrula" });
    expect(capture.create).toHaveBeenCalledTimes(2);
  });

  it("keeps the recording after an upload failure and retries with the same idempotency key", async () => {
    const take = recording(52); capture.stop.mockResolvedValue(take);
    const upload = vi.spyOn(SpeakerService, "upload")
      .mockRejectedValueOnce(new ApiError(503, "Service unavailable", "inference_unavailable_proxy"))
      .mockResolvedValue(recordingResponse);
    vi.spyOn(SpeakerService, "createJob").mockResolvedValue(enrollJob);
    vi.spyOn(SpeakerService, "job").mockResolvedValue({ ...enrollJob, status: "succeeded", result: enrolled });
    setup(profileFixture);
    await record();
    fireEvent.click(screen.getByRole("button", { name: "Durdur ve doğrula" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("İşlem tamamlanamadı.");
    expect(take.dispose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
    await screen.findByRole("heading", { name: "Ses profili kaydedildi" });
    expect(upload).toHaveBeenCalledTimes(2);
    expect(upload.mock.calls[1][1]).toBe(upload.mock.calls[0][1]);
  });

  it("stops automatically at the limit and sends the completed recording", async () => {
    capture.stop.mockResolvedValue(recording(ENROLLMENT_MAX_SECONDS));
    const upload = vi.spyOn(SpeakerService, "upload").mockResolvedValue(recordingResponse);
    vi.spyOn(SpeakerService, "createJob").mockResolvedValue(enrollJob);
    vi.spyOn(SpeakerService, "job").mockResolvedValue({ ...enrollJob, status: "succeeded", result: enrolled });
    setup(profileFixture);
    await record();
    options().onLimit?.();
    expect(await screen.findByText("120 saniye sınırına ulaşıldı. Kayıt otomatik durduruldu ve doğrulamaya gönderiliyor.")).toBeInTheDocument();
    await waitFor(() => expect(upload).toHaveBeenCalledTimes(1));
  });

  it("keeps file upload as the path when the browser cannot record", async () => {
    capture.support.mockReturnValue("unsupported");
    setup(profileFixture);
    expect(await screen.findByRole("alert")).toHaveTextContent("ses dosyası yükleyin");
    expect(screen.getByRole("button", { name: "Kaydı başlat" })).toBeDisabled();
  });

  it("releases an active recording when the panel closes", async () => {
    const { busy } = setup(profileFixture);
    await record();
    cleanup();
    await waitFor(() => expect(capture.cancel).toHaveBeenCalled());
    expect(busy).toHaveBeenLastCalledWith(false);
  });
});
