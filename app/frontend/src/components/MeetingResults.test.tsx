import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { IntlProvider, useIntl } from "@/contexts/IntlContext";
import { MeetingResults } from "@/components/MeetingResults";
import { MeetingService } from "@/services/meetings";
import { meeting, meetingSpeaker, transcript } from "@/test/meetingFixtures";
import { ApiError } from "@/lib/apiClient";

const session = vi.hoisted(() => ({ write: true, run: true }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: (permission: string) => permission === "speaker_profiles:write" ? session.write : session.run }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); session.write = true; session.run = true; });
function load() {
  const list = vi.spyOn(MeetingService, "speakers").mockResolvedValue({ items: [meetingSpeaker], total: 1, offset: 0, limit: 20 });
  vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [transcript], total: 1, offset: 0, limit: 50, provisional: false });
  return list;
}
function setup() { render(<IntlProvider><MeetingResults meeting={meeting} revision={0} /></IntlProvider>); }
function LocaleControl() { const { setLocale } = useIntl(); return <button onClick={() => setLocale("en")}>English</button>; }

describe("meeting result and memory distinctions", () => {
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
