/// <reference types="node" />
import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MeetingService, type MeetingUploadManifest } from "@/services/meetings";
import { uploadMeeting } from "@/services/meetingUpload";
import { meeting } from "@/test/meetingFixtures";

const partBytes = 4 * 1024 * 1024;
const digest = async (bytes: ArrayBuffer) => Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256", bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
const empty = (): MeetingUploadManifest => ({ meeting_public_id: meeting.public_id, parts: [], uploaded_bytes: 0, next_index: 0 });

function source(size = partBytes + 7) {
  const file = new File([new Uint8Array(size)], "meeting.wav");
  const read = vi.spyOn(file, "arrayBuffer");
  const slice = vi.spyOn(file, "slice");
  return { file, read, slice, record: { ...meeting, size_bytes: size, status: "uploading" as const } };
}

beforeEach(() => { vi.restoreAllMocks(); vi.stubGlobal("crypto", webcrypto); });

describe("bounded resumable meeting upload", () => {
  it("reads only 4 MiB slices, counts server acknowledgements, then completes", async () => {
    const { file, read, slice, record } = source();
    let manifest = empty();
    vi.spyOn(MeetingService, "manifest").mockResolvedValue(manifest);
    const append = vi.spyOn(MeetingService, "uploadPart").mockImplementation(async (_id, index, body, sha256) => {
      manifest = { ...manifest, next_index: index + 1, uploaded_bytes: manifest.uploaded_bytes + body.byteLength,
        parts: [...manifest.parts, { index, size_bytes: body.byteLength, sha256 }] };
      return manifest;
    });
    const complete = vi.spyOn(MeetingService, "complete").mockResolvedValue({ ...record, status: "queued" });
    const progress = vi.fn();
    await uploadMeeting(record, file, progress, new AbortController().signal);
    expect(read).not.toHaveBeenCalled();
    expect(slice.mock.calls).toEqual([[0, partBytes], [partBytes, partBytes + 7]]);
    expect(append).toHaveBeenCalledTimes(2);
    expect(progress).toHaveBeenCalledWith({ phase: "uploading", uploadedBytes: partBytes + 7 });
    expect(complete).toHaveBeenCalledOnce();
  });

  it("checks the saved prefix after a refresh before uploading remaining bytes", async () => {
    const { file, read, record } = source();
    const sha256 = await digest(new Uint8Array(partBytes).buffer);
    const prefix = { index: 0, size_bytes: partBytes, sha256 };
    vi.spyOn(MeetingService, "manifest").mockResolvedValue({ ...empty(), parts: [prefix], next_index: 1, uploaded_bytes: partBytes });
    const append = vi.spyOn(MeetingService, "uploadPart").mockImplementation(async (_id, index, body, hash) => ({
      ...empty(), next_index: 2, uploaded_bytes: record.size_bytes,
      parts: [prefix, { index, size_bytes: body.byteLength, sha256: hash }],
    }));
    vi.spyOn(MeetingService, "complete").mockResolvedValue(record);
    await uploadMeeting(record, file, vi.fn(), new AbortController().signal);
    expect(read).not.toHaveBeenCalled();
    expect(append).toHaveBeenCalledTimes(1);
    expect(append.mock.calls[0]?.[1]).toBe(1);
  });

  it("rejects a different saved prefix without sending or completing anything", async () => {
    const { file, record } = source();
    vi.spyOn(MeetingService, "manifest").mockResolvedValue({ ...empty(), next_index: 1, uploaded_bytes: partBytes,
      parts: [{ index: 0, size_bytes: partBytes, sha256: "a".repeat(64) }] });
    const append = vi.spyOn(MeetingService, "uploadPart");
    const complete = vi.spyOn(MeetingService, "complete");
    await expect(uploadMeeting(record, file, vi.fn(), new AbortController().signal)).rejects.toMatchObject({ code: "source_mismatch" });
    expect(append).not.toHaveBeenCalled();
    expect(complete).not.toHaveBeenCalled();
  });

  it("rejects a malformed acknowledgement instead of completing an incomplete upload", async () => {
    const { file, record } = source(7);
    vi.spyOn(MeetingService, "manifest").mockResolvedValue(empty());
    vi.spyOn(MeetingService, "uploadPart").mockResolvedValue(empty());
    const complete = vi.spyOn(MeetingService, "complete");
    await expect(uploadMeeting(record, file, vi.fn(), new AbortController().signal)).rejects.toMatchObject({ code: "upload_ack_invalid" });
    expect(complete).not.toHaveBeenCalled();
  });

  it("stops before reading the source when cancelled", async () => {
    const { file, read, slice, record } = source();
    const controller = new AbortController(); controller.abort();
    await expect(uploadMeeting(record, file, vi.fn(), controller.signal)).rejects.toMatchObject({ name: "AbortError" });
    expect(read).not.toHaveBeenCalled(); expect(slice).not.toHaveBeenCalled();
  });
});
