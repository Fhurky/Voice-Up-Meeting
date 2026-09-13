import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMicrophoneCapture, listMicrophoneDevices, microphoneSupportError } from "@/lib/microphoneCapture";
import type { PcmCaptureMessage } from "@/lib/microphonePcm";

vi.mock("@/lib/microphone.worklet.ts?worker&url", () => ({ default: "/assets/microphone-worklet.js" }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
class Track extends EventTarget { stop = vi.fn(); readyState = "live"; muted = false; }
class Context extends EventTarget {
  static latest: Context;
  sampleRate = 48000;
  state: AudioContextState = "running";
  destination = {};
  audioWorklet = { addModule: vi.fn<(url: string) => Promise<void>>().mockResolvedValue(undefined) };
  source = { connect: vi.fn(), disconnect: vi.fn() };
  resume = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  close = vi.fn<() => Promise<void>>().mockImplementation(async () => { this.state = "closed"; });
  createMediaStreamSource = vi.fn().mockImplementation(() => this.source);
  constructor() { super(); Context.latest = this; }
}
class Node extends EventTarget {
  static latest: Node;
  port = { onmessage: null as ((event: MessageEvent<PcmCaptureMessage>) => void) | null, postMessage: vi.fn(), close: vi.fn() };
  connect = vi.fn(); disconnect = vi.fn();
  constructor() { super(); Node.latest = this; }
  emit(data: PcmCaptureMessage) { this.port.onmessage?.(new MessageEvent("message", { data })); }
}

let track: Track;
let media: MediaStream;
let getUserMedia: ReturnType<typeof vi.fn<(constraints: MediaStreamConstraints) => Promise<MediaStream>>>;
let write: ReturnType<typeof vi.fn<(data: FileSystemWriteChunkType) => Promise<void>>>;
let close: ReturnType<typeof vi.fn<() => Promise<void>>>;
let abort: ReturnType<typeof vi.fn<() => Promise<void>>>;
let getFile: ReturnType<typeof vi.fn<() => Promise<File>>>;
let remove: ReturnType<typeof vi.fn<(name: string) => Promise<void>>>;
let createWritable: ReturnType<typeof vi.fn<() => Promise<FileSystemWritableFileStream>>>;
let bytes: Uint8Array<ArrayBuffer>;
let cursor: number;

beforeEach(() => {
  track = new Track();
  media = { getTracks: () => [track], getAudioTracks: () => [track] } as unknown as MediaStream;
  getUserMedia = vi.fn<(constraints: MediaStreamConstraints) => Promise<MediaStream>>().mockResolvedValue(media);
  bytes = new Uint8Array(); cursor = 0;
  write = vi.fn<(data: FileSystemWriteChunkType) => Promise<void>>().mockImplementation(async (data) => {
    if (typeof data === "object" && !(data instanceof ArrayBuffer) && !(data instanceof Blob) && "type" in data) {
      if (data.type === "seek") { cursor = data.position!; return; }
      if (data.type === "truncate") { bytes = bytes.slice(0, data.size ?? undefined); return; }
      if (data.position != null) cursor = data.position;
      data = data.data!;
    }
    const chunk = data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array((data as ArrayBufferView).buffer);
    const next = new Uint8Array(Math.max(bytes.length, cursor + chunk.byteLength)); next.set(bytes); next.set(chunk, cursor);
    bytes = next; cursor += chunk.byteLength;
  });
  close = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  abort = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  getFile = vi.fn<() => Promise<File>>().mockImplementation(async () => new File([bytes], "owned.wav", { type: "audio/wav" }));
  remove = vi.fn<(name: string) => Promise<void>>().mockResolvedValue(undefined);
  createWritable = vi.fn<() => Promise<FileSystemWritableFileStream>>().mockResolvedValue({ write, close, abort } as unknown as FileSystemWritableFileStream);
  const fileHandle = { createWritable, getFile };
  const directory = { getFileHandle: vi.fn().mockResolvedValue(fileHandle), removeEntry: remove };
  vi.stubGlobal("isSecureContext", true);
  vi.stubGlobal("AudioContext", Context);
  vi.stubGlobal("AudioWorkletNode", Node);
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia, enumerateDevices: vi.fn().mockResolvedValue([]) },
    storage: { getDirectory: vi.fn().mockResolvedValue({ getDirectoryHandle: vi.fn().mockResolvedValue(directory) }) } });
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("microphone capture lifecycle and disk ownership", () => {
  it("waits for the final producer message and disk write before sealing a WAV File", async () => {
    const onError = vi.fn();
    const capture = createMicrophoneCapture({ deviceId: "chosen-microphone", onError });
    await capture.start();
    expect(getUserMedia).toHaveBeenCalledWith(expect.objectContaining({ audio: expect.objectContaining({ deviceId: { exact: "chosen-microphone" }, channelCount: 1 }), video: false }));
    const pendingWrite = deferred<void>();
    const save = write.getMockImplementation()!;
    write.mockImplementationOnce(async (data) => { await pendingWrite.promise; await save(data); });
    const resultPromise = capture.stop();
    expect(Node.latest.port.postMessage).toHaveBeenCalledWith({ type: "stop" });
    expect(getFile).not.toHaveBeenCalled();
    Node.latest.emit({ type: "chunk", data: new Int16Array([100, -100, 0]).buffer, sampleCount: 3 });
    Node.latest.emit({ type: "stopped", sampleCount: 3 });
    await vi.waitFor(() => expect(track.stop).toHaveBeenCalled());
    expect(getFile).not.toHaveBeenCalled();
    expect(close).not.toHaveBeenCalled();
    pendingWrite.resolve();
    const result = await resultPromise;
    expect(result.file.size).toBe(50); expect(result.durationSeconds).toBe(3 / 48000);
    expect(new DataView(await result.file.slice(0, 44).arrayBuffer()).getUint32(40, true)).toBe(6);
    expect(close).toHaveBeenCalledOnce(); expect(onError).not.toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();
    await result.dispose(); await result.dispose();
    expect(remove).toHaveBeenCalledOnce();
  });

  it("returns credit only after the disk write resolves", async () => {
    const capture = createMicrophoneCapture({}); await capture.start();
    const pending = deferred<void>(); write.mockImplementationOnce(() => pending.promise);
    Node.latest.emit({ type: "chunk", data: new ArrayBuffer(8), sampleCount: 4 });
    await Promise.resolve();
    expect(Node.latest.port.postMessage).not.toHaveBeenCalledWith({ type: "credit", bytes: 8 });
    pending.resolve();
    await vi.waitFor(() => expect(Node.latest.port.postMessage).toHaveBeenCalledWith({ type: "credit", bytes: 8 }));
    await capture.cancel();
  });

  it("stops a permission result arriving after cancellation", async () => {
    const permission = deferred<MediaStream>(); getUserMedia.mockReturnValue(permission.promise);
    const capture = createMicrophoneCapture({});
    const started = capture.start(); const rejection = expect(started).rejects.toMatchObject({ name: "AbortError" });
    await capture.cancel(); permission.resolve(media);
    await rejection;
    await vi.waitFor(() => expect(track.stop).toHaveBeenCalled());
    expect(getFile).not.toHaveBeenCalled();
    expect(Context.latest.close).toHaveBeenCalled();
  });

  it.each(["ended", "mute"])("invalidates capture on a track %s event", async (event) => {
    const onError = vi.fn(); const capture = createMicrophoneCapture({ onError }); await capture.start();
    track.dispatchEvent(new Event(event));
    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: "device_interrupted" })));
    await expect(capture.stop()).rejects.toMatchObject({ code: "device_interrupted" });
    expect(track.stop).toHaveBeenCalled(); expect(getFile).not.toHaveBeenCalled(); await capture.cancel();
  });

  it("invalidates capture when the audio context is suspended", async () => {
    const onError = vi.fn(); const capture = createMicrophoneCapture({ onError }); await capture.start();
    Context.latest.state = "suspended"; Context.latest.dispatchEvent(new Event("statechange"));
    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: "device_interrupted" })));
    await capture.cancel(); expect(getFile).not.toHaveBeenCalled();
  });

  it("discards disk quota failures without returning a partial file", async () => {
    const onError = vi.fn(); const capture = createMicrophoneCapture({ onError }); await capture.start();
    write.mockRejectedValueOnce(new DOMException("Disk quota", "QuotaExceededError"));
    Node.latest.emit({ type: "chunk", data: new ArrayBuffer(8), sampleCount: 4 });
    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: "storage_full" })));
    await expect(capture.stop()).rejects.toMatchObject({ code: "storage_full" });
    await capture.cancel(); expect(getFile).not.toHaveBeenCalled(); expect(remove).toHaveBeenCalled();
  });

  it("rejects an inconsistent final sample count and empty recording", async () => {
    for (const count of [0, 1]) {
      const capture = createMicrophoneCapture({}); await capture.start(); const stopping = capture.stop();
      const rejection = expect(stopping).rejects.toMatchObject({ code: count ? "capture_failed" : "empty_recording" });
      Node.latest.emit({ type: "stopped", sampleCount: count });
      await rejection; await capture.cancel();
    }
    expect(getFile).not.toHaveBeenCalled();
  });

  it("cleans up on page departure and enumerates without requesting permission", async () => {
    await listMicrophoneDevices(); expect(getUserMedia).not.toHaveBeenCalled();
    const capture = createMicrophoneCapture({}); await capture.start();
    window.dispatchEvent(new Event("pagehide"));
    expect(track.stop).toHaveBeenCalled(); await capture.cancel(); expect(remove).toHaveBeenCalled();
  });

  it("explains unavailable capabilities and denied permission", async () => {
    vi.stubGlobal("isSecureContext", false); expect(microphoneSupportError()).toBe("insecure_context");
    vi.stubGlobal("isSecureContext", true);
    getUserMedia.mockRejectedValue(new DOMException("No", "NotAllowedError"));
    const capture = createMicrophoneCapture({});
    await expect(capture.start()).rejects.toMatchObject({ code: "permission_denied" }); await capture.cancel();
  });

  it("preserves a valid source at an automatic limit and transfers disposal ownership", async () => {
    const onLimit = vi.fn(); const capture = createMicrophoneCapture({ onLimit }); await capture.start();
    Node.latest.emit({ type: "chunk", data: new ArrayBuffer(8), sampleCount: 4 });
    Node.latest.emit({ type: "stopped", sampleCount: 4, reason: "limit" });
    expect(track.stop).toHaveBeenCalled(); expect(onLimit).toHaveBeenCalledOnce();
    const result = await capture.stop();
    expect(result.file.size).toBe(52);
    await capture.cancel(); expect(remove).not.toHaveBeenCalled();
    await result.dispose(); expect(remove).toHaveBeenCalledOnce();
  });

  it("rejects a microphone muted during asynchronous preparation", async () => {
    const ready = deferred<void>();
    const permission = deferred<MediaStream>(); getUserMedia.mockReturnValue(permission.promise);
    const capture = createMicrophoneCapture({}); const started = capture.start();
    Context.latest.audioWorklet.addModule.mockReturnValue(ready.promise);
    permission.resolve(media);
    await vi.waitFor(() => expect(Context.latest.audioWorklet.addModule).toHaveBeenCalled());
    track.muted = true; track.dispatchEvent(new Event("mute")); ready.resolve();
    await expect(started).rejects.toMatchObject({ code: "device_unavailable" });
    expect(track.stop).toHaveBeenCalled(); await capture.cancel();
  });

  it("aborts a writer that resolves while an earlier cancellation cleanup is still pending", async () => {
    const writerReady = deferred<FileSystemWritableFileStream>(); createWritable.mockReturnValue(writerReady.promise);
    const removalReady = deferred<void>(); remove.mockReturnValueOnce(removalReady.promise);
    const capture = createMicrophoneCapture({}); const started = capture.start();
    const rejected = expect(started).rejects.toMatchObject({ name: "AbortError" });
    await vi.waitFor(() => expect(createWritable).toHaveBeenCalled());
    const cancelled = capture.cancel();
    await vi.waitFor(() => expect(remove).toHaveBeenCalled());
    writerReady.resolve({ write, close, abort } as unknown as FileSystemWritableFileStream);
    await Promise.resolve(); await Promise.resolve(); removalReady.resolve();
    await rejected; await cancelled;
    expect(abort).toHaveBeenCalledOnce(); expect(getFile).not.toHaveBeenCalled();
  });

  it("reports captured sample duration and freezes it while final disk writes drain", async () => {
    const onProgress = vi.fn(); const capture = createMicrophoneCapture({ onProgress }); await capture.start();
    Node.latest.emit({ type: "progress", sampleCount: 12000, bufferedBytes: 24000, level: 0.5 });
    expect(onProgress).toHaveBeenLastCalledWith({ elapsedSeconds: 0.25, bufferedBytes: 24000, level: 0.5 });
    const pendingWrite = deferred<void>(); const save = write.getMockImplementation()!;
    write.mockImplementationOnce(async (data) => { await pendingWrite.promise; await save(data); });
    const stopped = capture.stop();
    Node.latest.emit({ type: "chunk", data: new ArrayBuffer(24002), sampleCount: 12001 });
    Node.latest.emit({ type: "stopped", sampleCount: 12001 });
    await vi.waitFor(() => expect(track.stop).toHaveBeenCalled());
    expect(onProgress).toHaveBeenLastCalledWith({ elapsedSeconds: 12001 / 48000, bufferedBytes: 24002, level: 0 });
    vi.spyOn(performance, "now").mockReturnValue(1000000000);
    pendingWrite.resolve(); const result = await stopped;
    expect(onProgress).toHaveBeenLastCalledWith({ elapsedSeconds: 12001 / 48000, bufferedBytes: 0, level: 0 });
    expect(result.durationSeconds).toBe(12001 / 48000);
    await result.dispose();
  });
});
