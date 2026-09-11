import { ApiError } from "@/lib/apiClient";
import { MeetingService, type Meeting, type MeetingUploadManifest } from "@/services/meetings";

export interface UploadProgress { phase: "verifying" | "uploading" | "completing"; uploadedBytes: number }
const fail = (code: string): never => { throw new ApiError(409, "Meeting upload could not continue", code); };

function validateManifest(manifest: MeetingUploadManifest, meeting: Meeting, partBytes: number) {
  if (manifest.meeting_public_id !== meeting.public_id || manifest.next_index !== manifest.parts.length
    || manifest.parts.length > Math.ceil(meeting.size_bytes / partBytes)) fail("upload_ack_invalid");
  let total = 0;
  for (const [index, part] of manifest.parts.entries()) {
    if (part.index !== index || part.size_bytes !== Math.min(partBytes, meeting.size_bytes - total)
      || !/^[a-f0-9]{64}$/.test(part.sha256)) fail("upload_ack_invalid");
    total += part.size_bytes;
  }
  if (manifest.uploaded_bytes !== total) fail("upload_ack_invalid");
}

export async function uploadMeeting(meeting: Meeting, file: File, progress: (value: UploadProgress) => void, signal: AbortSignal): Promise<Meeting> {
  signal.throwIfAborted();
  if (file.size !== meeting.size_bytes || file.name.split(".").at(-1)?.toUpperCase() !== meeting.format) fail("source_mismatch");
  const partBytes = meeting.upload_part_bytes;
  if (!Number.isSafeInteger(partBytes) || partBytes < 1 || partBytes > 4 * 1024 * 1024) fail("upload_ack_invalid");
  let manifest = await MeetingService.manifest(meeting.public_id, signal);
  signal.throwIfAborted();
  validateManifest(manifest, meeting, partBytes);
  progress({ phase: manifest.parts.length ? "verifying" : "uploading", uploadedBytes: manifest.uploaded_bytes });
  for (let index = 0; index < Math.ceil(file.size / partBytes); index += 1) {
    signal.throwIfAborted();
    const start = index * partBytes;
    const data = await file.slice(start, Math.min(start + partBytes, file.size)).arrayBuffer();
    signal.throwIfAborted();
    const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", data)), (byte) => byte.toString(16).padStart(2, "0")).join("");
    signal.throwIfAborted();
    const saved = manifest.parts[index];
    if (saved) {
      if (saved.sha256 !== sha256 || saved.size_bytes !== data.byteLength) fail("source_mismatch");
      continue;
    }
    const next = await MeetingService.uploadPart(meeting.public_id, index, data, sha256, signal);
    signal.throwIfAborted();
    validateManifest(next, meeting, partBytes);
    if (next.next_index !== index + 1 || next.parts[index]?.sha256 !== sha256
      || manifest.parts.some((part, previous) => next.parts[previous]?.sha256 !== part.sha256)) fail("upload_ack_invalid");
    manifest = next;
    progress({ phase: "uploading", uploadedBytes: manifest.uploaded_bytes });
  }
  signal.throwIfAborted();
  progress({ phase: "completing", uploadedBytes: manifest.uploaded_bytes });
  return MeetingService.complete(meeting.public_id, signal);
}
