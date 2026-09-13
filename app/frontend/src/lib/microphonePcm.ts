export const MICROPHONE_PART_BYTES = 1024 ** 2;
export const MICROPHONE_BUFFER_BYTES = 16 * 1024 ** 2;
// Reserve the final trim and one in-flight disk write copy, plus bounded meter data.
export const MICROPHONE_CREDIT_BYTES = MICROPHONE_BUFFER_BYTES - 2 * MICROPHONE_PART_BYTES - 4096;
export const MICROPHONE_MAX_BYTES = 2 * 1024 ** 3;
export const MICROPHONE_MAX_SECONDS = 14400;

export type PcmCaptureMessage =
  | { type: "chunk"; data: ArrayBuffer; sampleCount: number }
  | { type: "progress"; sampleCount: number; bufferedBytes: number; level: number }
  | { type: "stopped"; sampleCount: number; reason?: "limit" }
  | { type: "error"; code: "buffer_full" | "recording_limit" | "capture_failed" };
export interface PcmCaptureOptions { sampleRate: number; partBytes: number; creditBytes: number; maxSamples: number }

export function encodeWavHeader(sampleRate: number, sampleCount: number): ArrayBuffer {
  if (!Number.isInteger(sampleRate) || sampleRate < 8000 || sampleRate > 192000
    || !Number.isSafeInteger(sampleCount) || sampleCount <= 0
    || sampleCount > sampleRate * MICROPHONE_MAX_SECONDS || sampleCount * 2 + 44 > MICROPHONE_MAX_BYTES) {
    throw new RangeError("Invalid PCM source bounds");
  }
  const header = new ArrayBuffer(44);
  const view = new DataView(header);
  const text = (offset: number, value: string) => { for (let index = 0; index < value.length; index += 1) view.setUint8(offset + index, value.charCodeAt(index)); };
  text(0, "RIFF"); view.setUint32(4, 36 + sampleCount * 2, true); text(8, "WAVEfmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, "data");
  view.setUint32(40, sampleCount * 2, true);
  return header;
}

/** The audio thread owns the credit ledger, including partial and transferred samples. */
export class PcmCaptureBuffer {
  private readonly options: PcmCaptureOptions;
  private readonly emit: (message: PcmCaptureMessage) => void;
  private buffer: ArrayBuffer | null = null;
  private view: DataView | null = null;
  private position = 0;
  private availableBytes: number;
  private emittedBytes = 0;
  private sampleCount = 0;
  private meterSamples = 0;
  private meterSquares = 0;
  private progressPending = false;
  private active = true;

  constructor(options: PcmCaptureOptions, emit: (message: PcmCaptureMessage) => void) {
    this.options = options; this.emit = emit; this.availableBytes = options.creditBytes;
    if (!Number.isInteger(options.partBytes) || options.partBytes < 2 || options.partBytes % 2
      || options.partBytes > MICROPHONE_PART_BYTES || options.creditBytes < options.partBytes
      || options.creditBytes > MICROPHONE_CREDIT_BYTES || !Number.isInteger(options.creditBytes)
      || options.creditBytes % 2 || !Number.isSafeInteger(options.maxSamples) || options.maxSamples < 1
      || !Number.isInteger(options.sampleRate) || options.sampleRate < 8000 || options.sampleRate > 192000) {
      throw new RangeError("Invalid capture buffer bounds");
    }
  }

  push(samples: Float32Array): boolean {
    if (!this.active) return false;
    const count = Math.min(samples.length, this.options.maxSamples - this.sampleCount);
    if (count * 2 > this.availableBytes) return this.fail("buffer_full");
    for (let index = 0; index < count; index += 1) {
      const input = samples[index];
      if (!Number.isFinite(input)) return this.fail("capture_failed");
      const sample = Math.max(-1, Math.min(1, input));
      if (!this.buffer) { this.buffer = new ArrayBuffer(this.options.partBytes); this.view = new DataView(this.buffer); }
      this.view!.setInt16(this.position, Math.round(sample * (sample < 0 ? 32768 : 32767)), true);
      this.position += 2; this.availableBytes -= 2; this.sampleCount += 1;
      this.meterSquares += sample * sample; this.meterSamples += 1;
      if (this.position === this.options.partBytes) this.flush();
    }
    if (this.sampleCount === this.options.maxSamples) { this.stop("limit"); return false; }
    if (this.meterSamples >= this.options.sampleRate / 4 && !this.progressPending) {
      this.progressPending = true;
      this.emit({ type: "progress", sampleCount: this.sampleCount, bufferedBytes: this.options.creditBytes - this.availableBytes,
        level: Math.min(1, Math.sqrt(this.meterSquares / this.meterSamples)) });
      this.meterSamples = 0; this.meterSquares = 0;
    }
    return this.active;
  }

  acknowledge(bytes: number): void {
    if (!this.active) return;
    if (!Number.isInteger(bytes) || bytes <= 0 || bytes % 2 || bytes > this.emittedBytes) { this.fail("capture_failed"); return; }
    this.emittedBytes -= bytes; this.availableBytes += bytes;
  }

  acknowledgeProgress(): void { this.progressPending = false; }

  stop(reason?: "limit"): void {
    if (!this.active) return;
    this.flush(); this.active = false;
    this.emit({ type: "stopped", sampleCount: this.sampleCount, ...(reason ? { reason } : {}) });
  }

  private flush(): void {
    if (!this.buffer || !this.position) return;
    const data = this.position === this.options.partBytes ? this.buffer : this.buffer.slice(0, this.position);
    this.buffer = null; this.view = null; this.position = 0; this.emittedBytes += data.byteLength;
    this.emit({ type: "chunk", data, sampleCount: this.sampleCount });
  }

  private fail(code: "buffer_full" | "recording_limit" | "capture_failed"): false {
    this.active = false; this.buffer = null; this.view = null;
    this.emit({ type: "error", code });
    return false;
  }
}
