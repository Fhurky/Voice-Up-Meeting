import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import SpeakerProfilesPage from "@/pages/SpeakerProfilesPage";
import { SpeakerService } from "@/services/speakers";
import { jobFixture, profileFixture } from "@/test/speakerFixtures";

const session = vi.hoisted(() => ({ writable: true }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: (permission: string) => session.writable || permission.endsWith(":read"), logout: vi.fn() }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); session.writable = true; });
function setup() { return render(<IntlProvider><MemoryRouter><SpeakerProfilesPage /></MemoryRouter></IntlProvider>); }
function profilePage(total = 1, offset = 0) { return { items: [profileFixture], total, offset, limit: 20 }; }
function profiles(total = 1) { return vi.spyOn(SpeakerService, "profiles").mockResolvedValue(profilePage(total)); }

describe("speaker profile operations", () => {
  it("requires explicit deletion and removes the stale profile from the next list", async () => {
    const list = profiles();
    const remove = vi.spyOn(SpeakerService, "remove").mockResolvedValue(undefined);
    setup();
    await screen.findByText("Ada");
    fireEvent.click(screen.getByRole("button", { name: "Sil" }));
    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toHaveFocus();
    list.mockResolvedValue({ ...profilePage(0), items: [] });
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
    list.mockResolvedValue({ ...profilePage(), items: [{ ...profileFixture, name: "Ada Yeni" }] });
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

describe("speaker profiles without a count quota", () => {
  it.each([50, 51, 100, 200, 201])("shows the server total of %i and permits another new profile", async (total) => {
    profiles(total);
    vi.spyOn(SpeakerService, "upload").mockResolvedValue({ public_id: jobFixture.recording_public_id, sha256: "a".repeat(64), size_bytes: 200, format: "WAV", duration_seconds: 20, created_at: jobFixture.created_at });
    const create = vi.spyOn(SpeakerService, "createJob").mockResolvedValue(jobFixture);
    setup();
    await screen.findByText(`Toplam profil: ${total}`);
    expect(screen.queryByText(/Aktif profiller \/ kapasite/)).not.toBeInTheDocument();
    const name = screen.getByLabelText("Konuşmacı adı veya takma adı");
    const file = screen.getByLabelText("Ses dosyası");
    expect(name).toBeEnabled();
    expect(file).toBeEnabled();
    fireEvent.change(name, { target: { value: "New speaker" } });
    fireEvent.change(file, { target: { files: [new File(["wav"], "voice.wav")] } });
    expect(screen.getByRole("button", { name: "Yükle ve profil oluştur" })).toBeEnabled();
    fireEvent.submit(screen.getByRole("form", { name: "Konuşmacı ses örneği" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ recording_public_id: jobFixture.recording_public_id, purpose: "enroll", name: "New speaker" }, expect.any(String), expect.any(AbortSignal)));
  });

  it.each(["tr", "en"])("keeps new enrollment available during list loading and failure in %s", async (locale) => {
    let reject: (reason: unknown) => void = () => {};
    const list = vi.spyOn(SpeakerService, "profiles").mockImplementation(() => new Promise((_, rejectRequest) => { reject = rejectRequest; }));
    setup();
    expect(await screen.findByLabelText("Ses dosyası")).toBeEnabled();
    if (locale === "en") {
      fireEvent.click(screen.getByRole("button", { name: "English" }));
      await screen.findByLabelText("Audio file");
    }
    const fileLabel = locale === "tr" ? "Ses dosyası" : "Audio file";
    const nameLabel = locale === "tr" ? "Konuşmacı adı veya takma adı" : "Speaker name or nickname";
    const submitLabel = locale === "tr" ? "Yükle ve profil oluştur" : "Upload and create profile";
    expect(screen.getByLabelText(nameLabel)).toBeEnabled();
    fireEvent.change(screen.getByLabelText(nameLabel), { target: { value: "New speaker" } });
    fireEvent.change(screen.getByLabelText(fileLabel), { target: { files: [new File(["wav"], "voice.wav")] } });
    expect(screen.getByRole("button", { name: submitLabel })).toBeEnabled();
    await act(async () => { reject(new TypeError("network")); });
    expect(screen.getByRole("alert")).toHaveTextContent(locale === "tr" ? "İşlem tamamlanamadı" : "The request could not be completed");
    expect(screen.getByLabelText(fileLabel)).toBeEnabled();
    expect(screen.getByLabelText(nameLabel)).toBeEnabled();
    expect(screen.getByRole("button", { name: submitLabel })).toBeEnabled();
    list.mockResolvedValue(profilePage(201));
    fireEvent.click(screen.getByRole("button", { name: locale === "tr" ? "Yenile" : "Refresh" }));
    await screen.findByText(locale === "tr" ? "Toplam profil: 201" : "Total profiles: 201");
    expect(screen.getByLabelText(fileLabel)).toBeEnabled();
  });

  it("keeps an existing-profile sample and new enrollment available through a failed refresh", async () => {
    const list = profiles(201);
    setup();
    await screen.findByText("Toplam profil: 201");
    fireEvent.click(screen.getByRole("button", { name: "Örnek ekle" }));
    expect(screen.getByLabelText("Ses dosyası")).toBeEnabled();
    expect(screen.queryByLabelText("Konuşmacı adı veya takma adı")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Ses dosyası"), { target: { files: [new File(["wav"], "voice.wav")] } });
    expect(screen.getByRole("button", { name: "Yükle ve örneği doğrula" })).toBeEnabled();
    list.mockRejectedValue(new TypeError("network"));
    fireEvent.click(screen.getByRole("button", { name: "Yenile" }));
    expect(screen.getByRole("button", { name: "Yükle ve örneği doğrula" })).toBeEnabled();
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: "Yükle ve örneği doğrula" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Vazgeç" }));
    expect(screen.getByLabelText("Ses dosyası")).toBeEnabled();
  });

  it("refreshes the total after deletion without treating it as room for a new profile", async () => {
    const list = profiles(201);
    vi.spyOn(SpeakerService, "remove").mockResolvedValue(undefined);
    setup();
    await screen.findByText("Toplam profil: 201");
    expect(screen.getByLabelText("Ses dosyası")).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Sil" }));
    list.mockResolvedValue({ ...profilePage(200), items: [] });
    fireEvent.click(screen.getByRole("button", { name: "Profili sil" }));
    await screen.findByText("Toplam profil: 200");
    expect(screen.getByLabelText("Ses dosyası")).toBeEnabled();
  });

  it("uses the server total on later pages while keeping a pre-filled new form available", async () => {
    const list = profiles(200);
    setup();
    await screen.findByText("Toplam profil: 200");
    fireEvent.change(screen.getByLabelText("Konuşmacı adı veya takma adı"), { target: { value: "New speaker" } });
    fireEvent.change(screen.getByLabelText("Ses dosyası"), { target: { files: [new File(["wav"], "voice.wav")] } });
    let resolve: (value: ReturnType<typeof profilePage>) => void = () => {};
    list.mockImplementation(() => new Promise((resolveRequest) => { resolve = resolveRequest; }));
    fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
    expect(screen.getByRole("button", { name: "Yükle ve profil oluştur" })).toBeEnabled();
    await act(async () => { resolve(profilePage(201, 20)); });
    await screen.findByText("Toplam profil: 201");
    expect(list).toHaveBeenLastCalledWith(20, expect.any(AbortSignal));
    expect(screen.getByRole("button", { name: "Yükle ve profil oluştur" })).toBeEnabled();
  });

  it("shows the total in English and permits creating another profile", async () => {
    profiles(201);
    setup();
    await screen.findByText("Toplam profil: 201");
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    await screen.findByText("Total profiles: 201");
    expect(screen.queryByText(/Profile capacity is full/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Audio file")).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Add sample" }));
    expect(screen.getByLabelText("Audio file")).toBeEnabled();
  });

  it("preserves the twenty-sample limit for an existing profile without blocking a new person", async () => {
    vi.spyOn(SpeakerService, "profiles").mockResolvedValue({ ...profilePage(201), items: [{ ...profileFixture, sample_count: 20 }] });
    setup();
    await screen.findByText("Toplam profil: 201");
    expect(screen.getByRole("button", { name: "Örnek ekle" })).toBeDisabled();
    expect(screen.getByText("Bu profilde 20 örnek sınırına ulaşıldı. Yeni örnek eklenmedi.")).toBeInTheDocument();
    expect(screen.getByLabelText("Ses dosyası")).toBeEnabled();
    expect(screen.getByLabelText("Konuşmacı adı veya takma adı")).toBeEnabled();
  });
});
