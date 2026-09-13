import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { IntlProvider, useIntl } from "@/contexts/IntlContext";
import { MeetingResults } from "@/components/MeetingResults";
import { MeetingService } from "@/services/meetings";
import { meeting, meetingSpeaker, transcript } from "@/test/meetingFixtures";
import { ApiError } from "@/lib/apiClient";
import { correctionSuggestion, correctionTurn, reviewModels, savedCorrection } from "@/test/correctionFixtures";

const session = vi.hoisted(() => ({ write: true, read: true, run: true, user: { public_id: "user", tenant_id: "tenant" } as { public_id: string; tenant_id: string } | null }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ user: session.user, hasPermission: (permission: string) => permission === "speaker_profiles:write" ? session.write : permission === "meeting_analysis:read" ? session.read : session.run }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); session.write = true; session.read = true; session.run = true; session.user = { public_id: "user", tenant_id: "tenant" }; });
function load() {
  vi.spyOn(MeetingService, "reviewModels").mockResolvedValue(reviewModels);
  const list = vi.spyOn(MeetingService, "speakers").mockResolvedValue({ items: [meetingSpeaker], total: 1, offset: 0, limit: 20 });
  vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [transcript], total: 1, offset: 0, limit: 50, provisional: false });
  return list;
}
function setup() { render(<IntlProvider><MeetingResults meeting={meeting} revision={0} /></IntlProvider>); }
function LocaleControl() { const { setLocale } = useIntl(); return <button onClick={() => setLocale("en")}>English</button>; }

describe("meeting result and memory distinctions", () => {
  it("shows a saved correction to a read-only reader without offering model or save actions", async () => {
    load(); session.run = false;
    const correction = await savedCorrection();
    vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [{ ...correctionTurn, correction }], total: 1, offset: 0, limit: 50, provisional: false });
    setup(); await screen.findByRole("button", { name: "Düzeltilmiş" });
    expect(document.querySelector("[data-corrected-text]")).toHaveTextContent(correction.corrected_text);
    expect(screen.queryByRole("button", { name: /Bağlama göre kontrol et/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Düzeltilmiş sürümü kaydet" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Orijinal" }));
    expect(document.querySelector("[data-original-text]")).toHaveTextContent(correctionTurn.text);
  });
  it("publishes the saved server version in the transcript while leaving source words intact", async () => {
    load(); const correction = await savedCorrection();
    vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [correctionTurn], total: 1, offset: 0, limit: 50, provisional: false });
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(await correctionSuggestion());
    vi.spyOn(MeetingService, "saveCorrection").mockResolvedValue(correction);
    setup(); fireEvent.click(await screen.findByRole("button", { name: /Bağlama göre kontrol et/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Kontrol et" }));
    fireEvent.click(await screen.findByRole("button", { name: "Düzeltilmiş sürümü kaydet" }));
    await screen.findByText("Düzeltilmiş sürüm kaydedildi. Özgün metin korundu.");
    await screen.findByRole("button", { name: "Düzeltilmiş" });
    expect(document.querySelector("[data-text-review]")).toBeNull();
    expect(document.querySelector("[data-corrected-text] ins")).toHaveTextContent("sürümü");
    fireEvent.click(screen.getByRole("button", { name: "Orijinal" }));
    expect(document.querySelector("[data-original-text]")).toHaveTextContent(correctionTurn.text);
  });
  it("offers contextual review only for a completed result with read and run permissions", async () => {
    load(); setup();
    expect(await screen.findByRole("button", { name: /Bağlama göre kontrol et/ })).toBeInTheDocument();
  });
  it.each(["read", "run", "provisional", "running"])("does not offer review when %s is unavailable", async (condition) => {
    load();
    if (condition === "read") session.read = false;
    if (condition === "run") session.run = false;
    if (condition === "provisional") vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [transcript], total: 1, offset: 0, limit: 50, provisional: true });
    render(<IntlProvider><MeetingResults meeting={condition === "running" ? { ...meeting, status: "running" } : meeting} revision={0} /></IntlProvider>);
    await screen.findByText(transcript.text); expect(screen.queryByRole("button", { name: /Bağlama göre kontrol et/ })).toBeNull();
  });
  it("keeps one active review, restores focus on close, and cancels on page and user changes", async () => {
    load();
    vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [transcript, { ...transcript, public_id: "next", ordinal: 1 }], total: 51, offset: 0, limit: 50, provisional: false });
    const preview = vi.spyOn(MeetingService, "correctionSuggestion").mockReturnValue(new Promise(() => undefined));
    const mounted = render(<IntlProvider><MeetingResults meeting={meeting} revision={0} /></IntlProvider>);
    const buttons = await screen.findAllByRole("button", { name: /Bağlama göre kontrol et/ });
    fireEvent.click(buttons[0]); fireEvent.click(await screen.findByRole("button", { name: "Kontrol et" })); await waitFor(() => expect(preview).toHaveBeenCalledTimes(1));
    fireEvent.click(buttons[1]); fireEvent.click(await screen.findByRole("button", { name: "Kontrol et" })); await waitFor(() => expect(preview).toHaveBeenCalledTimes(2));
    expect(preview.mock.calls[0][3]?.aborted).toBe(true); expect(document.querySelectorAll("[data-text-review]")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "İncelemeyi kapat" }));
    expect(buttons[1]).toHaveFocus(); expect(preview.mock.calls[1][3]?.aborted).toBe(true);
    fireEvent.click(buttons[0]); fireEvent.click(await screen.findByRole("button", { name: "Kontrol et" })); await waitFor(() => expect(preview).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
    expect(preview.mock.calls[2][3]?.aborted).toBe(true); expect(document.querySelector("[data-text-review]")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Önceki" }));
    expect(document.querySelector("[data-text-review]")).toBeNull();
    fireEvent.click((await screen.findAllByRole("button", { name: /Bağlama göre kontrol et/ }))[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Kontrol et" }));
    await waitFor(() => expect(preview).toHaveBeenCalledTimes(4));
    session.user = null; mounted.rerender(<IntlProvider><MeetingResults meeting={meeting} revision={0} /></IntlProvider>);
    expect(preview.mock.calls[3][3]?.aborted).toBe(true); expect(document.querySelector("[data-text-review]")).toBeNull();
  });
  it("displays a safe reason and explains that renaming cannot correct identity", async () => {
    const list = load();
    list.mockResolvedValue({ items: [{ ...meetingSpeaker, reason: "inconsistent_audio" }], total: 1, offset: 0, limit: 20 });
    setup(); await screen.findByText("Seçilen ses bölümlerinde tek ve tutarlı bir konuşmacı doğrulanamadı.");
    fireEvent.click(screen.getByRole("button", { name: "Adı değiştir" }));
    expect(screen.getByText("Adı değiştirmek ses kimliğini veya yanlış konuşmacı atamasını düzeltmez.")).toBeInTheDocument();
  });
  it("never renders an unknown reason code", async () => {
    const list = load(); list.mockResolvedValue({ items: [{ ...meetingSpeaker, reason: "private/path" }], total: 1, offset: 0, limit: 20 });
    setup(); await screen.findByText("Toplantıya başlayabiliriz.");
    expect(screen.queryByText("private/path")).toBeNull();
  });
  it("cleans selected audio on pagination and logout while leaving text readable", async () => {
    load(); vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [transcript], total: 51, offset: 0, limit: 50, provisional: false });
    const preview = vi.spyOn(MeetingService, "audioPreview").mockResolvedValue(new Blob(["wav"]));
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:selected");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const view = render(<IntlProvider><MeetingResults meeting={meeting} revision={0} /></IntlProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Bu bölümü dinle/ }));
    await waitFor(() => expect(document.querySelector("audio")).toHaveAttribute("src", "blob:selected"));
    fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
    await waitFor(() => expect(document.querySelector("audio")).toBeNull());
    expect(preview.mock.calls[0][2]?.aborted).toBe(true); expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:selected");
    fireEvent.click(screen.getByRole("button", { name: "Önceki" }));
    await screen.findByRole("button", { name: /Bu bölümü dinle/ });
    expect(document.querySelector("audio")).toBeNull();
    fireEvent.click(await screen.findByRole("button", { name: /Bu bölümü dinle/ }));
    await waitFor(() => expect(document.querySelector("audio")).toHaveAttribute("src", "blob:selected"));
    session.user = null;
    view.rerender(<IntlProvider><MeetingResults meeting={meeting} revision={0} /></IntlProvider>);
    expect(document.querySelector("audio")).toBeNull(); expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2);
    session.user = { public_id: "user", tenant_id: "tenant" };
  });
  it("clears old results and audio when the meeting or user scope changes", async () => {
    load(); vi.spyOn(MeetingService, "audioPreview").mockResolvedValue(new Blob(["wav"]));
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:selected"); vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const view = render(<IntlProvider><MeetingResults meeting={meeting} revision={0} /></IntlProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Bu bölümü dinle/ }));
    await waitFor(() => expect(document.querySelector("audio")).toHaveAttribute("src", "blob:selected"));
    vi.spyOn(MeetingService, "transcript").mockReturnValue(new Promise(() => undefined));
    view.rerender(<IntlProvider><MeetingResults meeting={{ ...meeting, public_id: "second-meeting" }} revision={0} /></IntlProvider>);
    expect(document.querySelector("audio")).toBeNull(); expect(screen.queryByText(transcript.text)).toBeNull();
    expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
  });
  it.each(["tr", "en"])("numbers speaker cards, transcript and editor from one in %s without changing API ordinals", async (locale) => {
    const list = load();
    const last = { ...meetingSpeaker, public_id: "de1f4383-a207-45be-b7f4-702f44b784ab", ordinal: 49 };
    list.mockResolvedValue({ items: [meetingSpeaker, last], total: 2, offset: 0, limit: 20 });
    vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [transcript, { ...transcript, public_id: "4642a306-77c3-436c-a65c-b895f692ed99", ordinal: 1, speaker_public_id: last.public_id, speaker_ordinal: 49 }], total: 2, offset: 0, limit: 50, provisional: false });
    render(<IntlProvider><LocaleControl /><MeetingResults meeting={meeting} revision={0} /></IntlProvider>);
    if (locale === "en") fireEvent.click(await screen.findByRole("button", { name: "English" }));
    const label = locale === "tr" ? "Konuşmacı" : "Speaker";
    await screen.findByRole("heading", { name: `${label} 1` });
    expect(screen.getByRole("heading", { name: `${label} 50` })).toBeInTheDocument();
    const rendered = Array.from(document.querySelectorAll("[data-transcript-id] strong"), (element) => element.textContent);
    expect(rendered).toEqual([`${label} 1`, `${label} 50`]);
    expect(screen.queryByText(`${label} 0`, { exact: true })).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: locale === "tr" ? "Adı değiştir" : "Rename" })[0]);
    expect(screen.getAllByRole("heading", { name: `${label} 1` })).toHaveLength(2);
    expect(meetingSpeaker.ordinal).toBe(0); expect(transcript.speaker_ordinal).toBe(0);
  });
  it("keeps short speech visible with its text and names it locally without creating a profile", async () => {
    const list = load();
    const rename = vi.spyOn(MeetingService, "rename").mockResolvedValue({ ...meetingSpeaker, display_name: "<b>Ada</b>", version: 2 });
    setup(); await screen.findByText("Toplantıya başlayabiliriz.");
    expect(screen.getByText("Hafızaya kaydedilmedi")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Adı değiştir" }));
    expect(screen.getByLabelText("Konuşmacı adı")).toHaveFocus();
    fireEvent.change(screen.getByLabelText("Konuşmacı adı"), { target: { value: "  <b>Ada</b>  " } });
    list.mockResolvedValue({ items: [{ ...meetingSpeaker, display_name: "<b>Ada</b>", version: 2 }], total: 1, offset: 0, limit: 20 });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
    await screen.findByRole("heading", { name: "<b>Ada</b>" });
    expect(document.querySelector("b")).toBeNull();
    expect(rename).toHaveBeenCalledWith(meeting.public_id, meetingSpeaker.public_id, { name: "<b>Ada</b>", version: 1, profile_updated_at: null }, expect.any(AbortSignal));
  });

  it("requires profile write permission to rename a linked profile", async () => {
    session.write = false;
    const list = load();
    list.mockResolvedValue({ items: [{ ...meetingSpeaker, decision: "recognized", profile_public_id: "saved-person", profile_name: "Ada" }], total: 1, offset: 0, limit: 20 });
    setup(); await screen.findByRole("heading", { name: "Ada" });
    expect(screen.getByText("Önceki toplantılardan tanındı")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Adı değiştir" })).not.toBeInTheDocument();
  });

  it("pages transcript results instead of loading the whole recording", async () => {
    load();
    const get = vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [transcript], total: 51, offset: 0, limit: 50, provisional: true });
    setup(); await screen.findByText("Toplantıya başlayabiliriz.");
    expect(screen.getByText(/Ara sonuçlar/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
    await waitFor(() => expect(get).toHaveBeenCalledWith(meeting.public_id, 50, expect.any(AbortSignal)));
  });

  it("refreshes a name conflict before allowing another edit with the current version", async () => {
    const list = load();
    const rename = vi.spyOn(MeetingService, "rename").mockRejectedValueOnce(new ApiError(409, "Conflict", "name_conflict"));
    setup(); await screen.findByText("Toplantıya başlayabiliriz.");
    fireEvent.click(screen.getByRole("button", { name: "Adı değiştir" }));
    fireEvent.change(screen.getByLabelText("Konuşmacı adı"), { target: { value: "Ada" } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
    await screen.findByText(/Bu ad başka bir işlemde değiştirildi/);
    const updated = { ...meetingSpeaker, version: 2, display_name: "Current name" };
    list.mockResolvedValue({ items: [updated], total: 1, offset: 0, limit: 20 });
    fireEvent.click(screen.getByRole("button", { name: "Yenile" }));
    await screen.findByRole("heading", { name: "Current name" });
    expect(screen.queryByLabelText("Konuşmacı adı")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Adı değiştir" }));
    expect(screen.getByLabelText("Konuşmacı adı")).toHaveValue("Current name");
    rename.mockResolvedValue({ ...updated, version: 3 });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
    await waitFor(() => expect(rename).toHaveBeenLastCalledWith(meeting.public_id, meetingSpeaker.public_id, { name: "Current name", version: 2, profile_updated_at: null }, expect.any(AbortSignal)));
  });
});
