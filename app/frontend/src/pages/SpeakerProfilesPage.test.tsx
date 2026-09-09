import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import SpeakerProfilesPage from "@/pages/SpeakerProfilesPage";
import { SpeakerService } from "@/services/speakers";
import { profileFixture } from "@/test/speakerFixtures";

const session = vi.hoisted(() => ({ writable: true }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: (permission: string) => session.writable || permission.endsWith(":read"), logout: vi.fn() }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); session.writable = true; });
function setup() { return render(<IntlProvider><MemoryRouter><SpeakerProfilesPage /></MemoryRouter></IntlProvider>); }
function profiles() { return vi.spyOn(SpeakerService, "profiles").mockResolvedValue({ items: [profileFixture], total: 1, offset: 0, limit: 20 }); }

describe("speaker profile operations", () => {
  it("requires explicit deletion and removes the stale profile from the next list", async () => {
    const list = profiles();
    const remove = vi.spyOn(SpeakerService, "remove").mockResolvedValue(undefined);
    setup();
    await screen.findByText("Ada");
    fireEvent.click(screen.getByRole("button", { name: "Sil" }));
    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toHaveFocus();
    list.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 20 });
    fireEvent.click(screen.getByRole("button", { name: "Profili sil" }));
    await screen.findByRole("heading", { name: "Henüz konuşmacı profili yok" });
    expect(remove).toHaveBeenCalledWith(profileFixture.public_id, expect.any(AbortSignal));
    expect(screen.queryByText("Ada")).not.toBeInTheDocument();
  });

  it("normalizes a rename and updates the visible profile from the server", async () => {
    const list = profiles();
    const rename = vi.spyOn(SpeakerService, "rename").mockResolvedValue({ ...profileFixture, name: "Ada Yeni" });
    setup();
    await screen.findByText("Ada");
    fireEvent.click(screen.getByRole("button", { name: "Adı değiştir" }));
    const input = screen.getAllByLabelText("Konuşmacı adı veya takma adı").find((element) => element.id === "rename-profile");
    expect(input).toBeDefined();
    fireEvent.change(input!, { target: { value: "  Ada   Yeni  " } });
    list.mockResolvedValue({ items: [{ ...profileFixture, name: "Ada Yeni" }], total: 1, offset: 0, limit: 20 });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
    await screen.findByRole("heading", { name: "Ada Yeni" });
    expect(rename).toHaveBeenCalledWith(profileFixture.public_id, "Ada Yeni", expect.any(AbortSignal));
  });

  it("does not offer write or enrollment controls to a read-only user", async () => {
    session.writable = false;
    profiles();
    setup();
    await screen.findByText("Ada");
    expect(screen.queryByRole("button", { name: "Sil" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Örnek ekle" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Ses dosyası")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Ses örneği eklemek için profil yazma/)).toBeInTheDocument());
  });
});
