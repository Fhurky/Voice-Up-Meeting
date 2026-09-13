import workletUrl from "@/lib/microphone.worklet.ts?worker&url";
import { encodeWavHeader, MICROPHONE_CREDIT_BYTES, MICROPHONE_MAX_BYTES, MICROPHONE_MAX_SECONDS, MICROPHONE_PART_BYTES, type PcmCaptureMessage } from "@/lib/microphonePcm";

export type MicrophoneCaptureErrorCode = "insecure_context" | "unsupported" | "permission_denied" | "device_unavailable"
  | "device_interrupted" | "buffer_full" | "recording_limit" | "storage_full" | "storage_unavailable" | "empty_recording" | "capture_failed";
export class MicrophoneCaptureError extends Error {
  readonly code: MicrophoneCaptureErrorCode;
  constructor(code: MicrophoneCaptureErrorCode) { super(code); this.name = "MicrophoneCaptureError"; this.code = code; }
}
export interface MicrophoneCaptureProgress { elapsedSeconds: number; bufferedBytes: number; level: number }
export interface RecordedMicrophoneFile { file: File; durationSeconds: number; dispose: () => Promise<void> }
export interface MicrophoneCaptureOptions {
  deviceId?: string;
  signal?: AbortSignal;
  onProgress?: (progress: MicrophoneCaptureProgress) => void;
  onError?: (error: MicrophoneCaptureError) => void;
  onLimit?: () => void;
}
export interface MicrophoneCapture { start: () => Promise<void>; stop: () => Promise<RecordedMicrophoneFile>; cancel: () => Promise<void> }

export function microphoneSupportError(): MicrophoneCaptureErrorCode | null {
  if (!globalThis.isSecureContext) return "insecure_context";
  if (!navigator.mediaDevices?.getUserMedia || !navigator.storage?.getDirectory
    || typeof AudioContext === "undefined" || typeof AudioWorkletNode === "undefined") return "unsupported";
  return null;
}
export async function listMicrophoneDevices(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  return (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === "audioinput");
}
function mappedError(failure: unknown, fallback: MicrophoneCaptureErrorCode): MicrophoneCaptureError {
  if (failure instanceof MicrophoneCaptureError) return failure;
  const name = failure instanceof Error || failure instanceof DOMException ? failure.name : "";
  if (name === "QuotaExceededError") return new MicrophoneCaptureError("storage_full");
  if (fallback === "device_unavailable" && ["NotAllowedError", "PermissionDeniedError", "SecurityError"].includes(name)) return new MicrophoneCaptureError("permission_denied");
  return new MicrophoneCaptureError(fallback);
}

/** Captures to one owned OPFS file; successful callers retain it until dispose(). */
export function createMicrophoneCapture(options: MicrophoneCaptureOptions): MicrophoneCapture {
  let state: "idle" | "starting" | "recording" | "stopping" | "done" | "failed" | "cancelled" = "idle";
  let failure: MicrophoneCaptureError | null = null;
  const aborter = new AbortController();
  let context: AudioContext | null = null;
  let stream: MediaStream | null = null;
  let source: MediaStreamAudioSourceNode | null = null;
  let node: AudioWorkletNode | null = null;
  let directory: FileSystemDirectoryHandle | null = null;
  let fileHandle: FileSystemFileHandle | null = null;
  let writer: FileSystemWritableFileStream | null = null;
  let filename: string | null = null;
  let removed = false;
  let cleanup = Promise.resolve();
  let writeTail = Promise.resolve();
  let receivedSamples = 0;
  let writtenSamples = 0;
  let pendingBytes = 0;
  let sampleRate = 0;
  let stopResult: Promise<RecordedMicrophoneFile> | null = null;
  let stoppedResolve: ((samples: number) => void) | null = null;
  let automaticSamples: number | null = null;
  let capturedSamples = 0;
  let lastProgress = { bufferedBytes: 0, level: 0 };

  function check() { if (failure) throw failure; aborter.signal.throwIfAborted(); }
  function progress() {
    if (state !== "recording" && state !== "stopping") return;
    options.onProgress?.({ elapsedSeconds: sampleRate ? capturedSamples / sampleRate : 0,
      bufferedBytes: Math.max(pendingBytes, lastProgress.bufferedBytes), level: lastProgress.level });
  }
  function detach() {
    window.removeEventListener("pagehide", leave);
    window.removeEventListener("beforeunload", leave);
    options.signal?.removeEventListener("abort", leave);
  }
  function closeAudio() {
    for (const track of stream?.getTracks() ?? []) {
      track.removeEventListener("ended", interrupted); track.removeEventListener("mute", interrupted); track.stop();
    }
    stream = null;
    source?.disconnect(); source = null;
    if (node) { node.removeEventListener("processorerror", processorError); node.disconnect(); node.port.onmessage = null; node.port.close(); node = null; }
    if (context) {
      context.removeEventListener("statechange", contextChanged);
      if (context.state !== "closed") void context.close().catch(() => undefined);
      context = null;
    }
  }
  async function removeOwnedFile(): Promise<void> {
    // A late startup resource may arrive during cleanup. Serialize a new pass so it
    // is inspected after the preceding pass instead of reusing an obsolete snapshot.
    cleanup = cleanup.catch(() => undefined).then(async () => {
      const currentWriter = writer; writer = null;
      if (currentWriter) await currentWriter.abort().catch(() => undefined);
      await writeTail.catch(() => undefined);
      if (directory && filename && !removed) {
        try { await directory.removeEntry(filename); removed = true; }
        catch (error) { if (!(error instanceof DOMException && error.name === "NotFoundError")) throw error; }
      }
    });
    await cleanup;
  }
  function fail(error: MicrophoneCaptureError) {
    if (state === "cancelled" || failure || state === "done") return;
    failure = error; state = "failed"; aborter.abort(error); detach(); closeAudio();
    void removeOwnedFile().catch(() => undefined);
    options.onError?.(error);
  }
  async function cancel() {
    if (state === "done") return;
    if (state !== "failed") state = "cancelled";
    aborter.abort(); detach(); closeAudio();
    await removeOwnedFile();
  }
  function leave() { void cancel().catch(() => undefined); }
  function interrupted() { if (state === "recording" || state === "stopping") fail(new MicrophoneCaptureError("device_interrupted")); }
  function processorError() { fail(new MicrophoneCaptureError("capture_failed")); }
  function contextChanged() { if (context?.state !== "running") interrupted(); }
  function abortable<T>(operation: Promise<T>): Promise<T> {
    check();
    return new Promise<T>((resolve, reject) => {
      const abort = () => reject(failure ?? aborter.signal.reason);
      aborter.signal.addEventListener("abort", abort, { once: true });
      operation.then((value) => { aborter.signal.removeEventListener("abort", abort); resolve(value); },
        (error: unknown) => { aborter.signal.removeEventListener("abort", abort); reject(error); });
    });
  }
  function receive(event: MessageEvent<PcmCaptureMessage>) {
    if (state !== "recording" && state !== "stopping") return;
    const message = event.data;
    if (message.type === "error") { fail(new MicrophoneCaptureError(message.code)); return; }
    if (message.type === "progress") {
      if (Number.isSafeInteger(message.sampleCount) && message.sampleCount >= capturedSamples
        && Number.isFinite(message.bufferedBytes) && Number.isFinite(message.level)) {
        capturedSamples = message.sampleCount;
        lastProgress = { bufferedBytes: message.bufferedBytes, level: message.level }; progress();
      }
      node?.port.postMessage({ type: "progress-credit" });
      return;
    }
    if (message.type === "stopped") {
      if (message.sampleCount !== receivedSamples) { fail(new MicrophoneCaptureError("capture_failed")); return; }
      capturedSamples = message.sampleCount; lastProgress = { bufferedBytes: pendingBytes, level: 0 }; progress();
      if (state === "recording" && message.reason === "limit") {
        automaticSamples = message.sampleCount; closeAudio(); options.onLimit?.(); return;
      }
      if (state !== "stopping") { fail(new MicrophoneCaptureError("capture_failed")); return; }
      stoppedResolve?.(message.sampleCount);
      return;
    }
    if (message.type !== "chunk") { fail(new MicrophoneCaptureError("capture_failed")); return; }
    const data = message.data;
    const bytes = data.byteLength;
    if (!(data instanceof ArrayBuffer) || !bytes || bytes % 2 || bytes > MICROPHONE_PART_BYTES
      || receivedSamples + bytes / 2 !== message.sampleCount || pendingBytes + bytes > MICROPHONE_CREDIT_BYTES) {
      fail(new MicrophoneCaptureError("capture_failed")); return;
    }
    receivedSamples += bytes / 2; capturedSamples = Math.max(capturedSamples, receivedSamples); pendingBytes += bytes;
    writeTail = writeTail.then(async () => {
      check();
      if (!writer) throw new MicrophoneCaptureError("storage_unavailable");
      await writer.write(data); check();
      writtenSamples += bytes / 2; pendingBytes -= bytes;
      if (!node) lastProgress = { bufferedBytes: pendingBytes, level: 0 };
      node?.port.postMessage({ type: "credit", bytes });
      progress();
    });
    void writeTail.catch((error: unknown) => { if (!aborter.signal.aborted) fail(mappedError(error, "storage_unavailable")); });
  }

  async function start() {
    if (state !== "idle") throw new MicrophoneCaptureError("capture_failed");
    let fallback: MicrophoneCaptureErrorCode = "capture_failed";
    state = "starting";
    window.addEventListener("pagehide", leave); window.addEventListener("beforeunload", leave);
    options.signal?.addEventListener("abort", leave, { once: true });
    try {
      if (options.signal?.aborted) { await cancel(); check(); }
      const unsupported = microphoneSupportError(); if (unsupported) throw new MicrophoneCaptureError(unsupported);
      // Construct and resume inside the user's start action to satisfy browser activation rules.
      context = new AudioContext();
      if (!context.audioWorklet) throw new MicrophoneCaptureError("unsupported");
      sampleRate = context.sampleRate;
      if (!Number.isInteger(sampleRate) || sampleRate < 8000 || sampleRate > 192000) throw new MicrophoneCaptureError("unsupported");
      const resumed = context.resume(); void resumed.catch(() => undefined);
      fallback = "device_unavailable";
      const permission = navigator.mediaDevices.getUserMedia({ video: false, audio: {
        channelCount: 1, ...(options.deviceId ? { deviceId: { exact: options.deviceId } } : {}),
      } }).then((result) => {
        if (aborter.signal.aborted) for (const track of result.getTracks()) track.stop();
        return result;
      });
      stream = await abortable(permission); check();
      if (!stream.getAudioTracks().length || stream.getAudioTracks().some((track) => track.readyState !== "live")) throw new MicrophoneCaptureError("device_unavailable");
      for (const track of stream.getTracks()) { track.addEventListener("ended", interrupted); track.addEventListener("mute", interrupted); }
      await abortable(resumed); check();
      fallback = "storage_unavailable";
      const root = await navigator.storage.getDirectory(); check();
      directory = await root.getDirectoryHandle("voiceup-microphone", { create: true }); check();
      filename = `${crypto.randomUUID()}.wav`;
      fileHandle = await directory.getFileHandle(filename, { create: true }); check();
      if (typeof fileHandle.createWritable !== "function") throw new MicrophoneCaptureError("unsupported");
      writer = await fileHandle.createWritable(); check();
      await writer.write(new ArrayBuffer(44)); check();
      fallback = "capture_failed";
      const audio = context; if (!audio) { check(); throw new MicrophoneCaptureError("capture_failed"); }
      await audio.audioWorklet.addModule(workletUrl); check();
      if (audio.state !== "running") throw new MicrophoneCaptureError("device_interrupted");
      node = new AudioWorkletNode(audio, "voiceup-microphone-pcm", {
        numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1], channelCount: 1, channelCountMode: "explicit",
        processorOptions: { sampleRate, partBytes: MICROPHONE_PART_BYTES, creditBytes: MICROPHONE_CREDIT_BYTES,
          maxSamples: Math.min(sampleRate * MICROPHONE_MAX_SECONDS, Math.floor((MICROPHONE_MAX_BYTES - 44) / 2)) },
      });
      node.port.onmessage = receive; node.addEventListener("processorerror", processorError);
      audio.addEventListener("statechange", contextChanged);
      if (!stream || stream.getAudioTracks().some((track) => track.readyState !== "live" || track.muted)) throw new MicrophoneCaptureError("device_unavailable");
      source = audio.createMediaStreamSource(stream);
      state = "recording";
      node.connect(audio.destination); source.connect(node);
      progress();
    } catch (error) {
      if (!aborter.signal.aborted) fail(mappedError(error, fallback));
      closeAudio(); await removeOwnedFile().catch(() => undefined);
      throw failure ?? error;
    }
  }

  async function finish(): Promise<RecordedMicrophoneFile> {
    check();
    if (state !== "recording" || (!node && automaticSamples === null)) throw new MicrophoneCaptureError("capture_failed");
    state = "stopping";
    let deadline: ReturnType<typeof setTimeout> | undefined;
    try {
      const stopped = automaticSamples === null ? new Promise<number>((resolve) => { stoppedResolve = resolve; }) : Promise.resolve(automaticSamples);
      if (automaticSamples === null) {
        deadline = setTimeout(() => fail(new MicrophoneCaptureError("device_interrupted")), 5000);
        node?.port.postMessage({ type: "stop" });
      }
      const samples = await abortable(stopped); clearTimeout(deadline);
      closeAudio();
      await abortable(writeTail); check();
      if (!samples) throw new MicrophoneCaptureError("empty_recording");
      if (samples !== writtenSamples || !writer || !fileHandle) throw new MicrophoneCaptureError("capture_failed");
      const currentWriter = writer;
      await currentWriter.write({ type: "write", position: 0, data: encodeWavHeader(sampleRate, samples) }); check();
      await currentWriter.close(); writer = null; check();
      const file = await fileHandle.getFile(); check();
      if (file.size !== samples * 2 + 44) throw new MicrophoneCaptureError("capture_failed");
      state = "done"; detach();
      return { file, durationSeconds: samples / sampleRate, dispose: removeOwnedFile };
    } catch (error) {
      if (!aborter.signal.aborted) fail(mappedError(error, "storage_unavailable"));
      await removeOwnedFile().catch(() => undefined);
      throw failure ?? error;
    } finally { clearTimeout(deadline); stoppedResolve = null; }
  }
  function stop(): Promise<RecordedMicrophoneFile> { if (!stopResult) stopResult = finish(); return stopResult; }
  return { start, stop, cancel };
}
