import { CAPTURE_CHAIN_START, CAPTURE_FRAME_BYTES, CAPTURE_MEMORY_BYTES, hex, nextChain, sha256 } from "@/lib/meetingCapturePcm";

export type CaptureSendFailure =
  | { kind: "gap"; expectedFrame: number }
  | { kind: "conflict" }
  | { kind: "fatal"; code: string }
  | { kind: "retry" };
/** Thrown by the transport so the uploader can tell a resumable gap from a lost session. */
export class CaptureSendError extends Error {
  readonly failure: CaptureSendFailure;
  constructor(failure: CaptureSendFailure) { super(failure.kind); this.name = "CaptureSendError"; this.failure = failure; }
}
export interface CaptureSendRequest { startFrame: number; data: ArrayBuffer; sha256: string }
export interface CaptureUploaderOptions {
  send: (part: CaptureSendRequest) => Promise<{ receivedFrames: number }>;
  memoryBytes?: number;
  now?: () => number;
  /** Waits between drain retries; recording-time retries are paced by new parts, not timers. */
  wait?: (milliseconds: number) => Promise<void>;
  onState?: (state: CaptureUploadState) => void;
}
export interface CaptureUploadState { acknowledgedFrames: number; queuedBytes: number; retrying: boolean; waitingForFile: boolean; failed: string | null }
export interface CaptureUploadResult { frameCount: number; chainSha256: string }

interface QueuedPart { startFrame: number; frameCount: number; data: ArrayBuffer | null; digest: Promise<Uint8Array<ArrayBuffer>> }

const RETRY_START_MS = 1000;
const RETRY_MAX_MS = 30000;

/**
 * Sends capture parts in order, one at a time. Unacknowledged parts stay in memory up to `memoryBytes`;
 * beyond that the newest parts keep only their position and are read back from the sealed local file at drain.
 */
export class CaptureUploader {
  private readonly options: CaptureUploaderOptions;
  private readonly memoryBytes: number;
  private readonly now: () => number;
  private readonly parts: QueuedPart[] = [];
  private chain: Promise<Uint8Array<ArrayBuffer>> = Promise.resolve(CAPTURE_CHAIN_START);
  private nextFrame = 0;
  private acknowledgedFrames = 0;
  private queuedBytes = 0;
  private busy: Promise<void> | null = null;
  private retryAt = 0;
  private failures = 0;
  private waitingForFile = false;
  private failed: string | null = null;

  constructor(options: CaptureUploaderOptions) {
    this.options = options;
    this.memoryBytes = options.memoryBytes ?? CAPTURE_MEMORY_BYTES;
    this.now = options.now ?? Date.now;
  }

  get state(): CaptureUploadState {
    return { acknowledgedFrames: this.acknowledgedFrames, queuedBytes: this.queuedBytes, retrying: this.failures > 0,
      waitingForFile: this.waitingForFile, failed: this.failed };
  }

  add(part: { startFrame: number; frameCount: number; data: ArrayBuffer }): void {
    if (part.startFrame !== this.nextFrame || part.data.byteLength !== part.frameCount * CAPTURE_FRAME_BYTES || !part.frameCount) {
      throw new RangeError("Capture parts must be contiguous and frame aligned");
    }
    this.nextFrame += part.frameCount;
    const digest = sha256(part.data);
    this.chain = Promise.all([this.chain, digest]).then(([chain, value]) => nextChain(chain, value));
    const keep = !this.waitingForFile && this.queuedBytes + part.data.byteLength <= this.memoryBytes;
    // Once one part waits for the file, later parts must too: sending them would leave a gap on the server.
    if (!keep) this.waitingForFile = true;
    this.parts.push({ startFrame: part.startFrame, frameCount: part.frameCount, data: keep ? part.data : null, digest });
    if (keep) this.queuedBytes += part.data.byteLength;
    this.report();
    this.pump();
  }

  /** Sends what memory holds; returns without waiting. Called on every new part and after each acknowledgement. */
  pump(): void {
    if (this.busy || this.failed || this.now() < this.retryAt) return;
    const next = this.parts[0];
    if (!next?.data) return;
    this.busy = this.sendOne(next).finally(() => { this.busy = null; }).then(() => { if (!this.failures) this.pump(); });
  }

  /** After the recording is sealed: sends every remaining part, reading dropped ones from `file`, and returns the chain. */
  async drain(file: File | null, signal?: AbortSignal): Promise<CaptureUploadResult> {
    const wait = this.options.wait ?? ((milliseconds: number) => new Promise<void>((resolve) => setTimeout(resolve, milliseconds)));
    while (this.parts.length) {
      signal?.throwIfAborted();
      if (this.failed) throw new CaptureSendError({ kind: "fatal", code: this.failed });
      if (this.busy) { await this.busy; continue; }
      const next = this.parts[0];
      if (!next.data) {
        if (!file) throw new CaptureSendError({ kind: "fatal", code: "capture_file_missing" });
        const offset = 44 + next.startFrame * CAPTURE_FRAME_BYTES;
        next.data = await file.slice(offset, offset + next.frameCount * CAPTURE_FRAME_BYTES).arrayBuffer();
        if (next.data.byteLength !== next.frameCount * CAPTURE_FRAME_BYTES) throw new CaptureSendError({ kind: "fatal", code: "capture_file_short" });
        this.queuedBytes += next.data.byteLength;
      }
      const delay = this.retryAt - this.now();
      if (delay > 0) await wait(delay);
      this.retryAt = 0;
      this.busy = this.sendOne(next).finally(() => { this.busy = null; });
      await this.busy;
    }
    this.waitingForFile = false; this.report();
    return { frameCount: this.nextFrame, chainSha256: hex(await this.chain) };
  }

  private async sendOne(part: QueuedPart): Promise<void> {
    try {
      const { receivedFrames } = await this.options.send({ startFrame: part.startFrame, data: part.data!, sha256: hex(await part.digest) });
      // An acknowledgement must cover the part it answers; anything else would resend forever.
      if (!Number.isSafeInteger(receivedFrames) || receivedFrames < part.startFrame + part.frameCount || receivedFrames > this.nextFrame) {
        throw new CaptureSendError({ kind: "fatal", code: "capture_acknowledgement_invalid" });
      }
      this.failures = 0; this.retryAt = 0;
      this.acknowledge(receivedFrames);
    } catch (error) {
      const failure: CaptureSendFailure = error instanceof CaptureSendError ? error.failure : { kind: "retry" };
      if (failure.kind === "gap" && failure.expectedFrame > part.startFrame && failure.expectedFrame <= this.nextFrame) {
        // A lost response: the server already holds these frames.
        this.failures = 0; this.acknowledge(failure.expectedFrame);
      } else if (failure.kind === "retry") {
        this.failures += 1;
        this.retryAt = this.now() + Math.min(RETRY_MAX_MS, RETRY_START_MS * 2 ** (this.failures - 1));
      } else {
        this.failed = failure.kind === "fatal" ? failure.code : failure.kind === "gap" ? "capture_gap" : "capture_conflict";
      }
      this.report();
    }
  }

  private acknowledge(receivedFrames: number): void {
    this.acknowledgedFrames = Math.max(this.acknowledgedFrames, receivedFrames);
    while (this.parts.length && this.parts[0].startFrame + this.parts[0].frameCount <= this.acknowledgedFrames) {
      const done = this.parts.shift()!;
      if (done.data) this.queuedBytes -= done.data.byteLength;
    }
    this.report();
  }

  private report(): void { this.options.onState?.(this.state); }
}
