import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import { MeetingService } from "@/services/meetings";
import { SpeakerService } from "@/services/speakers";
import { meeting } from "@/test/meetingFixtures";
import { profileFixture } from "@/test/speakerFixtures";
import HomePage from "@/pages/HomePage";

const session = vi.hoisted(() => ({ user: { username: "Alex", public_id: "user-a", tenant_id: "tenant-a" }, permissions: ["meeting_analysis:read", "meeting_analysis:run", "speaker_profiles:read"] }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ user: session.user, logout: vi.fn(), hasPermission: (permission: string) => session.permissions.includes(permission) }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); session.user = { username: "Alex", public_id: "user-a", tenant_id: "tenant-a" }; session.permissions = ["meeting_analysis:read", "meeting_analysis:run", "speaker_profiles:read"]; });
function view() { return <IntlProvider><MemoryRouter><HomePage /></MemoryRouter></IntlProvider>; }
function setup() { return render(view()); }
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((finish) => { resolve = finish; });
  return { promise, resolve };
}

describe("workspace overview", () => {
  it("shows server totals, real recent records and localized navigation", async () => {
    vi.spyOn(MeetingService, "list").mockResolvedValue({ items: [meeting], total: 42, offset: 0, limit: 20 });
    vi.spyOn(SpeakerService, "profiles").mockResolvedValue({ items: [profileFixture], total: 35, offset: 0, limit: 20 });
    setup();
    expect(await screen.findByRole("link", { name: /Weekly meeting/ })).toHaveAttribute("href", `/meetings/${meeting.public_id}`);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("35")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "İçeriğe geç" })).toHaveAttribute("href", "#workspace-content");
    expect(within(screen.getByRole("navigation", { name: "Ana gezinme" })).getByRole("link", { name: "Ana sayfa" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    await screen.findByRole("heading", { name: "Your workspace", level: 1 });
    expect(MeetingService.list).toHaveBeenCalledTimes(1);
  });
  it("never reads or exposes unauthorized data and creation actions", async () => {
    session.permissions = [];
    const meetings = vi.spyOn(MeetingService, "list");
    const profiles = vi.spyOn(SpeakerService, "profiles");
    setup(); await screen.findByRole("heading", { level: 1 });
    expect(meetings).not.toHaveBeenCalled(); expect(profiles).not.toHaveBeenCalled();
    expect(screen.queryByRole("link", { name: "Toplantı kaydı yükle" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Konuşmacılar/ })).not.toBeInTheDocument();
  });
  it("shows a load failure without a fabricated zero and retries the real service", async () => {
    session.permissions = ["meeting_analysis:read"];
    const list = vi.spyOn(MeetingService, "list").mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ items: [], total: 0, offset: 0, limit: 20 });
    setup(); await screen.findByRole("alert");
    expect(screen.queryByText("0")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
    await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("0")).toBeInTheDocument();
    expect(screen.getByText("Henüz toplantı kaydı yok.")).toBeInTheDocument();
  });
  it.each(["public_id", "tenant_id"] as const)("removes previous data while a changed %s loads", async (field) => {
    const freshMeetings = deferred<Awaited<ReturnType<typeof MeetingService.list>>>();
    const freshProfiles = deferred<Awaited<ReturnType<typeof SpeakerService.profiles>>>();
    vi.spyOn(MeetingService, "list").mockResolvedValueOnce({ items: [meeting], total: 42, offset: 0, limit: 20 })
      .mockReturnValueOnce(freshMeetings.promise);
    vi.spyOn(SpeakerService, "profiles").mockResolvedValueOnce({ items: [profileFixture], total: 35, offset: 0, limit: 20 })
      .mockReturnValueOnce(freshProfiles.promise);
    const rendered = setup();
    await screen.findByRole("link", { name: /Weekly meeting/ });
    await screen.findByText("35");
    session.user = { ...session.user, [field]: `${field}-b` };
    rendered.rerender(view());
    expect(screen.queryByRole("link", { name: /Weekly meeting/ })).not.toBeInTheDocument();
    expect(screen.queryByText("42")).not.toBeInTheDocument();
    expect(screen.queryByText("35")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Yükleniyor");
    await act(async () => {
      freshMeetings.resolve({ items: [{ ...meeting, title: "Current scope meeting" }], total: 1, offset: 0, limit: 20 });
      freshProfiles.resolve({ items: [], total: 0, offset: 0, limit: 20 });
    });
    expect(await screen.findByRole("link", { name: /Current scope meeting/ })).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });
  it("removes previous errors when read permissions are revoked", async () => {
    const list = vi.spyOn(MeetingService, "list").mockRejectedValue(new Error("offline"));
    const profiles = vi.spyOn(SpeakerService, "profiles").mockRejectedValue(new Error("offline"));
    const rendered = setup();
    await screen.findByRole("alert");
    session.permissions = [];
    rendered.rerender(view());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(list).toHaveBeenCalledTimes(1);
    expect(profiles).toHaveBeenCalledTimes(1);
  });
  it("ignores a late response from the previous tenant", async () => {
    session.permissions = ["meeting_analysis:read"];
    const previous = deferred<Awaited<ReturnType<typeof MeetingService.list>>>();
    const list = vi.spyOn(MeetingService, "list").mockReturnValueOnce(previous.promise)
      .mockResolvedValueOnce({ items: [{ ...meeting, title: "Current tenant meeting" }], total: 1, offset: 0, limit: 20 });
    const rendered = setup();
    await waitFor(() => expect(list).toHaveBeenCalledTimes(1));
    session.user = { ...session.user, tenant_id: "tenant-b" };
    rendered.rerender(view());
    await screen.findByRole("link", { name: /Current tenant meeting/ });
    await act(async () => { previous.resolve({ items: [meeting], total: 42, offset: 0, limit: 20 }); });
    expect(screen.queryByRole("link", { name: /Weekly meeting/ })).not.toBeInTheDocument();
    expect(screen.queryByText("42")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Current tenant meeting/ })).toBeInTheDocument();
  });
});
