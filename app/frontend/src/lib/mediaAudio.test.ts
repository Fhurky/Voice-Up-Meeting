import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/apiClient";
import { extractMeetingAudio, isMediaContainer, monoPcm } from "@/lib/mediaAudio";

afterEach(() => { vi.unstubAllGlobals(); });

function stubDecoder(decode: () => Promise<unknown>) {
  const created: unknown[][] = [];
  vi.stubGlobal("OfflineAudioContext", class { constructor(...args: unknown[]) { created.push(args); } decodeAudioData = decode; });
  return created;
}
const mp4 = () => {
  const file = new File([new Uint8Array(8)], "toplanti.kayit.mp4", { type: "video/mp4", lastModified: 1234 });
  Object.defineProperty(file, "arrayBuffer", { value: async () => new ArrayBuffer(8) });
  return file;
};
const decoded = (channels: number[][]) => ({
  length: channels[0]?.length ?? 0, duration: (channels[0]?.length ?? 0) / 16000, numberOfChannels: channels.length,
  getChannelData: (index: number) => Float32Array.from(channels[index] ?? []),
});

describe("meeting audio from MP4 containers", () => {
  it.each([["a.mp4", true], ["A.MP4", true], ["a.m4a", true], ["a.wav", false], ["a.flac", false], ["mp4", false]])("recognizes %s", (name, expected) => {
    expect(isMediaContainer(new File([], name))).toBe(expected);
  });

  it("averages channels and clips to the 16 bit range", () => {
    expect(Array.from(monoPcm([Float32Array.of(1, -1, 0.5, 2), Float32Array.of(1, -1, -0.5, 2)]))).toEqual([32767, -32768, 0, 32767]);
  });

  it("produces a 16 kHz mono WAV named after the source, keeping its timestamp", async () => {
    const created = stubDecoder(async () => decoded([[0.5, -0.5], [0.5, -0.5]]));
    const audio = await extractMeetingAudio(mp4());
    expect(created[0]).toEqual([1, 1, 16000]);
    expect(audio.name).toBe("toplanti.kayit.wav");
    expect(audio.lastModified).toBe(1234);
    expect(audio.size).toBe(44 + 4);
    const bytes = new DataView(await new Response(audio).arrayBuffer());
    expect(bytes.getUint16(22, true)).toBe(1);
    expect(bytes.getUint32(24, true)).toBe(16000);
    expect(bytes.getUint32(40, true)).toBe(4);
    expect(bytes.getInt16(44, true)).toBe(16384);
    expect(bytes.getInt16(46, true)).toBe(-16384);
  });

  it("reports a file the browser cannot decode without creating anything", async () => {
    stubDecoder(async () => { throw new DOMException("bad", "EncodingError"); });
    await expect(extractMeetingAudio(mp4())).rejects.toMatchObject({ code: "media_no_audio" });
    await expect(extractMeetingAudio(mp4())).rejects.toBeInstanceOf(ApiError);
  });

  it("reports a file without audio", async () => {
    stubDecoder(async () => decoded([[]]));
    await expect(extractMeetingAudio(mp4())).rejects.toMatchObject({ code: "media_no_audio" });
  });

  it("rejects audio longer than the meeting limit", async () => {
    stubDecoder(async () => ({ ...decoded([[0]]), duration: 4 * 3600 + 1 }));
    await expect(extractMeetingAudio(mp4())).rejects.toMatchObject({ code: "audio_limit" });
  });
});
