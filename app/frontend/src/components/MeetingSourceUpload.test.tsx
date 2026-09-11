import { StrictMode } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { IntlProvider } from "@/contexts/IntlContext";
import { MeetingSourceUpload } from "@/components/MeetingSourceUpload";
import * as uploader from "@/services/meetingUpload";
import { meeting } from "@/test/meetingFixtures";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
describe("meeting source lifetime", () => {
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
    fireEvent.change(screen.getByLabelText("Toplantı ses dosyası"), { target: { files: [new File(["wav"], "meeting.wav")] } });
    fireEvent.click(screen.getByRole("button", { name: "Yüklemeye devam et" }));
    await screen.findByRole("button", { name: "Aktarımı duraklat" });
    fireEvent.click(screen.getByRole("button", { name: "Aktarımı duraklat" }));
    expect(run.mock.calls[0]?.[3].aborted).toBe(true);
    expect(screen.getByRole("button", { name: "Yüklemeye devam et" })).toBeEnabled();
  });
});
