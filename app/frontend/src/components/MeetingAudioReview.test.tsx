import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IntlProvider, useIntl } from "@/contexts/IntlContext";
import { MeetingAudioReview } from "@/components/MeetingAudioReview";
import { MeetingService } from "@/services/meetings";
import { meeting, transcript } from "@/test/meetingFixtures";
import { ApiError } from "@/lib/apiClient";

beforeEach(() => {
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:preview");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const props = { meeting, turn: transcript, speakerName: "Ada", onClose: vi.fn() };
function LocaleControl() { const { setLocale } = useIntl(); return <button onClick={() => setLocale("en")}>English</button>; }
const node = (overrides: Partial<typeof props> = {}) => <IntlProvider><LocaleControl /><MeetingAudioReview {...props} {...overrides} /></IntlProvider>;
const audio = () => document.querySelector("audio");
describe("one bounded source audio review", () => {
  it.each(["tr", "en"])("loads the selected source time with native controls in %s", async (locale) => {
    const preview = vi.spyOn(MeetingService, "audioPreview").mockResolvedValue(new Blob(["wav"], { type: "audio/wav" }));
    render(node()); if (locale === "en") fireEvent.click(await screen.findByText("English"));
    await waitFor(() => expect(audio()).toHaveAttribute("src", "blob:preview"));
    expect(preview).toHaveBeenCalledWith(meeting.public_id, { start_seconds: 1.2, end_seconds: 5.8 }, expect.any(AbortSignal));
    expect(audio()).toHaveAttribute("controls");
    expect(await screen.findByText(locale === "tr" ? "Kaynak ses" : "Source audio")).toBeInTheDocument();
  });
  it("pages a long turn in 30-second windows clipped to the source and revokes each old URL", async () => {
    const preview = vi.spyOn(MeetingService, "audioPreview").mockResolvedValue(new Blob(["wav"]));
    render(node({ turn: { ...transcript, start_seconds: 10, end_seconds: 95 }, meeting: { ...meeting, duration_seconds: 75 } }));
    await waitFor(() => expect(audio()).not.toBeNull());
    expect(preview).toHaveBeenLastCalledWith(meeting.public_id, { start_seconds: 10, end_seconds: 40 }, expect.any(AbortSignal));
    fireEvent.click(screen.getByRole("button", { name: "Sonraki ses bölümü" }));
    await waitFor(() => expect(preview).toHaveBeenLastCalledWith(meeting.public_id, { start_seconds: 40, end_seconds: 70 }, expect.any(AbortSignal)));
    fireEvent.click(screen.getByRole("button", { name: "Sonraki ses bölümü" }));
    await waitFor(() => expect(preview).toHaveBeenLastCalledWith(meeting.public_id, { start_seconds: 70, end_seconds: 75 }, expect.any(AbortSignal)));
    expect(screen.getByRole("button", { name: "Sonraki ses bölümü" })).toBeDisabled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview");
  });
  it("aborts the old selection and ignores its late response", async () => {
    let finish: ((value: Blob) => void) | undefined;
    const preview = vi.spyOn(MeetingService, "audioPreview").mockImplementationOnce(() => new Promise<Blob>((resolve) => { finish = resolve; })).mockResolvedValue(new Blob(["new"]));
    const view = render(node()); await waitFor(() => expect(preview).toHaveBeenCalledOnce()); const firstSignal = preview.mock.calls[0][2];
    view.rerender(node({ turn: { ...transcript, public_id: "second", start_seconds: 8, end_seconds: 12 } }));
    await waitFor(() => expect(audio()).toHaveAttribute("src", "blob:preview"));
    expect(firstSignal?.aborted).toBe(true);
    await act(async () => finish?.(new Blob(["old"])));
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
  });
  it("aborts and revokes on unmount", async () => {
    const preview = vi.spyOn(MeetingService, "audioPreview").mockResolvedValue(new Blob(["wav"]));
    const view = render(node()); await waitFor(() => expect(audio()).not.toBeNull());
    view.unmount(); expect(preview.mock.calls[0][2]?.aborted).toBe(true); expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
  });
  it("offers retry after read failure and keeps source expiry distinct", async () => {
    const preview = vi.spyOn(MeetingService, "audioPreview").mockRejectedValueOnce(new TypeError("network")).mockRejectedValueOnce(new ApiError(410, "private", "recording_unavailable"));
    render(node()); fireEvent.click(await screen.findByRole("button", { name: "Tekrar dene" }));
    await screen.findByText("Kaynak sesin saklama süresi dolmuş veya dosya artık okunamıyor. Metni incelemeye devam edebilirsiniz.");
    expect(preview).toHaveBeenCalledTimes(2); expect(screen.queryByText("private")).toBeNull();
  });
  it("does not request unavailable or empty source ranges", async () => {
    const preview = vi.spyOn(MeetingService, "audioPreview");
    const view = render(node({ meeting: { ...meeting, source_available: false } }));
    await screen.findByText("Kaynak sesin saklama süresi dolmuş veya dosya artık okunamıyor. Metni incelemeye devam edebilirsiniz.");
    expect(preview).not.toHaveBeenCalled();
    view.rerender(node({ turn: { ...transcript, start_seconds: 90, end_seconds: 100 } }));
    expect(await screen.findByText("Bu satır için dinlenebilir bir kaynak bölümü bulunmuyor.")).toBeInTheDocument(); expect(preview).not.toHaveBeenCalled();
  });
  it.each([
    [new ApiError(403, "private", "forbidden"), "Bu ses kaydını dinleme yetkiniz yok. Oturumunuzu ve erişim izninizi kontrol edin."],
    [new ApiError(200, "private", "invalid_response"), "Ses bölümü geçerli biçimde okunamadı. Yeniden deneyin; hata sürerse başka bir bölümü inceleyin."],
  ])("shows a safe permission or format error without raw detail", async (error, message) => {
    vi.spyOn(MeetingService, "audioPreview").mockRejectedValue(error);
    render(node()); expect(await screen.findByText(message)).toBeInTheDocument(); expect(screen.queryByText("private")).toBeNull();
  });
});
