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
import { SpeakerService } from "@/services/speakers";

const session = vi.hoisted(() => ({ memory: true, profiles: true }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: (permission: string) => (permission !== "speaker_profiles:write" || session.memory) && (permission !== "speaker_profiles:read" || session.profiles) }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
beforeEach(() => { session.memory = true; session.profiles = true; vi.spyOn(SpeakerService, "profiles").mockResolvedValue({ items: [], total: 0, offset: 0, limit: 20 }); });
function setup() { render(<IntlProvider><MeetingUploadContext.Provider value={{ selection: null, setSelection: vi.fn() }}><MemoryRouter><Routes><Route path="/" element={<MeetingUploadForm />} /><Route path="/meetings/:publicId" element={<p>Meeting detail route</p>} /></Routes></MemoryRouter></MeetingUploadContext.Provider></IntlProvider>); }
async function fill() {
  fireEvent.change(await screen.findByLabelText("Toplantı adı"), { target: { value: "  Haftalık   toplantı  " } });
  fireEvent.change(screen.getByLabelText("Toplantı ses veya video dosyası"), { target: { files: [new File(["wav"], "meeting.wav")] } });
}

describe("meeting upload form", () => {
  it("keeps optional participant details collapsed and exposes invalid fields for correction", async () => {
    setup();
    const participant = await screen.findByLabelText("En çok kişi sayısı (isteğe bağlı)");
    const options = participant.closest("details");
    expect(options).not.toBeNull();
    expect(options).not.toHaveAttribute("open");
    fireEvent.invalid(participant);
    expect(options).toHaveAttribute("open");
    expect(screen.getByLabelText("Tahmini konuşan kişi sayısı (isteğe bağlı)")).toHaveValue(null);
  });

  it("sends subject and questions in order, ignoring blank rows, and rejects a repeated question", async () => {
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("offline"));
    setup(); await fill();
    fireEvent.change(screen.getByLabelText("Toplantı konusu (isteğe bağlı)"), { target: { value: "  Bütçe   planı " } });
    const add = screen.getByRole("button", { name: "Soru ekle" });
    fireEvent.click(add); fireEvent.click(add); fireEvent.click(add);
    fireEvent.change(screen.getByLabelText("1. soru"), { target: { value: "Bütçe onaylandı mı?" } });
    fireEvent.change(screen.getByLabelText("3. soru"), { target: { value: "bütçe  onaylandı mı?" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Aynı soru birden çok kez girilmiş.");
    expect(create).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("3. soru"), { target: { value: "Kim sorumlu?" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create.mock.calls[0]?.[0]).toMatchObject({ subject: "Bütçe planı", questions: ["Bütçe onaylandı mı?", "Kim sorumlu?"] });
  });

  it("limits questions to twenty and returns focus when a question is removed", async () => {
    setup(); await fill();
    const add = screen.getByRole("button", { name: "Soru ekle" });
    for (let index = 0; index < 20; index++) fireEvent.click(add);
    expect(add).toBeDisabled();
    expect(screen.getByLabelText("20. soru")).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "20. soruyu kaldır" }));
    expect(screen.queryByLabelText("20. soru")).not.toBeInTheDocument();
    expect(add).toBeEnabled();
    expect(add).toHaveFocus();
  });

  it("keeps voice memory off until the person turns it on", async () => {
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("offline"));
    setup(); await fill();
    const memory = screen.getByRole("checkbox", { name: "Yeterli temiz sesi olan yeni kişileri hafızaya ekle" });
    expect(memory).not.toBeChecked();
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
    expect(create.mock.calls[0]?.[0].auto_enroll).toBe(false);
    fireEvent.click(memory);
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await waitFor(() => expect(create).toHaveBeenCalledTimes(2));
    expect(create.mock.calls[1]?.[0].auto_enroll).toBe(true);
  });

  it("uploads only extracted audio from an MP4 and does not decode it again on retry", async () => {
    const decode = vi.fn(async () => ({ length: 2, duration: 2 / 16000, numberOfChannels: 1, getChannelData: () => Float32Array.of(0.5, -0.5) }));
    vi.stubGlobal("OfflineAudioContext", class { decodeAudioData = decode; });
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("offline"));
    setup();
    fireEvent.change(await screen.findByLabelText("Toplantı adı"), { target: { value: "Video toplantı" } });
    const video = new File([new Uint8Array(8)], "kayit.mp4", { type: "video/mp4", lastModified: 5 });
    Object.defineProperty(video, "arrayBuffer", { value: async () => new ArrayBuffer(8) });
    fireEvent.change(screen.getByLabelText("Toplantı ses veya video dosyası"), { target: { files: [video] } });
    const form = screen.getByRole("form", { name: "Toplantı kaydı yükleme" });
    fireEvent.submit(form);
    await screen.findByRole("alert");
    expect(create.mock.calls[0]?.[0]).toMatchObject({ format: "WAV", size_bytes: 48 });
    fireEvent.submit(form);
    await waitFor(() => expect(create).toHaveBeenCalledTimes(2));
    expect(decode).toHaveBeenCalledTimes(1);
    expect(create.mock.calls[0]?.[1]).toBe(create.mock.calls[1]?.[1]);
    vi.unstubAllGlobals();
  });

  it("explains a video without decodable audio and creates nothing", async () => {
    vi.stubGlobal("OfflineAudioContext", class { decodeAudioData = async () => { throw new DOMException("bad", "EncodingError"); }; });
    const create = vi.spyOn(MeetingService, "create");
    setup();
    fireEvent.change(await screen.findByLabelText("Toplantı adı"), { target: { value: "Video toplantı" } });
    const video = new File([new Uint8Array(8)], "kayit.mp4", { type: "video/mp4" });
    Object.defineProperty(video, "arrayBuffer", { value: async () => new ArrayBuffer(8) });
    fireEvent.change(screen.getByLabelText("Toplantı ses veya video dosyası"), { target: { files: [video] } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Bu dosyadan ses çıkarılamadı");
    expect(create).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("warns that processing is slow only when the installation runs on the CPU", async () => {
    const mode = vi.spyOn(MeetingService, "processingMode").mockResolvedValue({ processing_device: "cpu" });
    setup();
    expect(await screen.findByRole("status")).toHaveTextContent("GPU olmadan çalışıyor");
    expect(mode).toHaveBeenCalledTimes(1);
    cleanup();
    mode.mockResolvedValue({ processing_device: "gpu" });
    setup();
    await screen.findByLabelText("Toplantı adı");
    await waitFor(() => expect(mode).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(/GPU olmadan çalışıyor/)).not.toBeInTheDocument();
  });

  it("keeps the form usable when the processing mode cannot be read", async () => {
    vi.spyOn(MeetingService, "processingMode").mockRejectedValue(new Error("offline"));
    setup();
    await screen.findByLabelText("Toplantı adı");
    expect(screen.queryByText(/GPU olmadan çalışıyor/)).not.toBeInTheDocument();
  });

  it("sends empty meeting details when nothing was entered", async () => {
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("offline"));
    setup(); await fill();
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create.mock.calls[0]?.[0]).toMatchObject({ subject: null, questions: [] });
  });

  it("keeps the maximum separate from the non-binding speaker estimate", async () => {
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("offline"));
    setup(); await fill();
    fireEvent.change(screen.getByLabelText("En çok kişi sayısı (isteğe bağlı)"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Tahmini konuşan kişi sayısı (isteğe bağlı)"), { target: { value: "6" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tahmini kişi sayısı en çok kişi sayısını aşamaz.");
    expect(create).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Tahmini konuşan kişi sayısı (isteğe bağlı)"), { target: { value: "3" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ title: "Haftalık toplantı", format: "WAV", size_bytes: 3,
      language: "tr", participant_count: 5, expected_speakers: 3, auto_enroll: false, participant_profile_ids: [], subject: null, questions: [] }, expect.any(String), expect.any(AbortSignal)));
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
    expect(screen.queryByLabelText("Toplantı ses veya video dosyası")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Toplantı adı"), { target: { value: "Mikrofon denemesi" } });
    fireEvent.change(screen.getByLabelText("En çok kişi sayısı (isteğe bağlı)"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Tahmini konuşan kişi sayısı (isteğe bağlı)"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydı başlat" }));
    fireEvent.click(await screen.findByRole("button", { name: "Durdur ve analiz et" }));
    expect(await screen.findByRole("button", { name: "Analizi yeniden dene" })).toBeEnabled();
    expect(screen.getByLabelText("Toplantı adı")).toBeDisabled();
    expect(dispose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Analizi yeniden dene" }));
    await screen.findByText("Meeting detail route");
    expect(create.mock.calls[0]?.[0]).toMatchObject({ format: "WAV", size_bytes: 100, participant_count: 5, expected_speakers: 4, auto_enroll: false });
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

  it("sends the selected saved participants and keeps the list within the participant bound", async () => {
    vi.spyOn(SpeakerService, "profiles").mockResolvedValue({ items: [profile("p-ayse", "Ayşe"), profile("p-can", "Can")], total: 2, offset: 0, limit: 20 });
    const create = vi.spyOn(MeetingService, "create").mockRejectedValue(new Error("offline"));
    setup(); await fill();
    fireEvent.click(await screen.findByRole("checkbox", { name: "Ayşe" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Can" }));
    expect(screen.getByText("2 kişi seçildi.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("En çok kişi sayısı (isteğe bağlı)"), { target: { value: "1" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Seçilen kişi sayısı katılımcı üst sınırından fazla olamaz.");
    expect(create).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("En çok kişi sayısı (isteğe bağlı)"), { target: { value: "" } });
    fireEvent.submit(screen.getByRole("form", { name: "Toplantı kaydı yükleme" }));
    await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
    expect(create.mock.calls[0]?.[0].participant_profile_ids).toEqual(["p-ayse", "p-can"]);
  });

  it("explains the missing participant list instead of loading profiles without permission", async () => {
    session.profiles = false;
    const profiles = vi.spyOn(SpeakerService, "profiles");
    setup();
    expect(await screen.findByText("Kayıtlı kişileri görme izniniz olmadığı için katılımcı listesi seçilemez.")).toBeInTheDocument();
    expect(profiles).not.toHaveBeenCalled();
  });
});

function profile(public_id: string, name: string) {
  return { public_id, name, sample_count: 1, model_id: "model", model_revision: "revision", created_at: "2026-10-29T10:00:00Z", updated_at: "2026-10-29T10:00:00Z" };
}
