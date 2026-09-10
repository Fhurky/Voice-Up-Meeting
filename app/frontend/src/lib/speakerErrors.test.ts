import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/apiClient";
import { errorMessageKey, jobErrorKey } from "@/lib/speakerErrors";

describe("speaker capacity errors", () => {
  it("maps the HTTP conflict and terminal job code to the same localized message", () => {
    expect(errorMessageKey(new ApiError(409, "server diagnostic", "profile_limit"))).toBe("speaker.error.profile_limit");
    expect(jobErrorKey("profile_limit")).toBe("speaker.error.profile_limit");
  });
});
