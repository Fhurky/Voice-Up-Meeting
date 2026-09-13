import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StrictMode } from "react";
import { IntlProvider, useIntl } from "@/contexts/IntlContext";
import { MeetingTextReview } from "@/components/MeetingTextReview";
import { MeetingService, type CorrectionSuggestion } from "@/services/meetings";
import { ApiError } from "@/lib/apiClient";
import { meeting } from "@/test/meetingFixtures";
import { correctionTurn as turn, correctionSuggestion as response, reviewModels, savedCorrection } from "@/test/correctionFixtures";

beforeEach(() => { vi.spyOn(MeetingService, "reviewModels").mockResolvedValue(reviewModels); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
function LocaleControl() { const { setLocale } = useIntl(); return <button onClick={() => setLocale("en")}>English</button>; }
function view(source = turn, onSaved = vi.fn()) {
  return render(<IntlProvider><LocaleControl /><MeetingTextReview meetingId={meeting.public_id} turn={source} onClose={vi.fn()} onSaved={onSaved} /></IntlProvider>);
}
async function check() { fireEvent.click(await screen.findByRole("button", { name: "Kontrol et" })); }

describe("selected-model word review and explicit save", () => {
  it("loads every model under StrictMode without inference until the explicit action", async () => {
    const suggest = vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(await response());
    render(<StrictMode><IntlProvider><MeetingTextReview meetingId={meeting.public_id} turn={turn} onClose={vi.fn()} /></IntlProvider></StrictMode>);
    const select = await screen.findByRole("combobox", { name: "Dil modeli" });
    expect(MeetingService.reviewModels).toHaveBeenCalledOnce(); expect(suggest).not.toHaveBeenCalled();
    expect(screen.getAllByRole("option")).toHaveLength(4); expect(select).toHaveValue("qwen3.5:27b");
    await check(); await screen.findByRole("heading", { name: "Önerilen metin" });
    expect(suggest).toHaveBeenCalledExactlyOnceWith(meeting.public_id, turn.public_id, { model_name: "qwen3.5:27b", model_digest: "a".repeat(64) }, expect.any(AbortSignal));
  });
  it("selects another installed model only on the explicit check and invalidates the old result", async () => {
    const first = await response();
    const suggest = vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValueOnce(first).mockResolvedValueOnce({ ...first, model_name: "qwen3.5:12b", model_digest: "b".repeat(64) });
    view(); await check(); await screen.findByRole("heading", { name: "Önerilen metin" });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "qwen3.5:12b" } });
    expect(screen.queryByRole("heading", { name: "Önerilen metin" })).toBeNull(); expect(screen.queryByRole("button", { name: "Düzeltilmiş sürümü kaydet" })).toBeNull(); expect(suggest).toHaveBeenCalledTimes(1);
    await check(); await screen.findByRole("heading", { name: "Önerilen metin" });
    expect(suggest).toHaveBeenLastCalledWith(meeting.public_id, turn.public_id, { model_name: "qwen3.5:12b", model_digest: "b".repeat(64) }, expect.any(AbortSignal));
  });
  it("does not silently choose an alternative when the configured default is unavailable", async () => {
    vi.mocked(MeetingService.reviewModels).mockResolvedValue({ items: reviewModels.items.map((model, index) => index ? model : { ...model, selectable: false, is_default: false, unavailable_reason: "default_changed" }) });
    const suggest = vi.spyOn(MeetingService, "correctionSuggestion"); view();
    expect(await screen.findByRole("combobox")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Kontrol et" })).toBeDisabled();
    expect(screen.getByRole("option", { name: /27b/ })).toBeDisabled(); expect(suggest).not.toHaveBeenCalled();
  });
  it.each(["tr", "en"])("shows green inline words and the original-to-new list in %s", async (locale) => {
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(await response()); view();
    if (locale === "en") fireEvent.click(await screen.findByRole("button", { name: "English" }));
    fireEvent.click(await screen.findByRole("button", { name: locale === "tr" ? "Kontrol et" : "Check" }));
    await screen.findByRole("heading", { name: locale === "tr" ? "Önerilen metin" : "Suggested text" });
    expect(document.querySelector("[data-suggested-text]")).toHaveTextContent("Yeni sürümü sunucuya yükledik.");
    expect(document.querySelector("[data-suggested-text] ins")).toHaveClass("correction-word");
    expect(document.querySelector("del")).toHaveTextContent("sürüyü");
    expect(screen.getByRole("button", { name: locale === "tr" ? "Düzeltilmiş sürümü kaydet" : "Save corrected version" })).toBeEnabled();
    expect(turn.text).toBe("Yeni sürüyü sunucuya yükledik.");
  });
  it("shows semantic review-required proposals inline and allows explicit saving", async () => {
    const result = await response(); result.proposals[0].assessment = "review_required"; result.proposals[0].reason = "semantic_review";
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(result); view(); await check();
    await screen.findByText("Bu değişikliği bağlamıyla birlikte inceleyin.");
    expect(document.querySelector("[data-suggested-text] ins")).toHaveTextContent("sürümü");
    expect(screen.getByRole("button", { name: "Düzeltilmiş sürümü kaydet" })).toBeEnabled();
  });
  it("shows unmapped proposals without inventing an inline position or a save action", async () => {
    const result = await response();
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue({ ...result, status: "unmapped", suggested_text: turn.text, save_token: null, expires_at: null, proposals: [{ original: "Not present", replacement: "Visible proposal", start_char: null, end_char: null, assessment: "unmapped", reason: "source_not_found" }] });
    view(); await check(); await screen.findByText("Visible proposal");
    expect(document.querySelector("[data-suggested-text]")).toBeNull(); expect(document.querySelector("ins")).toHaveClass("correction-word");
    expect(screen.queryByRole("button", { name: "Düzeltilmiş sürümü kaydet" })).toBeNull();
  });
  it("shows malformed and truncated model text literally without saving it", async () => {
    const result = await response(turn, false);
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue({ ...result, status: "invalid_output", model_output: "<script>untrusted()</script>", model_output_truncated: true });
    view(); await check(); await screen.findByText("<script>untrusted()</script>");
    expect(document.querySelector("script")).toBeNull(); expect(document.querySelector("details")).toHaveAttribute("open");
    expect(screen.getByText(/Model yanıtı gösterim sınırında kesildi/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Düzeltilmiş sürümü kaydet" })).toBeNull();
  });
  it("explains an unchanged result without claiming perfect accuracy", async () => {
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(await response(turn, false)); view(); await check();
    await screen.findByText(/Model bir kelime değişikliği önermedi/); expect(document.querySelector("[data-suggested-text]")).toBeNull();
  });
  it.each(["id", "text", "digest", "model", "revision"])("rejects a response bound to a different %s", async (kind) => {
    const result = await response();
    if (kind === "id") result.transcript_public_id = "different";
    if (kind === "text") result.original_text += " changed";
    if (kind === "digest") result.source_text_sha256 = "0".repeat(64);
    if (kind === "model") result.model_digest = "b".repeat(64);
    if (kind === "revision") result.expected_revision = 9;
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(result); view(); await check();
    await screen.findByRole("alert"); expect(document.querySelector("[data-suggested-text]")).toBeNull(); expect(screen.queryByRole("button", { name: "Düzeltilmiş sürümü kaydet" })).toBeNull();
  });
  it("does not display a suggestion that disagrees with its word positions", async () => {
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue({ ...await response(), suggested_text: "Invented text" }); view(); await check();
    await screen.findByText(/Tutarlı bir düzeltme önerisi alınamadı/); expect(screen.queryByText("Invented text")).toBeNull();
  });
  it("uses Unicode code points and renders model source text as text", async () => {
    const source = { ...turn, text: "😀 <b>Yeni sürüyü sunucuya yükledik.</b>" };
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(await response(source)); view(source); await check();
    await screen.findByRole("heading", { name: "Önerilen metin" });
    expect(document.querySelector("[data-suggested-text]")).toHaveTextContent("😀 <b>Yeni sürümü sunucuya yükledik.</b>");
    expect(document.querySelector("b")).toBeNull();
  });
  it.each([
    [503, "text_review_unavailable", "Yerel metin kontrolü hazır değil"], [503, "text_review_model_mismatch", "Model kimliği değişmiş"],
    [504, "text_review_timeout", "Kelime kontrolü süre sınırına ulaştı"], [502, "text_review_invalid_response", "Tutarlı bir düzeltme önerisi alınamadı"],
    [422, "text_review_context_limit", "Bu konuşma satırı tek seferde"], [409, "meeting_state_conflict", "Kelime kontrolü için toplantı analizinin"],
    [403, "forbidden", "Kelime kontrolü için toplantıyı okuma"], [404, "not_found", "İncelenecek toplantı metni artık"],
    [500, "private/model/path", "Kelime kontrolü tamamlanamadı"],
  ])("maps failure %s/%s without provider details", async (status, code, message) => {
    vi.spyOn(MeetingService, "correctionSuggestion").mockRejectedValue(new ApiError(Number(status), "private transcript and path", String(code))); view(); await check();
    await screen.findByText(new RegExp(String(message))); expect(screen.queryByText(/private/)).toBeNull();
  });
  it("retries only when explicitly checked again under StrictMode", async () => {
    const suggest = vi.spyOn(MeetingService, "correctionSuggestion").mockRejectedValueOnce(new ApiError(504, "Timeout", "text_review_timeout")).mockResolvedValueOnce(await response());
    render(<StrictMode><IntlProvider><MeetingTextReview meetingId={meeting.public_id} turn={turn} onClose={vi.fn()} /></IntlProvider></StrictMode>);
    await check(); await screen.findByRole("alert"); expect(suggest).toHaveBeenCalledTimes(1);
    await check(); await screen.findByRole("heading", { name: "Önerilen metin" }); expect(suggest).toHaveBeenCalledTimes(2);
  });
  it("aborts a stale selected model and ignores its late completion", async () => {
    let finish: ((result: CorrectionSuggestion) => void) | undefined;
    const suggest = vi.spyOn(MeetingService, "correctionSuggestion").mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    view(); await check(); const old = await response();
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "qwen3.5:12b" } });
    expect(suggest.mock.calls[0][3]?.aborted).toBe(true); finish?.(old);
    await waitFor(() => expect(screen.getByRole("button", { name: "Kontrol et" })).toBeEnabled());
    expect(document.querySelector("[data-suggested-text]")).toBeNull();
  });
  it("invalidates a suggestion when refreshed source text changes", async () => {
    const suggest = vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(await response());
    const mounted = view(); await check(); await screen.findByRole("heading", { name: "Önerilen metin" });
    mounted.rerender(<IntlProvider><MeetingTextReview meetingId={meeting.public_id} turn={{ ...turn, text: "Changed source" }} onClose={vi.fn()} /></IntlProvider>);
    expect(document.querySelector("[data-suggested-text]")).toBeNull();
    await screen.findByRole("combobox"); expect(suggest).toHaveBeenCalledTimes(1);
  });
  it("saves the exact proof once, disables duplicate clicks, and reports the saved DTO", async () => {
    const result = await response(), saved = await savedCorrection(); const onSaved = vi.fn();
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(result);
    let finish: ((result: typeof saved) => void) | undefined;
    const save = vi.spyOn(MeetingService, "saveCorrection").mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    view(turn, onSaved); await check(); const button = await screen.findByRole("button", { name: "Düzeltilmiş sürümü kaydet" });
    fireEvent.click(button); fireEvent.click(button);
    expect(save).toHaveBeenCalledExactlyOnceWith(meeting.public_id, turn.public_id, { save_token: result.save_token }, expect.any(AbortSignal));
    expect(screen.getByRole("combobox")).toBeDisabled(); expect(screen.getByRole("button", { name: "İncelemeyi kapat" })).toBeDisabled();
    finish?.(saved); await waitFor(() => expect(onSaved).toHaveBeenCalledExactlyOnceWith(saved));
  });
  it("retries a lost save response with the same proof", async () => {
    const result = await response(); vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(result);
    const save = vi.spyOn(MeetingService, "saveCorrection").mockRejectedValueOnce(new ApiError(504, "Timeout")).mockResolvedValueOnce(await savedCorrection());
    const onSaved = vi.fn(); view(turn, onSaved); await check();
    fireEvent.click(await screen.findByRole("button", { name: "Düzeltilmiş sürümü kaydet" })); await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Düzeltilmiş sürümü kaydet" })); await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(save.mock.calls[0][2]).toEqual(save.mock.calls[1][2]);
  });
  it.each(["correction_conflict", "invalid_correction_token"])("prevents reusing save proof after %s", async (code) => {
    vi.spyOn(MeetingService, "correctionSuggestion").mockResolvedValue(await response());
    const save = vi.spyOn(MeetingService, "saveCorrection").mockRejectedValue(new ApiError(code === "correction_conflict" ? 409 : 422, "Invalid", code)); view(); await check();
    fireEvent.click(await screen.findByRole("button", { name: "Düzeltilmiş sürümü kaydet" })); await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: "Düzeltilmiş sürümü kaydet" })).toBeDisabled(); expect(save).toHaveBeenCalledOnce();
  });
  it("explains an empty catalog and allows retrying a catalog outage", async () => {
    vi.mocked(MeetingService.reviewModels).mockRejectedValueOnce(new ApiError(503, "Unavailable", "text_review_unavailable")).mockResolvedValueOnce({ items: [] });
    view(); fireEvent.click(await screen.findByRole("button", { name: "Tekrar dene" })); await screen.findByText(/Kurulu model bulunamadı/);
    expect(screen.queryByRole("button", { name: "Kontrol et" })).toBeNull();
  });
});
