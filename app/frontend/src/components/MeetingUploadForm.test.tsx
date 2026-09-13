import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import { MeetingUploadForm } from "@/components/MeetingUploadForm";
import { MeetingService } from "@/services/meetings";
import { meeting } from "@/test/meetingFixtures";
import { MeetingUploadContext } from "@/contexts/meetingUploadSelection";
import * as microphone from "@/lib/microphoneCapture";
import * as uploader from "@/services/meetingUpload";

const session = vi.hoisted(() => ({ memory: true }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: (permission: string) => permission !== "speaker_profiles:write" || session.memory }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
beforeEach(() => { session.memory = true; });
function setup() { render(<IntlProvider><MeetingUploadContext.Provider value={{ selection: null, setSelection: vi.fn() }}><MemoryRouter><Routes><Route path="/" element={<MeetingUploadForm />} /><Route path="/meetings/:publicId" element={<p>Meeting detail route</p>} /></Routes></MemoryRouter></MeetingUploadContext.Provider></IntlProvider>); }
async function fill() {
  fireEvent.change(await screen.findByLabelText("Toplantı adı"), { target: { value: "  Haftalık   toplantı  " } });
  fireEvent.change(screen.getByLabelText("Toplantı ses dosyası"), { target: { files: [new File(["wav"], "meeting.wav")] } });
}

describe("meeting upload form", () => {
  it("keeps optional participant details collapsed and exposes invalid fields for correction", async () => {
    setup();
    const participant = await screen.findByLabelText("Toplam katılımcı sayısı (isteğe bağlı)");
    const options = participant.closest("details");
    expect(options).not.toBeNull();
    expect(options).not.toHaveAttribute("open");
    fireEvent.invalid(participant);
    expect(options).toHaveAttribute("open");
    expect(screen.getByLabelText("Konuşan kişi sayısı (kesin biliniyorsa)")).toHaveValue(null);
  });

  it("keeps participant upper bound separate from exact active speaker count", async () => {
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("offline"));
    setup(); await fill();
    fireEvent.change(screen.getByLabelText("Toplam katılımcı sayısı (isteğe bağlı)"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Konuşan kişi sayısı (kesin biliniyorsa)"), { target: { value: "6" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Konuşan kişi sayısı toplam katılımcı sayısını aşamaz.");
    expect(create).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Konuşan kişi sayısı (kesin biliniyorsa)"), { target: { value: "3" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ title: "Haftalık toplantı", format: "WAV", size_bytes: 3,
      language: "tr", participant_count: 5, expected_speakers: 3, auto_enroll: true }, expect.any(String), expect.any(AbortSignal)));
  });

  it("uses the same creation key after a lost response and excludes memory without its permission", async () => {
    session.memory = false;
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("lost response"));
    setup(); await fill();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    const form = screen.getByRole("form", { name: "Toplantı kaydı yükleme" });
    fireEvent.submit(form); await screen.findByRole("alert");
    fireEvent.submit(form); await waitFor(() => expect(create).toHaveBeenCalledTimes(2));
    expect(create.mock.calls[0]?.[1]).toBe(create.mock.calls[1]?.[1]);
    expect(create.mock.calls[0]?.[0].auto_enroll).toBe(false);
  });

  it("opens the durable detail page before reading any file bytes", async () => {
    vi.spyOn(MeetingService, "create").mockResolvedValue({ ...meeting, status: "uploading" });
    setup(); await fill();
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await screen.findByText("Meeting detail route");
  });

  it("records without a file picker and reuses the same upload after a lost acknowledgement", async () => {
    const file = new File([new Uint8Array(100)], "microphone.wav"); const dispose = vi.fn(async () => {});
    const capture = { start: vi.fn(async () => {}), stop: vi.fn(async () => ({ file, durationSeconds: 30, dispose })), cancel: vi.fn(async () => {}) };
    vi.spyOn(microphone, "microphoneSupportError").mockReturnValue(null);
    vi.spyOn(microphone, "listMicrophoneDevices").mockResolvedValue([]);
    vi.spyOn(microphone, "createMicrophoneCapture").mockReturnValue(capture);
    const create = vi.spyOn(MeetingService, "create").mockResolvedValue({ ...meeting, size_bytes: file.size, status: "uploading" });
    const upload = vi.spyOn(uploader, "uploadMeeting").mockRejectedValueOnce(new Error("lost acknowledgement")).mockResolvedValueOnce({ ...meeting, status: "queued" });
    setup(); fireEvent.click(await screen.findByRole("button", { name: "Mikrofonla kaydet" }));
    expect(screen.queryByLabelText("Toplantı ses dosyası")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Toplantı adı"), { target: { value: "Mikrofon denemesi" } });
    fireEvent.change(screen.getByLabelText("Toplam katılımcı sayısı (isteğe bağlı)"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Konuşan kişi sayısı (kesin biliniyorsa)"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydı başlat" }));
    fireEvent.click(await screen.findByRole("button", { name: "Durdur ve analiz et" }));
    expect(await screen.findByRole("button", { name: "Analizi yeniden dene" })).toBeEnabled();
    expect(screen.getByLabelText("Toplantı adı")).toBeDisabled();
    expect(dispose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Analizi yeniden dene" }));
    await screen.findByText("Meeting detail route");
    expect(create.mock.calls[0]?.[0]).toMatchObject({ format: "WAV", size_bytes: 100, participant_count: 5, expected_speakers: 4, auto_enroll: true });
    expect(create.mock.calls[0]?.[1]).toBe(create.mock.calls[1]?.[1]);
    expect(upload.mock.calls.map((call) => call[1])).toEqual([file, file]);
    expect(capture.start).toHaveBeenCalledOnce(); expect(dispose).toHaveBeenCalledOnce();
  });

  it("cancels a late committed meeting after the recording was discarded during creation", async () => {
    let resolve!: (value: typeof meeting) => void;
    const pending = new Promise<typeof meeting>((done) => { resolve = done; });
    const file = new File(["wav"], "microphone.wav");
    vi.spyOn(microphone, "microphoneSupportError").mockReturnValue(null);
    vi.spyOn(microphone, "listMicrophoneDevices").mockResolvedValue([]);
    vi.spyOn(microphone, "createMicrophoneCapture").mockReturnValue({ start: async () => {}, stop: async () => ({ file, durationSeconds: 1, dispose: async () => {} }), cancel: async () => {} });
    const create = vi.spyOn(MeetingService, "create").mockReturnValue(pending);
    const cancel = vi.spyOn(MeetingService, "cancel").mockResolvedValue({ ...meeting, status: "cancelled" });
    const upload = vi.spyOn(uploader, "uploadMeeting");
    setup(); fireEvent.click(await screen.findByRole("button", { name: "Mikrofonla kaydet" }));
    fireEvent.change(screen.getByLabelText("Toplantı adı"), { target: { value: "Discarded recording" } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydı başlat" }));
    fireEvent.click(await screen.findByRole("button", { name: "Durdur ve analiz et" }));
    await waitFor(() => expect(create).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole("button", { name: "Kaydı iptal et" }));
    await screen.findByRole("button", { name: "Kaydı başlat" });
    expect(create.mock.calls[0]?.[2]?.aborted).toBe(false);
    resolve({ ...meeting, status: "uploading" });
    await waitFor(() => expect(cancel).toHaveBeenCalledWith(meeting.public_id));
    expect(upload).not.toHaveBeenCalled(); expect(screen.queryByText("Meeting detail route")).not.toBeInTheDocument();
  });
});
