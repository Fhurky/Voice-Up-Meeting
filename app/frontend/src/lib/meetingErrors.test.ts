import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/apiClient";
import { meetingErrorKey, validateMeetingFile } from "@/lib/meetingErrors";

describe("meeting input limits and safe errors", () => {
  it("allows 2 GiB and rejects one byte more without reading file contents", () => {
    const file = new File(["wav"], "recording.wav");
    Object.defineProperty(file, "size", { value: 2 * 1024 ** 3, configurable: true });
    expect(validateMeetingFile(file)).toBeNull();
    Object.defineProperty(file, "size", { value: 2 * 1024 ** 3 + 1 });
    expect(validateMeetingFile(file)).toBe("meeting.error.audio_limit");
  });
  it("does not display arbitrary backend diagnostics or confuse long recording limits with the pilot", () => {
    expect(meetingErrorKey(new ApiError(500, "private path", "unknown_provider_failure"))).toBe("meeting.error.unexpected");
    expect(meetingErrorKey(new ApiError(413, "private path"))).toBe("meeting.error.audio_limit");
    expect(validateMeetingFile(new File(["audio"], "recording.mp3"))).toBe("meeting.error.unsupported_audio");
  });
});
