import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { AudioJobForm } from "@/components/AudioJobForm";
import { IntlProvider, useIntl } from "@/contexts/IntlContext";
import { ApiError } from "@/lib/apiClient";
import * as media from "@/lib/mediaAudio";
import { SpeakerService } from "@/services/speakers";
import { jobFixture, profileFixture } from "@/test/speakerFixtures";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const recording = { public_id: jobFixture.recording_public_id, sha256: "a".repeat(64), size_bytes: 200, format: "WAV" as const, duration_seconds: 20, created_at: jobFixture.created_at };

function LocaleSwitch() {
  const { setLocale } = useIntl();
  return <button onClick={() => setLocale("en")}>English</button>;
}

function setup(purpose: "enroll" | "identify" = "identify", existing = false) {
  return render(<IntlProvider><MemoryRouter><Routes>
    <Route path="/" element={<><LocaleSwitch /><AudioJobForm purpose={purpose} profile={existing ? profileFixture : undefined} /></>} />
    <Route path="/speaker-jobs/:publicId" element={<p>Saved job route</p>} />
  </Routes></MemoryRouter></IntlProvider>);
}

const video = () => new File([new Uint8Array(64)], "kayit.mp4", { type: "video/mp4" });
const extractedAudio = new File(["RIFF"], "kayit.wav", { type: "audio/wav" });

describe("audio from a video file", () => {
  it("creates a profile from an MP4 by uploading only the extracted WAV", async () => {
    const extract = vi.spyOn(media, "extractAudio").mockResolvedValue(extractedAudio);
    const upload = vi.spyOn(SpeakerService, "upload").mockResolvedValue(recording);
    vi.spyOn(SpeakerService, "createJob").mockResolvedValue(jobFixture);
    setup("enroll");
    const input = await screen.findByLabelText("Ses dosyası");
    expect(input.getAttribute("accept")).toContain(".mp4");
    fireEvent.change(input, { target: { files: [video()] } });
    fireEvent.change(screen.getByLabelText("Konuşmacı adı veya takma adı"), { target: { value: "Video speaker" } });
    fireEvent.submit(screen.getByRole("form", { name: "Konuşmacı ses örneği" }));
    await screen.findByText("Saved job route");
    expect(extract).toHaveBeenCalledWith(expect.objectContaining({ name: "kayit.mp4" }), 120);
    expect(upload.mock.calls[0][0]).toBe(extractedAudio);
  });

  it("decodes once and retries the upload with the same audio", async () => {
    const extract = vi.spyOn(media, "extractAudio").mockResolvedValue(extractedAudio);
    const upload = vi.spyOn(SpeakerService, "upload").mockRejectedValueOnce(new TypeError("network")).mockResolvedValue(recording);
    vi.spyOn(SpeakerService, "createJob").mockResolvedValue(jobFixture);
    setup("identify");
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [video()] } });
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    await screen.findByRole("alert");
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    await screen.findByText("Saved job route");
    expect(extract).toHaveBeenCalledTimes(1);
    expect(upload.mock.calls.map((call) => call[0])).toEqual([extractedAudio, extractedAudio]);
  });

  it.each([
    [new ApiError(422, "No decodable audio", "media_no_audio"), "Bu dosyadan ses çıkarılamadı"],
    [new ApiError(413, "Audio too long", "audio_limit"), "120 saniye"],
  ])("explains %s before uploading anything", async (failure, text) => {
    vi.spyOn(media, "extractAudio").mockRejectedValue(failure);
    const upload = vi.spyOn(SpeakerService, "upload");
    setup("identify");
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [video()] } });
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(text);
    expect(upload).not.toHaveBeenCalled();
  });

  it("accepts a video larger than the audio upload limit", async () => {
    vi.spyOn(media, "extractAudio").mockResolvedValue(extractedAudio);
    vi.spyOn(SpeakerService, "upload").mockResolvedValue(recording);
    vi.spyOn(SpeakerService, "createJob").mockResolvedValue(jobFixture);
    const large = video();
    Object.defineProperty(large, "size", { value: 300 * 1024 * 1024 });
    setup("identify");
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [large] } });
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    await screen.findByText("Saved job route");
  });
});

describe("audio submission contract", () => {
  it("submits a new profile without a capacity contract", async () => {
    const upload = vi.spyOn(SpeakerService, "upload").mockResolvedValue(recording);
    const create = vi.spyOn(SpeakerService, "createJob").mockResolvedValue(jobFixture);
    setup("enroll");
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [new File(["wav"], "voice.wav")] } });
    fireEvent.change(screen.getByLabelText("Konuşmacı adı veya takma adı"), { target: { value: "New speaker" } });
    fireEvent.submit(screen.getByRole("form", { name: "Konuşmacı ses örneği" }));
    await screen.findByText("Saved job route");
    expect(upload).toHaveBeenCalledTimes(1);
    expect(create.mock.calls[0][0]).toEqual({ recording_public_id: recording.public_id, purpose: "enroll", name: "New speaker" });
  });

  it.each(["tr", "en"])("recognizes an older server profile_limit response in %s as a historical rule", async (locale) => {
    vi.spyOn(SpeakerService, "upload").mockResolvedValue(recording);
    const create = vi.spyOn(SpeakerService, "createJob").mockRejectedValue(new ApiError(409, "private backend diagnostic", "profile_limit"));
    setup("enroll");
    await screen.findByLabelText("Ses dosyası");
    if (locale === "en") {
      fireEvent.click(screen.getByRole("button", { name: "English" }));
      await screen.findByLabelText("Audio file");
    }
    fireEvent.change(screen.getByLabelText(locale === "tr" ? "Konuşmacı adı veya takma adı" : "Speaker name or nickname"), { target: { value: "New speaker" } });
    fireEvent.change(screen.getByLabelText(locale === "tr" ? "Ses dosyası" : "Audio file"), { target: { files: [new File(["wav"], "voice.wav")] } });
    fireEvent.submit(screen.getByRole("form", { name: locale === "tr" ? "Konuşmacı ses örneği" : "Speaker voice sample" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(locale === "tr" ? "Bu kayıt, o sırada geçerli olan profil sınırı nedeniyle reddedildi. Yeni profil oluşturulmadı. Artık yeni bir kayıt başlatabilirsiniz." : "This enrollment was rejected under the profile limit in effect at the time. No new profile was created. You can now start a new enrollment.");
    expect(create.mock.calls[0][0]).toEqual({ recording_public_id: recording.public_id, purpose: "enroll", name: "New speaker" });
    expect(screen.queryByText("private backend diagnostic")).not.toBeInTheDocument();
  });

  it("retries a lost job response with the same key and does not repeat the successful upload", async () => {
    const upload = vi.spyOn(SpeakerService, "upload").mockResolvedValue(recording);
    const create = vi.spyOn(SpeakerService, "createJob").mockRejectedValueOnce(new TypeError("network")).mockResolvedValueOnce(jobFixture);
    setup();
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [new File(["wav"], "voice.wav")] } });
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("İşlem tamamlanamadı");
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    await screen.findByText("Saved job route");
    expect(upload).toHaveBeenCalledTimes(1);
    expect(create).toHaveBeenCalledTimes(2);
    expect(create.mock.calls[0][1]).toBe(create.mock.calls[1][1]);
    expect(create.mock.calls[1][0]).toEqual({ recording_public_id: recording.public_id, purpose: "identify" });
  });

  it("reuses the upload key after a lost upload response", async () => {
    const upload = vi.spyOn(SpeakerService, "upload").mockRejectedValueOnce(new TypeError("network")).mockResolvedValueOnce(recording);
    vi.spyOn(SpeakerService, "createJob").mockResolvedValue(jobFixture);
    setup();
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [new File(["wav"], "voice.wav")] } });
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    await screen.findByRole("alert");
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    await screen.findByText("Saved job route");
    expect(upload.mock.calls[0][1]).toBe(upload.mock.calls[1][1]);
  });

  it("sends an opaque target profile ID and never a new name for an added sample", async () => {
    vi.spyOn(SpeakerService, "upload").mockResolvedValue(recording);
    const create = vi.spyOn(SpeakerService, "createJob").mockResolvedValue(jobFixture);
    setup("enroll", true);
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [new File(["wav"], "voice.wav")] } });
    expect(screen.queryByLabelText("Konuşmacı adı veya takma adı")).not.toBeInTheDocument();
    fireEvent.submit(screen.getByRole("form", { name: "Konuşmacı ses örneği" }));
    await screen.findByText("Saved job route");
    expect(create.mock.calls[0][0]).toEqual({ recording_public_id: recording.public_id, purpose: "enroll", profile_public_id: profileFixture.public_id });
  });

  it("rejects oversize files before uploading", async () => {
    const upload = vi.spyOn(SpeakerService, "upload");
    setup();
    const file = new File(["audio"], "voice.wav");
    Object.defineProperty(file, "size", { value: 50 * 1024 * 1024 + 1 });
    fireEvent.change(await screen.findByLabelText("Ses dosyası"), { target: { files: [file] } });
    fireEvent.submit(screen.getByRole("form", { name: "Ses tanıma kaydı" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("50 MiB"));
    expect(upload).not.toHaveBeenCalled();
  });
});
