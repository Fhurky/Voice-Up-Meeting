import { StrictMode } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { IntlProvider } from "@/contexts/IntlContext";
import { ApiError } from "@/lib/apiClient";
import { MeetingSourceUpload } from "@/components/MeetingSourceUpload";
import * as uploader from "@/services/meetingUpload";
import * as media from "@/lib/mediaAudio";
import { meeting } from "@/test/meetingFixtures";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
describe("meeting source lifetime", () => {
  it("resumes from a reselected MP4 by uploading its extracted audio", async () => {
    const audio = new File(["RIFF"], "meeting.wav", { type: "audio/wav" });
    const extract = vi.spyOn(media, "extractAudio").mockResolvedValue(audio);
    const run = vi.spyOn(uploader, "uploadMeeting").mockImplementation(() => new Promise(() => {}));
    render(<IntlProvider><MeetingSourceUpload meeting={{ ...meeting, status: "uploading" }} initialFile={null} onComplete={vi.fn()} /></IntlProvider>);
    const input = await screen.findByLabelText("Toplantı ses veya video dosyası");
    expect(input.getAttribute("accept")).toContain(".mp4");
    fireEvent.change(input, { target: { files: [new File([new Uint8Array(8)], "meeting.mp4", { type: "video/mp4" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Yüklemeye devam et" }));
    await waitFor(() => expect(run).toHaveBeenCalledOnce());
    expect(extract).toHaveBeenCalledOnce();
    expect(run.mock.calls[0]?.[1]).toBe(audio);
  });

  it("shows why an MP4 cannot resume", async () => {
    vi.spyOn(media, "extractAudio").mockRejectedValue(new ApiError(422, "No decodable audio", "media_no_audio"));
    const run = vi.spyOn(uploader, "uploadMeeting");
    render(<IntlProvider><MeetingSourceUpload meeting={{ ...meeting, status: "uploading" }} initialFile={null} onComplete={vi.fn()} /></IntlProvider>);
    fireEvent.change(await screen.findByLabelText("Toplantı ses veya video dosyası"), { target: { files: [new File([new Uint8Array(8)], "meeting.mp4")] } });
    fireEvent.click(screen.getByRole("button", { name: "Yüklemeye devam et" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Bu dosyadan ses çıkarılamadı");
    expect(run).not.toHaveBeenCalled();
  });

  it("starts once under Strict Mode and aborts an upload on unmount", async () => {
    const run = vi.spyOn(uploader, "uploadMeeting").mockImplementation(() => new Promise(() => {}));
    const view = render(<StrictMode><IntlProvider><MeetingSourceUpload meeting={{ ...meeting, status: "uploading" }} initialFile={new File(["wav"], "meeting.wav")} onComplete={vi.fn()} /></IntlProvider></StrictMode>);
    await waitFor(() => expect(run).toHaveBeenCalledOnce());
    const signal = run.mock.calls[0]?.[3];
    view.unmount();
    expect(signal?.aborted).toBe(true);
  });

  it("requires file reselection after refresh and pauses without cancelling the server meeting", async () => {
    const run = vi.spyOn(uploader, "uploadMeeting").mockImplementation(() => new Promise(() => {}));
    render(<IntlProvider><MeetingSourceUpload meeting={{ ...meeting, status: "uploading" }} initialFile={null} onComplete={vi.fn()} /></IntlProvider>);
    expect(await screen.findByRole("button", { name: "Yüklemeye devam et" })).toBeDisabled();
    expect(run).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Toplantı ses veya video dosyası"), { target: { files: [new File(["wav"], "meeting.wav")] } });
    fireEvent.click(screen.getByRole("button", { name: "Yüklemeye devam et" }));
    await screen.findByRole("button", { name: "Aktarımı duraklat" });
    fireEvent.click(screen.getByRole("button", { name: "Aktarımı duraklat" }));
    expect(run.mock.calls[0]?.[3].aborted).toBe(true);
    expect(screen.getByRole("button", { name: "Yüklemeye devam et" })).toBeEnabled();
  });
});
