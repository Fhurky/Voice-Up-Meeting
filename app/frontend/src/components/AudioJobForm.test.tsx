import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { AudioJobForm } from "@/components/AudioJobForm";
import { IntlProvider } from "@/contexts/IntlContext";
import { SpeakerService } from "@/services/speakers";
import { jobFixture, profileFixture } from "@/test/speakerFixtures";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const recording = { public_id: jobFixture.recording_public_id, sha256: "a".repeat(64), size_bytes: 200, format: "WAV" as const, duration_seconds: 20, created_at: jobFixture.created_at };

function setup(purpose: "enroll" | "identify" = "identify", existing = false) {
  return render(<IntlProvider><MemoryRouter><Routes>
    <Route path="/" element={<AudioJobForm purpose={purpose} profile={existing ? profileFixture : undefined} />} />
    <Route path="/speaker-jobs/:publicId" element={<p>Saved job route</p>} />
  </Routes></MemoryRouter></IntlProvider>);
}

describe("audio submission contract", () => {
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
