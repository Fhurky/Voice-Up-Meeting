import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { IntlProvider } from "@/contexts/IntlContext";
import { CorrectedTranscriptText } from "@/components/CorrectedTranscriptText";
import { correctionTurn, savedCorrection } from "@/test/correctionFixtures";

afterEach(cleanup);
describe("saved correction and original views", () => {
  it("renders a saved version in green by default and preserves the original toggle across a fresh mount", async () => {
    const correction = await savedCorrection();
    const turn = { ...correctionTurn, correction };
    const first = render(<IntlProvider><CorrectedTranscriptText turn={turn} /></IntlProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "Orijinal" }));
    expect(document.querySelector("[data-original-text]")).toHaveTextContent(correctionTurn.text);
    fireEvent.click(screen.getByRole("button", { name: "Düzeltilmiş" }));
    expect(document.querySelector("[data-corrected-text] ins")).toHaveClass("correction-word");
    expect(document.querySelector("[data-corrected-text]")).toHaveTextContent(correction.corrected_text);
    first.unmount(); render(<IntlProvider><CorrectedTranscriptText turn={turn} /></IntlProvider>);
    expect(await screen.findByRole("button", { name: "Düzeltilmiş" })).toHaveAttribute("aria-pressed", "true");
    expect(turn.text).toBe(correctionTurn.text);
  });
  it("shows original source when the saved hash no longer matches", async () => {
    const correction = { ...await savedCorrection(), source_text_sha256: "0".repeat(64) };
    render(<IntlProvider><CorrectedTranscriptText turn={{ ...correctionTurn, correction }} /></IntlProvider>);
    await screen.findByText(/Kaydedilmiş düzeltme bu özgün metinle doğrulanamadı/);
    expect(document.querySelector("[data-original-text]")).toHaveTextContent(correctionTurn.text);
    expect(document.querySelector("[data-corrected-text]")).toBeNull();
  });
  it("rejects a saved edit that does not reconstruct its corrected text", async () => {
    const correction = { ...await savedCorrection(), corrected_text: "Invented" };
    render(<IntlProvider><CorrectedTranscriptText turn={{ ...correctionTurn, correction }} /></IntlProvider>);
    await screen.findByText(/Kaydedilmiş düzeltme bu özgün metinle doğrulanamadı/);
    expect(screen.queryByText("Invented")).toBeNull();
  });
  it("keeps HTML literal and non-BMP offsets correct in a saved result", async () => {
    const source = { ...correctionTurn, text: "😀 <script>Yeni sürüyü sunucuya yükledik.</script>" };
    const correction = await savedCorrection(source);
    render(<IntlProvider><CorrectedTranscriptText turn={{ ...source, correction }} /></IntlProvider>);
    await screen.findByRole("button", { name: "Düzeltilmiş" });
    expect(document.querySelector("[data-corrected-text]")).toHaveTextContent(correction.corrected_text);
    expect(document.querySelector("script")).toBeNull();
  });
});
