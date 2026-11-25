import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import {
  CAPTURE_CHAIN_START, CAPTURE_CREDIT_BYTES, CAPTURE_FRAME_BYTES, CaptureMonitor, captureMaxFrames, encodeStereoWavHeader,
  hex, nextChain, sha256, StereoCaptureBuffer, type CaptureChannelLevels, type CaptureMessage,
} from "@/lib/meetingCapturePcm";

function buffer(overrides: Partial<{ sampleRate: number; partFrames: number; creditBytes: number; maxFrames: number }> = {}) {
  const messages: CaptureMessage[] = [];
  const capture = new StereoCaptureBuffer({ sampleRate: 16000, partFrames: 4, creditBytes: CAPTURE_CREDIT_BYTES, maxFrames: 1000, ...overrides },
    (message) => messages.push(message));
  return { capture, messages };
}
const frames = (values: number[]) => Float32Array.from(values);

describe("encodeStereoWavHeader", () => {
  it("describes two interleaved 16-bit channels", () => {
    const view = new DataView(encodeStereoWavHeader(16000, 10));
    expect(view.getUint16(22, true)).toBe(2);
    expect(view.getUint32(24, true)).toBe(16000);
    expect(view.getUint32(28, true)).toBe(64000);
    expect(view.getUint16(32, true)).toBe(4);
    expect(view.getUint32(40, true)).toBe(40);
    expect(view.getUint32(4, true)).toBe(76);
  });

  it("rejects an empty or oversized source", () => {
    expect(() => encodeStereoWavHeader(16000, 0)).toThrow(RangeError);
    expect(() => encodeStereoWavHeader(16000, captureMaxFrames(16000) + 1)).toThrow(RangeError);
    expect(captureMaxFrames(16000)).toBe(16000 * 14400);
    expect(captureMaxFrames(192000)).toBe(Math.floor((2 * 1024 ** 3 - 44) / 4));
  });
});

describe("StereoCaptureBuffer", () => {
  it("interleaves microphone and system samples into contiguous fixed parts", () => {
    const { capture, messages } = buffer();
    capture.push(frames([0.5, -0.5, 1, -1, 0, 0.25]), frames([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]));
    capture.stop();
    const parts = messages.filter((message) => message.type === "part");
    expect(parts.map((part) => [part.startFrame, part.frameCount])).toEqual([[0, 4], [4, 2]]);
    const first = new DataView(parts[0].data);
    expect([first.getInt16(0, true), first.getInt16(2, true)]).toEqual([16384, 3277]);
    expect([first.getInt16(8, true), first.getInt16(12, true)]).toEqual([32767, -32768]);
    expect(messages.at(-1)).toEqual({ type: "stopped", frameCount: 6 });
  });

  it("writes silence on the microphone channel while muted and keeps time aligned", () => {
    const { capture, messages } = buffer();
    capture.setMicrophoneMuted(true);
    capture.push(frames([0.5, 0.5, 0.5, 0.5]), frames([0.25, 0.25, 0.25, 0.25]));
    const part = messages.find((message) => message.type === "part");
    const view = new DataView(part!.data);
    expect([0, 4, 8, 12].map((offset) => view.getInt16(offset, true))).toEqual([0, 0, 0, 0]);
    expect(view.getInt16(2, true)).toBe(8192);
  });

  it("treats a missing system input as silence", () => {
    const { capture, messages } = buffer();
    capture.push(frames([0.5, 0.5, 0.5, 0.5]), undefined);
    const view = new DataView(messages.find((message) => message.type === "part")!.data);
    expect(view.getInt16(2, true)).toBe(0);
  });

  it("fails instead of growing past the unwritten-audio credit", () => {
    const { capture, messages } = buffer({ partFrames: 2, creditBytes: 4 * CAPTURE_FRAME_BYTES });
    expect(capture.push(frames([0, 0, 0, 0]), frames([0, 0, 0, 0]))).toBe(true);
    expect(capture.push(frames([0]), frames([0]))).toBe(false);
    expect(messages.at(-1)).toEqual({ type: "error", code: "buffer_full" });
  });

  it("returns credit after the local file write", () => {
    const { capture, messages } = buffer({ partFrames: 2, creditBytes: 4 * CAPTURE_FRAME_BYTES });
    capture.push(frames([0, 0, 0, 0]), frames([0, 0, 0, 0]));
    capture.acknowledge(4 * CAPTURE_FRAME_BYTES);
    expect(capture.push(frames([0, 0]), frames([0, 0]))).toBe(true);
    expect(messages.filter((message) => message.type === "part")).toHaveLength(3);
  });

  it("stops at the frame limit with the limit reason", () => {
    const { capture, messages } = buffer({ maxFrames: 3 });
    expect(capture.push(frames([0, 0, 0, 0]), frames([0, 0, 0, 0]))).toBe(false);
    expect(messages.at(-1)).toEqual({ type: "stopped", frameCount: 3, reason: "limit" });
  });

  it("rejects non-finite samples", () => {
    const { capture, messages } = buffer();
    capture.push(frames([Number.NaN]), frames([0]));
    expect(messages.at(-1)).toEqual({ type: "error", code: "capture_failed" });
  });

  it("reports 50 ms level blocks for both channels and waits for the consumer", () => {
    const { capture, messages } = buffer({ partFrames: 16000, maxFrames: 100000 });
    const quarter = 16000 / 4;
    capture.push(new Float32Array(quarter).fill(0.5), new Float32Array(quarter).fill(0));
    const levels = messages.filter((message) => message.type === "levels");
    expect(levels).toHaveLength(1);
    expect(levels[0].blocks).toHaveLength(5);
    expect(levels[0].blocks[0][0]).toBeCloseTo(0.5);
    expect(levels[0].blocks[0][1]).toBe(0);
    capture.push(new Float32Array(quarter).fill(0.5), new Float32Array(quarter).fill(0));
    expect(messages.filter((message) => message.type === "levels")).toHaveLength(1);
    capture.acknowledgeLevels();
    capture.push(new Float32Array(800), new Float32Array(800));
    expect(messages.filter((message) => message.type === "levels")).toHaveLength(2);
  });
});

describe("CaptureMonitor", () => {
  const second = 20;
  it("flags a channel after a minute of silence and clears on sound", () => {
    const monitor = new CaptureMonitor();
    const silentSystem: CaptureChannelLevels[] = Array.from({ length: 59 * second }, () => [0.05, 0]);
    expect(monitor.push(silentSystem).systemSilent).toBe(false);
    const state = monitor.push(Array.from({ length: second }, () => [0.05, 0]));
    expect(state.systemSilent).toBe(true);
    expect(state.microphoneSilent).toBe(false);
    expect(monitor.push([[0.05, 0.1]]).systemSilent).toBe(false);
  });

  it("detects the system audio leaking into the microphone", () => {
    const monitor = new CaptureMonitor();
    const blocks: CaptureChannelLevels[] = Array.from({ length: 10 * second }, (_, index) => {
      const system = 0.02 + 0.2 * Math.abs(Math.sin(index / 3));
      return [system * 0.3, system];
    });
    expect(monitor.push(blocks).echo).toBe(true);
  });

  it("does not flag independent headset speech", () => {
    const monitor = new CaptureMonitor();
    let seed = 7;
    const random = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    const blocks: CaptureChannelLevels[] = Array.from({ length: 10 * second }, () => [0.002 + 0.1 * random(), 0.02 + 0.2 * random()]);
    expect(monitor.push(blocks).echo).toBe(false);
  });
});

describe("chain", () => {
  it("matches SHA-256(previous || SHA-256(part)) from 32 zero bytes", async () => {
    const parts = [new Uint8Array([1, 2, 3, 4]), new Uint8Array([5, 6, 7, 8])];
    let chain = CAPTURE_CHAIN_START;
    for (const part of parts) chain = await nextChain(chain, await sha256(part));
    let expected = Buffer.alloc(32);
    for (const part of parts) expected = createHash("sha256").update(expected).update(createHash("sha256").update(part).digest()).digest();
    expect(hex(chain)).toBe(expected.toString("hex"));
  });
});
