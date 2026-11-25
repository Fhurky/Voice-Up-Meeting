/** Two-channel meeting capture: channel 0 is this computer's microphone, channel 1 is the system audio. */
export const CAPTURE_SAMPLE_RATE = 16000;
export const CAPTURE_CHANNELS = 2;
export const CAPTURE_FRAME_BYTES = CAPTURE_CHANNELS * 2;
export const CAPTURE_PART_SECONDS = 2;
export const CAPTURE_MAX_BYTES = 2 * 1024 ** 3;
export const CAPTURE_MAX_SECONDS = 14400;
/** Bounded audio-thread ledger: samples not yet written to the local file. */
export const CAPTURE_CREDIT_BYTES = 16 * 1024 ** 2;
/** Parts kept in memory until the server acknowledges them. */
export const CAPTURE_MEMORY_BYTES = 32 * 1024 ** 2;
export const CAPTURE_METER_BLOCK_SECONDS = 0.05;
export const CAPTURE_METER_BLOCKS = 5;
/** Below this RMS (about -60 dBFS) a channel counts as silent. */
export const CAPTURE_SILENCE_LEVEL = 0.001;
export const CAPTURE_SILENCE_WARNING_SECONDS = 60;
/** Envelope history used to tell speaker leakage into the microphone apart from a headset. */
export const CAPTURE_ECHO_WINDOW_SECONDS = 20;
export const CAPTURE_ECHO_MIN_ACTIVE_SECONDS = 5;
export const CAPTURE_ECHO_CORRELATION = 0.6;

export type CaptureChannelLevels = [microphone: number, system: number];
export type CaptureMessage =
  | { type: "part"; data: ArrayBuffer; startFrame: number; frameCount: number }
  | { type: "levels"; frameCount: number; bufferedBytes: number; blocks: CaptureChannelLevels[] }
  | { type: "stopped"; frameCount: number; reason?: "limit" }
  | { type: "error"; code: "buffer_full" | "capture_failed" };
export interface CaptureBufferOptions { sampleRate: number; partFrames: number; creditBytes: number; maxFrames: number }

export function capturePartFrames(sampleRate: number): number { return sampleRate * CAPTURE_PART_SECONDS; }
export function captureMaxFrames(sampleRate: number): number {
  return Math.min(sampleRate * CAPTURE_MAX_SECONDS, Math.floor((CAPTURE_MAX_BYTES - 44) / CAPTURE_FRAME_BYTES));
}

export function encodeStereoWavHeader(sampleRate: number, frameCount: number): ArrayBuffer {
  if (!Number.isInteger(sampleRate) || sampleRate < 8000 || sampleRate > 192000
    || !Number.isSafeInteger(frameCount) || frameCount <= 0 || frameCount > captureMaxFrames(sampleRate)) {
    throw new RangeError("Invalid PCM source bounds");
  }
  const header = new ArrayBuffer(44);
  const view = new DataView(header);
  const text = (offset: number, value: string) => { for (let index = 0; index < value.length; index += 1) view.setUint8(offset + index, value.charCodeAt(index)); };
  const dataBytes = frameCount * CAPTURE_FRAME_BYTES;
  text(0, "RIFF"); view.setUint32(4, 36 + dataBytes, true); text(8, "WAVEfmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, CAPTURE_CHANNELS, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * CAPTURE_FRAME_BYTES, true);
  view.setUint16(32, CAPTURE_FRAME_BYTES, true); view.setUint16(34, 16, true); text(36, "data");
  view.setUint32(40, dataBytes, true);
  return header;
}

function pcm16(value: number): number {
  const sample = Math.max(-1, Math.min(1, value));
  return Math.round(sample * (sample < 0 ? 32768 : 32767));
}

/**
 * Audio-thread side. Interleaves both channels into fixed parts of `partFrames`, keeps a credit
 * ledger so unwritten audio stays bounded, and reports 50 ms RMS blocks for both channels.
 */
export class StereoCaptureBuffer {
  private readonly options: CaptureBufferOptions;
  private readonly emit: (message: CaptureMessage) => void;
  private readonly blockFrames: number;
  private buffer: ArrayBuffer | null = null;
  private view: DataView | null = null;
  private partStart = 0;
  private position = 0;
  private availableBytes: number;
  private emittedBytes = 0;
  private frameCount = 0;
  private blockCount = 0;
  private squares: [number, number] = [0, 0];
  private blocks: CaptureChannelLevels[] = [];
  private levelsPending = false;
  private microphoneMuted = false;
  private active = true;

  constructor(options: CaptureBufferOptions, emit: (message: CaptureMessage) => void) {
    this.options = options; this.emit = emit; this.availableBytes = options.creditBytes;
    this.blockFrames = Math.round(options.sampleRate * CAPTURE_METER_BLOCK_SECONDS);
    if (!Number.isInteger(options.sampleRate) || options.sampleRate < 8000 || options.sampleRate > 192000
      || !Number.isInteger(options.partFrames) || options.partFrames < 1
      || options.partFrames * CAPTURE_FRAME_BYTES > options.creditBytes
      || !Number.isInteger(options.creditBytes) || options.creditBytes > CAPTURE_CREDIT_BYTES || options.creditBytes % CAPTURE_FRAME_BYTES
      || !Number.isSafeInteger(options.maxFrames) || options.maxFrames < 1) {
      throw new RangeError("Invalid capture buffer bounds");
    }
  }

  setMicrophoneMuted(muted: boolean): void { this.microphoneMuted = muted; }

  /** `microphone` and `system` are one render quantum of the merged input. */
  push(microphone: Float32Array | undefined, system: Float32Array | undefined): boolean {
    if (!this.active) return false;
    const length = Math.max(microphone?.length ?? 0, system?.length ?? 0);
    const count = Math.min(length, this.options.maxFrames - this.frameCount);
    if (count * CAPTURE_FRAME_BYTES > this.availableBytes) return this.fail("buffer_full");
    for (let index = 0; index < count; index += 1) {
      const left = this.microphoneMuted ? 0 : (microphone?.[index] ?? 0);
      const right = system?.[index] ?? 0;
      if (!Number.isFinite(left) || !Number.isFinite(right)) return this.fail("capture_failed");
      if (!this.buffer) {
        this.buffer = new ArrayBuffer(this.options.partFrames * CAPTURE_FRAME_BYTES);
        this.view = new DataView(this.buffer); this.partStart = this.frameCount;
      }
      this.view!.setInt16(this.position, pcm16(left), true);
      this.view!.setInt16(this.position + 2, pcm16(right), true);
      this.position += CAPTURE_FRAME_BYTES; this.availableBytes -= CAPTURE_FRAME_BYTES; this.frameCount += 1;
      this.squares[0] += left * left; this.squares[1] += right * right; this.blockCount += 1;
      if (this.blockCount === this.blockFrames) this.closeBlock();
      if (this.position === this.buffer.byteLength) this.flush();
    }
    if (this.frameCount === this.options.maxFrames) { this.stop("limit"); return false; }
    return this.active;
  }

  acknowledge(bytes: number): void {
    if (!this.active) return;
    if (!Number.isInteger(bytes) || bytes <= 0 || bytes % CAPTURE_FRAME_BYTES || bytes > this.emittedBytes) { this.fail("capture_failed"); return; }
    this.emittedBytes -= bytes; this.availableBytes += bytes;
  }

  acknowledgeLevels(): void { this.levelsPending = false; }

  stop(reason?: "limit"): void {
    if (!this.active) return;
    this.flush(); this.active = false;
    this.emit({ type: "stopped", frameCount: this.frameCount, ...(reason ? { reason } : {}) });
  }

  private closeBlock(): void {
    const frames = this.blockCount;
    this.blocks.push([Math.min(1, Math.sqrt(this.squares[0] / frames)), Math.min(1, Math.sqrt(this.squares[1] / frames))]);
    this.squares = [0, 0]; this.blockCount = 0;
    // The main thread acknowledges each report, so slow consumers merge blocks instead of queueing messages.
    if (this.blocks.length >= CAPTURE_METER_BLOCKS && !this.levelsPending) {
      this.levelsPending = true;
      this.emit({ type: "levels", frameCount: this.frameCount, bufferedBytes: this.options.creditBytes - this.availableBytes, blocks: this.blocks });
      this.blocks = [];
    } else if (this.blocks.length > 4 * CAPTURE_METER_BLOCKS) {
      this.blocks = this.blocks.slice(-CAPTURE_METER_BLOCKS);
    }
  }

  private flush(): void {
    if (!this.buffer || !this.position) return;
    const data = this.position === this.buffer.byteLength ? this.buffer : this.buffer.slice(0, this.position);
    const frameCount = this.position / CAPTURE_FRAME_BYTES;
    this.buffer = null; this.view = null; this.position = 0; this.emittedBytes += data.byteLength;
    this.emit({ type: "part", data, startFrame: this.partStart, frameCount });
  }

  private fail(code: "buffer_full" | "capture_failed"): false {
    this.active = false; this.buffer = null; this.view = null;
    this.emit({ type: "error", code });
    return false;
  }
}

export interface CaptureMonitorState {
  levels: CaptureChannelLevels;
  silentSeconds: CaptureChannelLevels;
  microphoneSilent: boolean;
  systemSilent: boolean;
  echo: boolean;
}

function correlation(left: number[], right: number[]): number {
  const count = left.length;
  const meanLeft = left.reduce((sum, value) => sum + value, 0) / count;
  const meanRight = right.reduce((sum, value) => sum + value, 0) / count;
  let product = 0; let squaresLeft = 0; let squaresRight = 0;
  for (let index = 0; index < count; index += 1) {
    const a = left[index] - meanLeft; const b = right[index] - meanRight;
    product += a * b; squaresLeft += a * a; squaresRight += b * b;
  }
  return squaresLeft && squaresRight ? product / Math.sqrt(squaresLeft * squaresRight) : 0;
}

/**
 * Main-thread warnings from the 50 ms level blocks. A channel is silent after a minute below the floor.
 * Speaker leakage shows as the microphone envelope following the system envelope while the system
 * channel carries speech; with a headset the two envelopes are independent.
 */
export class CaptureMonitor {
  private readonly history: CaptureChannelLevels[] = [];
  private readonly windowBlocks = Math.round(CAPTURE_ECHO_WINDOW_SECONDS / CAPTURE_METER_BLOCK_SECONDS);
  private silentBlocks: [number, number] = [0, 0];
  private latest: CaptureChannelLevels = [0, 0];

  push(blocks: CaptureChannelLevels[]): CaptureMonitorState {
    for (const block of blocks) {
      this.latest = block;
      for (const channel of [0, 1] as const) this.silentBlocks[channel] = block[channel] < CAPTURE_SILENCE_LEVEL ? this.silentBlocks[channel] + 1 : 0;
      this.history.push(block);
    }
    if (this.history.length > this.windowBlocks) this.history.splice(0, this.history.length - this.windowBlocks);
    const silentSeconds: CaptureChannelLevels = [this.silentBlocks[0] * CAPTURE_METER_BLOCK_SECONDS, this.silentBlocks[1] * CAPTURE_METER_BLOCK_SECONDS];
    return {
      levels: this.latest,
      silentSeconds,
      microphoneSilent: silentSeconds[0] >= CAPTURE_SILENCE_WARNING_SECONDS,
      systemSilent: silentSeconds[1] >= CAPTURE_SILENCE_WARNING_SECONDS,
      echo: this.echo(),
    };
  }

  private echo(): boolean {
    const active = this.history.filter((block) => block[1] >= CAPTURE_SILENCE_LEVEL * 10);
    if (active.length * CAPTURE_METER_BLOCK_SECONDS < CAPTURE_ECHO_MIN_ACTIVE_SECONDS) return false;
    const decibels = (value: number) => 20 * Math.log10(Math.max(value, 1e-6));
    // A small lag allowance covers the speaker-to-microphone path and output buffering.
    let best = -1;
    for (let lag = 0; lag <= 2; lag += 1) {
      const system: number[] = []; const microphone: number[] = [];
      for (let index = lag; index < this.history.length; index += 1) {
        if (this.history[index - lag][1] < CAPTURE_SILENCE_LEVEL * 10) continue;
        system.push(decibels(this.history[index - lag][1])); microphone.push(decibels(this.history[index][0]));
      }
      if (system.length >= 2) best = Math.max(best, correlation(system, microphone));
    }
    return best >= CAPTURE_ECHO_CORRELATION;
  }
}

/** `chain_n = SHA-256(chain_{n-1} || SHA-256(part_n))`, starting from 32 zero bytes; the server keeps the same value. */
export const CAPTURE_CHAIN_START = new Uint8Array(32);
export async function sha256(data: ArrayBuffer | Uint8Array<ArrayBuffer>): Promise<Uint8Array<ArrayBuffer>> {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", data));
}
export async function nextChain(chain: Uint8Array<ArrayBuffer>, partDigest: Uint8Array<ArrayBuffer>): Promise<Uint8Array<ArrayBuffer>> {
  const joined = new Uint8Array(64); joined.set(chain); joined.set(partDigest, 32);
  return sha256(joined);
}
export function hex(bytes: Uint8Array): string { return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(""); }
