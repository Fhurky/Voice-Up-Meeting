import { ApiError } from "@/lib/apiClient";
import { CaptureSendError, type CaptureSendRequest } from "@/lib/captureUpload";
import { MeetingService } from "@/services/meetings";

/**
 * Sends capture parts once the meeting exists. A gap is resolved from the server's captured
 * frame count; server and network trouble is retried; anything else ends the upload.
 */
export function captureTransport(meetingId: Promise<string>) {
  return async (part: CaptureSendRequest): Promise<{ receivedFrames: number }> => {
    const id = await meetingId;
    try {
      const ack = await MeetingService.appendCapture(id, part.startFrame, part.data, part.sha256);
      return { receivedFrames: ack.received_frames };
    } catch (error) {
      if (!(error instanceof ApiError)) throw error;
      if (error.code === "capture_gap") {
        const meeting = await MeetingService.get(id);
        throw new CaptureSendError({ kind: "gap", expectedFrame: meeting.captured_frames ?? 0 });
      }
      if (error.code === "capture_conflict") throw new CaptureSendError({ kind: "conflict" });
      if (error.status >= 500 || error.status === 408 || error.status === 429) throw new CaptureSendError({ kind: "retry" });
      throw new CaptureSendError({ kind: "fatal", code: error.code });
    }
  };
}
