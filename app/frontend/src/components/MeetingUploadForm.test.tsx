import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import { MeetingUploadForm } from "@/components/MeetingUploadForm";
import { MeetingService } from "@/services/meetings";
import { meeting } from "@/test/meetingFixtures";
import { MeetingUploadContext } from "@/contexts/meetingUploadSelection";

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
});
