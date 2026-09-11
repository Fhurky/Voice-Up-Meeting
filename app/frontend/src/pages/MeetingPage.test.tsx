import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import MeetingPage from "@/pages/MeetingPage";
import MeetingsPage from "@/pages/MeetingsPage";
import { MeetingService } from "@/services/meetings";
import { meeting } from "@/test/meetingFixtures";

const session = vi.hoisted(() => ({ writable: true }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: (permission: string) => session.writable || permission.endsWith(":read"), logout: vi.fn() }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); session.writable = true; });
function setup() {
  vi.spyOn(MeetingService, "speakers").mockResolvedValue({ items: [], total: 0, offset: 0, limit: 20 });
  vi.spyOn(MeetingService, "transcript").mockResolvedValue({ items: [], total: 0, offset: 0, limit: 50, provisional: false });
  return render(<IntlProvider><MemoryRouter initialEntries={[`/meetings/${meeting.public_id}`]}><Routes>
    <Route path="/meetings/:publicId" element={<MeetingPage />} /><Route path="/meetings" element={<p>Meeting list route</p>} />
  </Routes></MemoryRouter></IntlProvider>);
}

describe("meeting detail boundaries", () => {
  it.each(["tr", "en"])("shows count disagreement without claiming a successful identity match in %s", async (locale) => {
    vi.spyOn(MeetingService, "get").mockResolvedValue({ ...meeting, observed_speakers: 6, count_mismatch: true });
    setup(); await screen.findByText("Weekly meeting");
    if (locale === "en") { fireEvent.click(screen.getByRole("button", { name: "English" })); await screen.findByRole("heading", { name: "Meeting result" }); }
    expect(screen.getByRole("alert")).toHaveTextContent(locale === "tr" ? "beklentiyle uyuşmuyor" : "differs from your expectation");
    expect(screen.getByText("6", { selector: "dd" })).toBeInTheDocument();
  });

  it("requires focused confirmation before deletion and returns to the meeting list", async () => {
    vi.spyOn(MeetingService, "get").mockResolvedValue(meeting);
    const remove = vi.spyOn(MeetingService, "remove").mockResolvedValue(undefined);
    setup(); await screen.findByText("Weekly meeting");
    fireEvent.click(screen.getByRole("button", { name: "Sil" }));
    expect(screen.getByRole("alertdialog")).toHaveFocus();
    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByText(/Kalıcı hafızaya eklenen kişiler korunur/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Toplantıyı sil" }));
    await screen.findByText("Meeting list route");
    expect(remove).toHaveBeenCalledWith(meeting.public_id, expect.any(AbortSignal));
  });

  it("keeps all mutation controls absent for a read-only user", async () => {
    session.writable = false;
    vi.spyOn(MeetingService, "get").mockResolvedValue({ ...meeting, status: "uploading", uploaded_bytes: 0 });
    setup(); await screen.findByText("Weekly meeting");
    expect(screen.queryByRole("button", { name: "Sil" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Analizi iptal et" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Toplantı ses dosyası")).not.toBeInTheDocument();
  });

  it("aborts an older status request when refreshing", async () => {
    const get = vi.spyOn(MeetingService, "get").mockImplementation(() => new Promise(() => {}));
    setup(); await screen.findByRole("button", { name: "Yenile" });
    await waitFor(() => expect(get).toHaveBeenCalledOnce());
    const previous = get.mock.calls[0]?.[1];
    fireEvent.click(screen.getByRole("button", { name: "Yenile" }));
    await waitFor(() => expect(get).toHaveBeenCalledTimes(2));
    expect(previous?.aborted).toBe(true);
  });
});

it("renders a read-only meeting list in both locales without an upload form", async () => {
  session.writable = false;
  vi.spyOn(MeetingService, "list").mockResolvedValue({ items: [meeting], total: 1, offset: 0, limit: 20 });
  render(<IntlProvider><MemoryRouter><MeetingsPage /></MemoryRouter></IntlProvider>);
  await screen.findByText("Weekly meeting");
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
  expect(screen.getByText(/Toplantıları görüntüleyebilirsiniz/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "English" }));
  await screen.findByText(/You can view meetings/);
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
});
