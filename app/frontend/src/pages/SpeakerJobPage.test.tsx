import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import SpeakerJobPage from "@/pages/SpeakerJobPage";
import { SpeakerService } from "@/services/speakers";
import { jobFixture, resultFixture } from "@/test/speakerFixtures";

vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: () => true, logout: vi.fn() }) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });
function setup() { return render(<IntlProvider><MemoryRouter initialEntries={[`/speaker-jobs/${jobFixture.public_id}`]}><Routes><Route path="/speaker-jobs/:publicId" element={<SpeakerJobPage />} /></Routes></MemoryRouter></IntlProvider>); }

describe("saved job status", () => {
  it.each(["tr", "en"])("explains a saved terminal profile_limit failure in %s as a historical rule without changing the job", async (locale) => {
    const saved = { ...jobFixture, purpose: "enroll" as const, status: "failed" as const, error: { code: "profile_limit", message: "private backend diagnostic" } };
    const get = vi.spyOn(SpeakerService, "job").mockResolvedValue(saved);
    const create = vi.spyOn(SpeakerService, "createJob");
    setup();
    await screen.findByText("Başarısız");
    if (locale === "en") {
      fireEvent.click(screen.getByRole("button", { name: "English" }));
      await screen.findByText("Failed");
    }
    expect(screen.getByRole("alert")).toHaveTextContent(locale === "tr" ? "Bu kayıt, o sırada geçerli olan profil sınırı nedeniyle reddedildi. Yeni profil oluşturulmadı. Artık yeni bir kayıt başlatabilirsiniz." : "This enrollment was rejected under the profile limit in effect at the time. No new profile was created. You can now start a new enrollment.");
    expect(screen.queryByText("private backend diagnostic")).not.toBeInTheDocument();
    expect(get).toHaveBeenCalledTimes(1);
    expect(create).not.toHaveBeenCalled();
    expect(saved.error.code).toBe("profile_limit");
    expect(saved.status).toBe("failed");
  });

  it("loads a job by its public URL after refresh without starting it again", async () => {
    const get = vi.spyOn(SpeakerService, "job").mockResolvedValue({ ...jobFixture, status: "succeeded", result: resultFixture });
    const create = vi.spyOn(SpeakerService, "createJob");
    const first = setup();
    await screen.findByRole("heading", { name: "Konuşmacı tanındı" });
    first.unmount();
    setup();
    await screen.findByRole("heading", { name: "Konuşmacı tanındı" });
    expect(get).toHaveBeenCalledTimes(2);
    expect(get.mock.calls[1][0]).toBe(jobFixture.public_id);
    expect(create).not.toHaveBeenCalled();
  });

  it("polls pending jobs serially and stops at the terminal failure", async () => {
    const get = vi.spyOn(SpeakerService, "job")
      .mockResolvedValueOnce(jobFixture)
      .mockResolvedValueOnce({ ...jobFixture, status: "running" })
      .mockResolvedValue({ ...jobFixture, status: "failed", error: { code: "target_mismatch", message: "safe diagnostic" } });
    setup();
    await screen.findByText("Sırada");
    // The first scheduled timer predates fake timers; wait for that real status transition.
    await screen.findByText("İşleniyor", {}, { timeout: 4_000 });
    await screen.findByText("Başarısız", {}, { timeout: 4_000 });
    expect(screen.getByRole("alert")).toHaveTextContent("Mevcut profil değiştirilmedi");
    expect(get).toHaveBeenCalledTimes(3);
    vi.useFakeTimers();
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(get).toHaveBeenCalledTimes(3);
  }, 10_000);
});
