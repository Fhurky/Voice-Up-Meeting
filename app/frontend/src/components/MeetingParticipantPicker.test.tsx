import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { IntlProvider } from "@/contexts/IntlContext";
import { MAX_LISTED_PARTICIPANTS, MeetingParticipantPicker } from "@/components/MeetingParticipantPicker";
import { SpeakerService, type SpeakerProfile } from "@/services/speakers";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function profile(index: number, name: string): SpeakerProfile {
  return { public_id: `p-${index}`, name, sample_count: 1, model_id: "model", model_revision: "revision", created_at: "2026-10-29T10:00:00Z", updated_at: "2026-10-29T10:00:00Z" };
}

function Harness({ initial = [] as string[] }) {
  const [selected, setSelected] = useState(initial);
  return <IntlProvider><MeetingParticipantPicker selected={selected} disabled={false} onChange={setSelected} /></IntlProvider>;
}

describe("meeting participant picker", () => {
  it("loads every page, sorts and filters names with Turkish casing", async () => {
    const pages = vi.spyOn(SpeakerService, "profiles")
      .mockResolvedValueOnce({ items: [profile(1, "Zeynep"), profile(2, "Şule")], total: 3, offset: 0, limit: 2 })
      .mockResolvedValueOnce({ items: [profile(3, "İsmail")], total: 3, offset: 2, limit: 2 });
    render(<Harness />);
    const boxes = await screen.findAllByRole("checkbox");
    expect(boxes.map((box) => box.closest("label")?.textContent)).toEqual(["İsmail", "Şule", "Zeynep"]);
    expect(pages).toHaveBeenNthCalledWith(2, 2, expect.any(AbortSignal));
    fireEvent.change(screen.getByLabelText("Kişi ara"), { target: { value: "şu" } });
    expect(screen.getAllByRole("checkbox")).toHaveLength(1);
    fireEvent.click(screen.getByRole("checkbox", { name: "Şule" }));
    expect(screen.getByText("1 kişi seçildi.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Kişi ara"), { target: { value: "yok" } });
    expect(screen.getByText("Aramayla eşleşen kişi yok.")).toBeInTheDocument();
  });

  it("disables further choices at the participant limit but keeps selected ones removable", async () => {
    const profiles = Array.from({ length: MAX_LISTED_PARTICIPANTS + 1 }, (_, index) => profile(index, `Kişi ${String(index).padStart(2, "0")}`));
    vi.spyOn(SpeakerService, "profiles").mockResolvedValue({ items: profiles, total: profiles.length, offset: 0, limit: 100 });
    render(<Harness initial={profiles.slice(0, MAX_LISTED_PARTICIPANTS).map((item) => item.public_id)} />);
    const last = await screen.findByRole("checkbox", { name: `Kişi ${MAX_LISTED_PARTICIPANTS}` });
    expect(last).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "Kişi 00" })).toBeEnabled();
    expect(screen.getByText(/En fazla 50 kişi seçilebilir\./)).toBeInTheDocument();
  });

  it("reports empty and failed loads without blocking the meeting", async () => {
    vi.spyOn(SpeakerService, "profiles").mockResolvedValueOnce({ items: [], total: 0, offset: 0, limit: 20 });
    render(<Harness />);
    expect(await screen.findByText("Henüz kayıtlı kişi yok; liste olmadan devam edebilirsiniz.")).toBeInTheDocument();
    cleanup();
    vi.spyOn(SpeakerService, "profiles").mockRejectedValueOnce(new Error("offline"));
    render(<Harness />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Kayıtlı kişiler yüklenemedi");
  });
});
