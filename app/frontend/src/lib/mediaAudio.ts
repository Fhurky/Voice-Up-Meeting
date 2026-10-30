import { ApiError } from "@/lib/apiClient";
import { encodeWavHeader } from "@/lib/microphonePcm";

const SAMPLE_RATE = 16000;
const MAX_SECONDS = 4 * 3600;

export function isMediaContainer(file: File): boolean {
  return /\.(mp4|m4a)$/i.test(file.name);
}

export function monoPcm(channels: Float32Array[]): Int16Array {
  const length = channels[0]?.length ?? 0;
  const pcm = new Int16Array(length);
  for (let index = 0; index < length; index++) {
    let sum = 0;
    for (const channel of channels) sum += channel[index] ?? 0;
    const sample = Math.max(-1, Math.min(1, sum / channels.length));
    pcm[index] = Math.round(sample < 0 ? sample * 32768 : sample * 32767);
  }
  return pcm;
}

/** Only the audio leaves the browser: the picture is never uploaded or stored. */
export async function extractMeetingAudio(file: File): Promise<File> {
  let decoded: AudioBuffer;
  try {
    decoded = await new OfflineAudioContext(1, 1, SAMPLE_RATE).decodeAudioData(await file.arrayBuffer());
  } catch {
    throw new ApiError(422, "No decodable audio", "media_no_audio");
  }
  if (decoded.length === 0) throw new ApiError(422, "No decodable audio", "media_no_audio");
  if (decoded.duration > MAX_SECONDS) throw new ApiError(413, "Audio too long", "audio_limit");
  const channels = Array.from({ length: decoded.numberOfChannels }, (_, index) => decoded.getChannelData(index));
  const pcm = monoPcm(channels);
  return new File([encodeWavHeader(SAMPLE_RATE, pcm.length), pcm.buffer as ArrayBuffer], file.name.replace(/\.[^.]+$/, ".wav"), {
    type: "audio/wav",
    lastModified: file.lastModified,
  });
}
