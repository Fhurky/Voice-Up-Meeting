import { createHash } from "node:crypto";
import { describe, expect, it, vi } from "vitest";
import { CaptureSendError, CaptureUploader, type CaptureSendRequest } from "@/lib/captureUpload";

const FRAME = 4;
function part(startFrame: number, frameCount: number, fill = startFrame % 251) {
  return { startFrame, frameCount, data: new Uint8Array(frameCount * FRAME).fill(fill).buffer };
}
function chainOf(parts: ArrayBuffer[]): string {
  let chain = Buffer.alloc(32);
  for (const data of parts) chain = createHash("sha256").update(chain).update(createHash("sha256").update(new Uint8Array(data)).digest()).digest();
  return chain.toString("hex");
}
function deferred<T>() {
  let resolve!: (value: T) => void; let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("CaptureUploader", () => {
  it("sends parts in order with one request in flight and their SHA-256", async () => {
    const pending: Array<{ request: CaptureSendRequest; reply: ReturnType<typeof deferred<{ receivedFrames: number }>> }> = [];
    const uploader = new CaptureUploader({ send: (request) => { const reply = deferred<{ receivedFrames: number }>(); pending.push({ request, reply }); return reply.promise; } });
    const first = part(0, 2); const second = part(2, 2);
    uploader.add(first); uploader.add(second);
    await settle();
    expect(pending).toHaveLength(1);
    expect(pending[0].request.startFrame).toBe(0);
    expect(pending[0].request.sha256).toBe(createHash("sha256").update(new Uint8Array(first.data)).digest("hex"));
    pending[0].reply.resolve({ receivedFrames: 2 });
    await settle();
    expect(pending).toHaveLength(2);
    expect(pending[1].request.startFrame).toBe(2);
    pending[1].reply.resolve({ receivedFrames: 4 });
    await settle();
    expect(uploader.state).toMatchObject({ acknowledgedFrames: 4, queuedBytes: 0 });
  });

  it("rejects a non-contiguous part", () => {
    const uploader = new CaptureUploader({ send: vi.fn() });
    uploader.add(part(0, 2));
    expect(() => uploader.add(part(3, 2))).toThrow(RangeError);
  });

  it("waits with growing backoff after a network failure and resumes on the next part", async () => {
    let now = 0;
    const send = vi.fn<(request: CaptureSendRequest) => Promise<{ receivedFrames: number }>>()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockImplementation(async (request) => ({ receivedFrames: request.startFrame + request.data.byteLength / FRAME }));
    const uploader = new CaptureUploader({ send, now: () => now });
    uploader.add(part(0, 2));
    await settle();
    expect(uploader.state.retrying).toBe(true);
    uploader.pump(); await settle();
    expect(send).toHaveBeenCalledTimes(1);
    now = 1000;
    uploader.add(part(2, 2)); await settle(); await settle();
    expect(send.mock.calls.map((call) => call[0].startFrame)).toEqual([0, 0, 2]);
    expect(uploader.state).toMatchObject({ acknowledgedFrames: 4, retrying: false });
  });

  it("treats a gap reply ahead of the part as a lost acknowledgement", async () => {
    const send = vi.fn<(request: CaptureSendRequest) => Promise<{ receivedFrames: number }>>()
      .mockRejectedValueOnce(new CaptureSendError({ kind: "gap", expectedFrame: 2 })).mockResolvedValue({ receivedFrames: 4 });
    const uploader = new CaptureUploader({ send });
    uploader.add(part(0, 2)); uploader.add(part(2, 2));
    await settle(); await settle();
    expect(send.mock.calls.map((call) => call[0].startFrame)).toEqual([0, 2]);
    expect(uploader.state.acknowledgedFrames).toBe(4);
  });

  it("stops when an acknowledgement does not cover the part", async () => {
    const uploader = new CaptureUploader({ send: vi.fn().mockResolvedValue({ receivedFrames: 1 }) });
    uploader.add(part(0, 2));
    await settle();
    expect(uploader.state.failed).toBe("capture_acknowledgement_invalid");
  });

  it("stops on a conflicting part", async () => {
    const uploader = new CaptureUploader({ send: vi.fn().mockRejectedValue(new CaptureSendError({ kind: "conflict" })) });
    uploader.add(part(0, 2));
    await settle();
    expect(uploader.state.failed).toBe("capture_conflict");
    await expect(uploader.drain(null)).rejects.toThrow(CaptureSendError);
  });

  it("keeps memory bounded and sends the overflow from the sealed file at drain", async () => {
    const parts = [part(0, 2, 1), part(2, 2, 2), part(4, 2, 3)];
    const sent: CaptureSendRequest[] = [];
    let online = false;
    const send = vi.fn(async (request: CaptureSendRequest) => {
      if (!online) throw new TypeError("offline");
      sent.push(request); return { receivedFrames: request.startFrame + request.data.byteLength / FRAME };
    });
    let now = 0;
    const uploader = new CaptureUploader({ send, memoryBytes: 2 * 2 * FRAME, now: () => now, wait: async (ms) => { now += ms; } });
    for (const item of parts) uploader.add(item);
    await settle();
    expect(uploader.state).toMatchObject({ queuedBytes: 16, waitingForFile: true });
    const header = new Uint8Array(44);
    const file = new File([header, ...parts.map((item) => new Uint8Array(item.data))], "capture.wav");
    online = true;
    const result = await uploader.drain(file);
    expect(sent.map((request) => request.startFrame)).toEqual([0, 2, 4]);
    expect(new Uint8Array(sent[2].data)).toEqual(new Uint8Array(parts[2].data));
    expect(result).toEqual({ frameCount: 6, chainSha256: chainOf(parts.map((item) => item.data)) });
    expect(uploader.state).toMatchObject({ acknowledgedFrames: 6, queuedBytes: 0, waitingForFile: false });
  });

  it("fails the drain when overflowed parts have no local file", async () => {
    const uploader = new CaptureUploader({ send: vi.fn().mockRejectedValue(new TypeError("offline")), memoryBytes: 4 });
    uploader.add(part(0, 2)); uploader.add(part(2, 2));
    await settle();
    await expect(uploader.drain(null, undefined)).rejects.toMatchObject({ failure: { kind: "fatal", code: "capture_file_missing" } });
  });
});
