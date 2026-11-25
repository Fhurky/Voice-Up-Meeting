import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMeetingCapture, meetingCaptureSupportError } from "@/lib/meetingCapture";
import type { CaptureMessage } from "@/lib/meetingCapturePcm";

vi.mock("@/lib/meetingCapture.worklet.ts?worker&url", () => ({ default: "/assets/meeting-capture-worklet.js" }));

class Track extends EventTarget { stop = vi.fn(); readyState = "live"; muted = false; kind: string; constructor(kind: string) { super(); this.kind = kind; } }
class FakeStream {
  tracks: Track[];
  constructor(tracks: Track[] = []) { this.tracks = tracks; }
  getTracks() { return this.tracks; }
  getAudioTracks() { return this.tracks.filter((track) => track.kind === "audio"); }
  getVideoTracks() { return this.tracks.filter((track) => track.kind === "video"); }
}
class AudioNodeMock { connect = vi.fn(); disconnect = vi.fn(); }
class Context extends EventTarget {
  static latest: Context;
  static options: AudioContextOptions | undefined;
  sampleRate: number;
  state: AudioContextState = "running";
  destination = {};
  audioWorklet = { addModule: vi.fn<(url: string) => Promise<void>>().mockResolvedValue(undefined) };
  merger = new AudioNodeMock();
  sources: AudioNodeMock[] = [];
  resume = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  close = vi.fn<() => Promise<void>>().mockImplementation(async () => { this.state = "closed"; });
  createChannelMerger = vi.fn().mockImplementation(() => this.merger);
  createMediaStreamSource = vi.fn().mockImplementation(() => { const source = new AudioNodeMock(); this.sources.push(source); return source; });
  constructor(options?: AudioContextOptions) { super(); Context.options = options; this.sampleRate = options?.sampleRate ?? 48000; Context.latest = this; }
}
class Node extends EventTarget {
  static latest: Node;
  port = { onmessage: null as ((event: MessageEvent<CaptureMessage>) => void) | null, postMessage: vi.fn(), close: vi.fn() };
  connect = vi.fn(); disconnect = vi.fn();
  options?: AudioWorkletNodeOptions;
  constructor(_context?: unknown, _name?: string, options?: AudioWorkletNodeOptions) { super(); this.options = options; Node.latest = this; }
  emit(data: CaptureMessage) { this.port.onmessage?.(new MessageEvent("message", { data })); }
}

let microphoneTrack: Track;
let systemTrack: Track;
let videoTrack: Track;
let getUserMedia: ReturnType<typeof vi.fn>;
let getDisplayMedia: ReturnType<typeof vi.fn>;
let write: ReturnType<typeof vi.fn<(data: FileSystemWriteChunkType) => Promise<void>>>;
let remove: ReturnType<typeof vi.fn>;
let bytes: Uint8Array<ArrayBuffer>;
let cursor: number;

beforeEach(() => {
  microphoneTrack = new Track("audio"); systemTrack = new Track("audio"); videoTrack = new Track("video");
  getUserMedia = vi.fn().mockResolvedValue(new FakeStream([microphoneTrack]));
  getDisplayMedia = vi.fn().mockResolvedValue(new FakeStream([videoTrack, systemTrack]));
  bytes = new Uint8Array(); cursor = 0;
  write = vi.fn<(data: FileSystemWriteChunkType) => Promise<void>>().mockImplementation(async (data) => {
    if (typeof data === "object" && !(data instanceof ArrayBuffer) && !(data instanceof Blob) && "type" in data) {
      if (data.position != null) cursor = data.position;
      data = data.data!;
    }
    const chunk = new Uint8Array(data as ArrayBuffer);
    const next = new Uint8Array(Math.max(bytes.length, cursor + chunk.byteLength)); next.set(bytes); next.set(chunk, cursor);
    bytes = next; cursor += chunk.byteLength;
  });
  remove = vi.fn().mockResolvedValue(undefined);
  const writable = { write, close: vi.fn().mockResolvedValue(undefined), abort: vi.fn().mockResolvedValue(undefined) };
  const fileHandle = { createWritable: vi.fn().mockResolvedValue(writable), getFile: vi.fn().mockImplementation(async () => new File([bytes], "owned.wav")) };
  const directory = { getFileHandle: vi.fn().mockResolvedValue(fileHandle), removeEntry: remove };
  vi.stubGlobal("isSecureContext", true);
  vi.stubGlobal("AudioContext", Context);
  vi.stubGlobal("AudioWorkletNode", Node);
  vi.stubGlobal("MediaStream", FakeStream);
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia, getDisplayMedia },
    storage: { getDirectory: vi.fn().mockResolvedValue({ getDirectoryHandle: vi.fn().mockResolvedValue(directory) }) } });
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("meeting capture", () => {
  it("needs both capture APIs", () => {
    expect(meetingCaptureSupportError()).toBeNull();
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia }, storage: { getDirectory: vi.fn() } });
    expect(meetingCaptureSupportError()).toBe("unsupported");
  });

  it("asks for the screen with system audio first, drops the video and merges microphone and system into two channels", async () => {
    const capture = createMeetingCapture({ deviceId: "headset" });
    await capture.start();
    expect(Context.options).toEqual({ sampleRate: 16000 });
    expect(getDisplayMedia.mock.invocationCallOrder[0]).toBeLessThan(getUserMedia.mock.invocationCallOrder[0]);
    expect(getDisplayMedia).toHaveBeenCalledWith(expect.objectContaining({ video: true, systemAudio: "include",
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } }));
    expect(getUserMedia).toHaveBeenCalledWith({ video: false, audio: { channelCount: 1, deviceId: { exact: "headset" } } });
    expect(videoTrack.stop).toHaveBeenCalled();
    expect(systemTrack.stop).not.toHaveBeenCalled();
    expect(Node.latest.options).toMatchObject({ channelCount: 2, channelCountMode: "explicit", channelInterpretation: "discrete",
      processorOptions: { sampleRate: 16000, partFrames: 32000, maxFrames: 16000 * 14400 } });
    const [microphoneSource, systemSource] = Context.latest.sources;
    expect(microphoneSource.connect).toHaveBeenCalledWith(Context.latest.merger, 0, 0);
    expect(systemSource.connect).toHaveBeenCalledWith(Context.latest.merger, 0, 1);
    await capture.cancel();
  });

  it("refuses a share without system audio", async () => {
    getDisplayMedia.mockResolvedValue(new FakeStream([videoTrack]));
    const onError = vi.fn();
    await expect(createMeetingCapture({ onError }).start()).rejects.toMatchObject({ code: "system_audio_missing" });
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: "system_audio_missing" }));
    expect(getUserMedia).not.toHaveBeenCalled();
  });

  it("maps a dismissed screen picker to share_cancelled", async () => {
    getDisplayMedia.mockRejectedValue(new DOMException("dismissed", "NotAllowedError"));
    await expect(createMeetingCapture({}).start()).rejects.toMatchObject({ code: "share_cancelled" });
  });

  it("writes each part to the local file before handing it on, then seals a two-channel WAV", async () => {
    const parts: number[] = [];
    const capture = createMeetingCapture({ onPart: (part) => parts.push(part.startFrame) });
    await capture.start();
    Node.latest.emit({ type: "part", data: new Int16Array([1, 2, 3, 4]).buffer, startFrame: 0, frameCount: 2 });
    await vi.waitFor(() => expect(parts).toEqual([0]));
    expect(Node.latest.port.postMessage).toHaveBeenCalledWith({ type: "credit", bytes: 8 });
    const stopping = capture.stop();
    Node.latest.emit({ type: "part", data: new Int16Array([5, 6]).buffer, startFrame: 2, frameCount: 1 });
    Node.latest.emit({ type: "stopped", frameCount: 3 });
    const result = await stopping;
    expect(parts).toEqual([0, 2]);
    expect(result).toMatchObject({ frameCount: 3, sampleRate: 16000 });
    expect(result.file.size).toBe(44 + 12);
    const header = new DataView(await result.file.slice(0, 44).arrayBuffer());
    expect([header.getUint16(22, true), header.getUint32(40, true)]).toEqual([2, 12]);
  });

  it("fails on a part that does not continue the previous one", async () => {
    const onError = vi.fn();
    const capture = createMeetingCapture({ onError }); await capture.start();
    Node.latest.emit({ type: "part", data: new ArrayBuffer(8), startFrame: 4, frameCount: 2 });
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: "capture_failed" }));
  });

  it("reports levels and warnings, and keeps recording when the microphone goes away", async () => {
    const onProgress = vi.fn();
    const capture = createMeetingCapture({ onProgress }); await capture.start();
    microphoneTrack.dispatchEvent(new Event("ended"));
    Node.latest.emit({ type: "levels", frameCount: 8000, bufferedBytes: 0, blocks: [[0, 0.2], [0, 0.2], [0, 0.2], [0, 0.2], [0, 0.2]] });
    expect(onProgress).toHaveBeenCalledWith(expect.objectContaining({ elapsedSeconds: 0.5, levels: [0, 0.2], microphoneLost: true, systemSilent: false }));
    expect(Node.latest.port.postMessage).toHaveBeenCalledWith({ type: "levels-credit" });
    await capture.cancel();
  });

  it("tells the caller when the browser's stop sharing control ends the system audio", async () => {
    const onShareEnded = vi.fn();
    const capture = createMeetingCapture({ onShareEnded }); await capture.start();
    systemTrack.dispatchEvent(new Event("ended"));
    expect(onShareEnded).toHaveBeenCalledOnce();
    await capture.cancel();
  });

  it("forwards the microphone switch to the audio thread", async () => {
    const capture = createMeetingCapture({}); await capture.start();
    capture.setMicrophoneMuted(true);
    expect(Node.latest.port.postMessage).toHaveBeenCalledWith({ type: "microphone", muted: true });
    await capture.cancel();
  });

  it("asks before leaving the page while recording", async () => {
    const capture = createMeetingCapture({}); await capture.start();
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    await capture.cancel();
    const after = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(after);
    expect(after.defaultPrevented).toBe(false);
  });
});
