import { describe, expect, it } from "vitest";
import { encodeWavHeader, PcmCaptureBuffer, type PcmCaptureMessage } from "@/lib/microphonePcm";

const chunks = (messages: PcmCaptureMessage[]) => messages.filter((message) => message.type === "chunk");
describe("bounded microphone PCM producer", () => {
  it("encodes mono signed little-endian samples and flushes the last partial before stopped", () => {
    const messages: PcmCaptureMessage[] = [];
    const buffer = new PcmCaptureBuffer({ sampleRate: 16000, partBytes: 8, creditBytes: 16, maxSamples: 100 }, (message) => messages.push(message));
    buffer.push(new Float32Array([-2, -0.5, 0, 0.5, 2]));
    buffer.stop();
    expect(messages.map((message) => message.type)).toEqual(["chunk", "chunk", "stopped"]);
    expect(Array.from(new Int16Array(chunks(messages)[0].data))).toEqual([-32768, -16384, 0, 16384]);
    expect(Array.from(new Int16Array(chunks(messages)[1].data))).toEqual([32767]);
    expect(messages.at(-1)).toEqual({ type: "stopped", sampleCount: 5 });
  });

  it("counts transferred, in-flight and partial bytes before granting new producer credit", () => {
    const messages: PcmCaptureMessage[] = [];
    const buffer = new PcmCaptureBuffer({ sampleRate: 16000, partBytes: 8, creditBytes: 12, maxSamples: 100 }, (message) => messages.push(message));
    buffer.push(new Float32Array(6));
    expect(chunks(messages)).toHaveLength(1);
    buffer.push(new Float32Array(1));
    buffer.stop();
    expect(messages.at(-1)).toEqual({ type: "error", code: "buffer_full" });
    expect(messages.some((message) => message.type === "stopped")).toBe(false);
  });

  it("can record many chunks when disk acknowledgements return exact credits", () => {
    const messages: PcmCaptureMessage[] = [];
    const buffer = new PcmCaptureBuffer({ sampleRate: 16000, partBytes: 8, creditBytes: 12, maxSamples: 1000 }, (message) => messages.push(message));
    for (let index = 0; index < 100; index += 1) {
      buffer.push(new Float32Array(4));
      buffer.acknowledge(8);
    }
    buffer.stop();
    expect(chunks(messages)).toHaveLength(100);
    expect(messages.at(-1)).toEqual({ type: "stopped", sampleCount: 400 });
  });

  it("rejects over-acknowledgement without a successful final signal", () => {
    const messages: PcmCaptureMessage[] = [];
    const buffer = new PcmCaptureBuffer({ sampleRate: 16000, partBytes: 8, creditBytes: 16, maxSamples: 100 }, (message) => messages.push(message));
    buffer.push(new Float32Array(4)); buffer.acknowledge(10); buffer.stop();
    expect(messages.at(-1)).toEqual({ type: "error", code: "capture_failed" });
    expect(messages.some((message) => message.type === "stopped")).toBe(false);
  });

  it("seals the exact last allowed sample and explains an automatic source limit", () => {
    const messages: PcmCaptureMessage[] = [];
    const buffer = new PcmCaptureBuffer({ sampleRate: 16000, partBytes: 8, creditBytes: 16, maxSamples: 5 }, (message) => messages.push(message));
    buffer.push(new Float32Array(8)); buffer.stop();
    expect(chunks(messages).map((message) => message.data.byteLength)).toEqual([8, 2]);
    expect(messages.at(-1)).toEqual({ type: "stopped", sampleCount: 5, reason: "limit" });
  });

  it("allows only one unacknowledged progress message when the main thread stalls", () => {
    const messages: PcmCaptureMessage[] = [];
    const buffer = new PcmCaptureBuffer({ sampleRate: 8000, partBytes: 64000, creditBytes: 128000, maxSamples: 100000 }, (message) => messages.push(message));
    for (let index = 0; index < 5; index += 1) buffer.push(new Float32Array(2000));
    expect(messages.filter((message) => message.type === "progress")).toHaveLength(1);
    buffer.acknowledgeProgress(); buffer.push(new Float32Array(2000));
    expect(messages.filter((message) => message.type === "progress")).toHaveLength(2);
  });

  it("writes a canonical WAV header at the actual context sample rate", () => {
    const header = encodeWavHeader(48000, 48001);
    const view = new DataView(header);
    expect(new TextDecoder().decode(header.slice(0, 4))).toBe("RIFF");
    expect(new TextDecoder().decode(header.slice(8, 16))).toBe("WAVEfmt ");
    expect(new TextDecoder().decode(header.slice(36, 40))).toBe("data");
    expect([view.getUint32(4, true), view.getUint32(16, true), view.getUint16(20, true), view.getUint16(22, true), view.getUint32(24, true), view.getUint32(28, true), view.getUint16(32, true), view.getUint16(34, true), view.getUint32(40, true)])
      .toEqual([96038, 16, 1, 1, 48000, 96000, 2, 16, 96002]);
  });

  it.each([[48000, 0], [7999, 1], [192001, 1], [48000, 48000 * 14400 + 1], [192000, 2 ** 30]])("rejects invalid WAV rate or source bounds (%s, %s)", (rate, count) => {
    expect(() => encodeWavHeader(rate, count)).toThrow();
  });
});
