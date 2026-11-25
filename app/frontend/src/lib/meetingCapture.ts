import workletUrl from "@/lib/meetingCapture.worklet.ts?worker&url";
import {
  CAPTURE_CREDIT_BYTES, CAPTURE_FRAME_BYTES, CAPTURE_SAMPLE_RATE, CaptureMonitor, captureMaxFrames, capturePartFrames,
  encodeStereoWavHeader, type CaptureMessage, type CaptureMonitorState,
} from "@/lib/meetingCapturePcm";

export type MeetingCaptureErrorCode = "insecure_context" | "unsupported" | "permission_denied" | "share_cancelled"
  | "system_audio_missing" | "device_unavailable" | "device_interrupted" | "buffer_full" | "storage_full"
  | "storage_unavailable" | "empty_recording" | "capture_failed";
export class MeetingCaptureError extends Error {
  readonly code: MeetingCaptureErrorCode;
  constructor(code: MeetingCaptureErrorCode) { super(code); this.name = "MeetingCaptureError"; this.code = code; }
}
export interface MeetingCaptureProgress extends CaptureMonitorState { elapsedSeconds: number; bufferedBytes: number; microphoneLost: boolean }
export interface MeetingCapturePart { startFrame: number; frameCount: number; data: ArrayBuffer }
export interface RecordedMeetingCapture { file: File; frameCount: number; sampleRate: number; durationSeconds: number; dispose: () => Promise<void> }
export interface MeetingCaptureOptions {
  deviceId?: string;
  signal?: AbortSignal;
  onProgress?: (progress: MeetingCaptureProgress) => void;
  /** Called in capture order once a part is in the local file. */
  onPart?: (part: MeetingCapturePart) => void;
  onError?: (error: MeetingCaptureError) => void;
  /** The browser's own "stop sharing" control or the end of the system audio track; callers finish the recording. */
  onShareEnded?: () => void;
  onLimit?: () => void;
}
export interface MeetingCapture {
  start: () => Promise<void>;
  stop: () => Promise<RecordedMeetingCapture>;
  cancel: () => Promise<void>;
  setMicrophoneMuted: (muted: boolean) => void;
  readonly sampleRate: number;
}

/** Chromium options for the screen picker that the DOM typings do not describe yet. */
interface SystemAudioDisplayOptions extends DisplayMediaStreamOptions {
  systemAudio: "include"; selfBrowserSurface: "exclude"; surfaceSwitching: "exclude"; monitorTypeSurfaces: "include";
}

export function meetingCaptureSupportError(): MeetingCaptureErrorCode | null {
  if (!globalThis.isSecureContext) return "insecure_context";
  if (!navigator.mediaDevices?.getUserMedia || !navigator.mediaDevices?.getDisplayMedia || !navigator.storage?.getDirectory
    || typeof AudioContext === "undefined" || typeof AudioWorkletNode === "undefined") return "unsupported";
  return null;
}
function mappedError(failure: unknown, fallback: MeetingCaptureErrorCode): MeetingCaptureError {
  if (failure instanceof MeetingCaptureError) return failure;
  const name = failure instanceof Error || failure instanceof DOMException ? failure.name : "";
  if (name === "QuotaExceededError") return new MeetingCaptureError("storage_full");
  if (fallback === "share_cancelled" && ["NotAllowedError", "AbortError"].includes(name)) return new MeetingCaptureError("share_cancelled");
  if (["NotAllowedError", "PermissionDeniedError", "SecurityError"].includes(name)
    && (fallback === "device_unavailable" || fallback === "share_cancelled")) return new MeetingCaptureError("permission_denied");
  return new MeetingCaptureError(fallback);
}
function openContext(): AudioContext {
  try { return new AudioContext({ sampleRate: CAPTURE_SAMPLE_RATE }); }
  catch { return new AudioContext(); }
}

/**
 * Captures this computer's microphone (channel 0) and the system audio of the shared screen (channel 1)
 * into one owned OPFS WAV. Screen video is stopped as soon as the audio track is confirmed; no frame is read.
 */
export function createMeetingCapture(options: MeetingCaptureOptions): MeetingCapture {
  let state: "idle" | "starting" | "recording" | "stopping" | "done" | "failed" | "cancelled" = "idle";
  let failure: MeetingCaptureError | null = null;
  const aborter = new AbortController();
  const monitor = new CaptureMonitor();
  let context: AudioContext | null = null;
  let microphone: MediaStream | null = null;
  let display: MediaStream | null = null;
  let sources: AudioNode[] = [];
  let node: AudioWorkletNode | null = null;
  let directory: FileSystemDirectoryHandle | null = null;
  let fileHandle: FileSystemFileHandle | null = null;
  let writer: FileSystemWritableFileStream | null = null;
  let filename: string | null = null;
  let removed = false;
  let cleanup = Promise.resolve();
  let writeTail = Promise.resolve();
  let receivedFrames = 0;
  let writtenFrames = 0;
  let sampleRate = 0;
  let microphoneLost = false;
  let stopResult: Promise<RecordedMeetingCapture> | null = null;
  let stoppedResolve: ((frames: number) => void) | null = null;
  let automaticFrames: number | null = null;

  function check() { if (failure) throw failure; aborter.signal.throwIfAborted(); }
  function detach() {
    window.removeEventListener("pagehide", leave);
    window.removeEventListener("beforeunload", confirmLeave);
    options.signal?.removeEventListener("abort", leave);
  }
  function stopTracks(stream: MediaStream | null) {
    for (const track of stream?.getTracks() ?? []) {
      track.removeEventListener("ended", microphoneEnded); track.removeEventListener("ended", shareEnded); track.stop();
    }
  }
  function closeAudio() {
    stopTracks(microphone); stopTracks(display); microphone = null; display = null;
    for (const source of sources) source.disconnect();
    sources = [];
    if (node) { node.removeEventListener("processorerror", processorError); node.disconnect(); node.port.onmessage = null; node.port.close(); node = null; }
    if (context) {
      context.removeEventListener("statechange", contextChanged);
      if (context.state !== "closed") void context.close().catch(() => undefined);
      context = null;
    }
  }
  async function removeOwnedFile(): Promise<void> {
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
  function fail(error: MeetingCaptureError) {
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
  function confirmLeave(event: BeforeUnloadEvent) { if (state === "recording" || state === "stopping") event.preventDefault(); }
  function microphoneEnded() { if (state === "recording") microphoneLost = true; }
  function shareEnded() { if (state === "recording") options.onShareEnded?.(); }
  function processorError() { fail(new MeetingCaptureError("capture_failed")); }
  function contextChanged() {
    if (!context || context.state === "running") return;
    if (context.state === "closed") { if (state === "recording") fail(new MeetingCaptureError("device_interrupted")); return; }
    void context.resume().catch(() => fail(new MeetingCaptureError("device_interrupted")));
  }
  function abortable<T>(operation: Promise<T>): Promise<T> {
    check();
    return new Promise<T>((resolve, reject) => {
      const abort = () => reject(failure ?? aborter.signal.reason);
      aborter.signal.addEventListener("abort", abort, { once: true });
      operation.then((value) => { aborter.signal.removeEventListener("abort", abort); resolve(value); },
        (error: unknown) => { aborter.signal.removeEventListener("abort", abort); reject(error); });
    });
  }
  function receive(event: MessageEvent<CaptureMessage>) {
    if (state !== "recording" && state !== "stopping") return;
    const message = event.data;
    if (message.type === "error") { fail(new MeetingCaptureError(message.code)); return; }
    if (message.type === "levels") {
      if (Number.isSafeInteger(message.frameCount) && Array.isArray(message.blocks)) {
        options.onProgress?.({ ...monitor.push(message.blocks), elapsedSeconds: message.frameCount / sampleRate,
          bufferedBytes: message.bufferedBytes, microphoneLost });
      }
      node?.port.postMessage({ type: "levels-credit" });
      return;
    }
    if (message.type === "stopped") {
      if (message.frameCount !== receivedFrames) { fail(new MeetingCaptureError("capture_failed")); return; }
      if (state === "recording" && message.reason === "limit") {
        automaticFrames = message.frameCount; closeAudio(); options.onLimit?.(); return;
      }
      if (state !== "stopping") { fail(new MeetingCaptureError("capture_failed")); return; }
      stoppedResolve?.(message.frameCount);
      return;
    }
    if (message.type !== "part") { fail(new MeetingCaptureError("capture_failed")); return; }
    const { data, startFrame, frameCount } = message;
    if (!(data instanceof ArrayBuffer) || !frameCount || data.byteLength !== frameCount * CAPTURE_FRAME_BYTES || startFrame !== receivedFrames) {
      fail(new MeetingCaptureError("capture_failed")); return;
    }
    receivedFrames += frameCount;
    writeTail = writeTail.then(async () => {
      check();
      if (!writer) throw new MeetingCaptureError("storage_unavailable");
      await writer.write(data); check();
      writtenFrames += frameCount;
      node?.port.postMessage({ type: "credit", bytes: data.byteLength });
      options.onPart?.({ startFrame, frameCount, data });
    });
    void writeTail.catch((error: unknown) => { if (!aborter.signal.aborted) fail(mappedError(error, "storage_unavailable")); });
  }

  async function start() {
    if (state !== "idle") throw new MeetingCaptureError("capture_failed");
    let fallback: MeetingCaptureErrorCode = "capture_failed";
    state = "starting";
    window.addEventListener("pagehide", leave); window.addEventListener("beforeunload", confirmLeave);
    options.signal?.addEventListener("abort", leave, { once: true });
    try {
      if (options.signal?.aborted) { await cancel(); check(); }
      const unsupported = meetingCaptureSupportError(); if (unsupported) throw new MeetingCaptureError(unsupported);
      // The context, its resume and the screen picker all start inside the user's click: the picker needs that activation.
      context = openContext();
      if (!context.audioWorklet) throw new MeetingCaptureError("unsupported");
      sampleRate = context.sampleRate;
      if (!Number.isInteger(sampleRate) || sampleRate < 8000 || sampleRate > 192000) throw new MeetingCaptureError("unsupported");
      const resumed = context.resume(); void resumed.catch(() => undefined);
      fallback = "share_cancelled";
      const picker: SystemAudioDisplayOptions = {
        video: true,
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
        systemAudio: "include", selfBrowserSurface: "exclude", surfaceSwitching: "exclude", monitorTypeSurfaces: "include",
      };
      const shared = navigator.mediaDevices.getDisplayMedia(picker).then((result) => {
        if (aborter.signal.aborted) stopTracks(result);
        return result;
      });
      display = await abortable(shared); check();
      // The video track is never read; ending it keeps only the system audio capture.
      for (const track of display.getVideoTracks()) track.stop();
      const systemTracks = display.getAudioTracks().filter((track) => track.readyState === "live");
      if (!systemTracks.length) throw new MeetingCaptureError("system_audio_missing");
      fallback = "device_unavailable";
      const permission = navigator.mediaDevices.getUserMedia({ video: false, audio: {
        channelCount: 1, ...(options.deviceId ? { deviceId: { exact: options.deviceId } } : {}),
      } }).then((result) => {
        if (aborter.signal.aborted) stopTracks(result);
        return result;
      });
      microphone = await abortable(permission); check();
      if (!microphone.getAudioTracks().length || microphone.getAudioTracks().some((track) => track.readyState !== "live")) throw new MeetingCaptureError("device_unavailable");
      await abortable(resumed); check();
      fallback = "storage_unavailable";
      const root = await navigator.storage.getDirectory(); check();
      directory = await root.getDirectoryHandle("voiceup-meeting-capture", { create: true }); check();
      filename = `${crypto.randomUUID()}.wav`;
      fileHandle = await directory.getFileHandle(filename, { create: true }); check();
      if (typeof fileHandle.createWritable !== "function") throw new MeetingCaptureError("unsupported");
      writer = await fileHandle.createWritable(); check();
      await writer.write(new ArrayBuffer(44)); check();
      fallback = "capture_failed";
      const audio = context; if (!audio) { check(); throw new MeetingCaptureError("capture_failed"); }
      await audio.audioWorklet.addModule(workletUrl); check();
      if (audio.state !== "running") throw new MeetingCaptureError("device_interrupted");
      node = new AudioWorkletNode(audio, "voiceup-meeting-capture", {
        numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1], channelCount: 2,
        channelCountMode: "explicit", channelInterpretation: "discrete",
        processorOptions: { sampleRate, partFrames: capturePartFrames(sampleRate), creditBytes: CAPTURE_CREDIT_BYTES, maxFrames: captureMaxFrames(sampleRate) },
      });
      node.port.onmessage = receive; node.addEventListener("processorerror", processorError);
      audio.addEventListener("statechange", contextChanged);
      const merger = audio.createChannelMerger(2);
      const microphoneSource = audio.createMediaStreamSource(microphone);
      const systemSource = audio.createMediaStreamSource(new MediaStream(systemTracks));
      sources = [microphoneSource, systemSource, merger];
      for (const track of microphone.getAudioTracks()) track.addEventListener("ended", microphoneEnded);
      for (const track of systemTracks) track.addEventListener("ended", shareEnded);
      state = "recording";
      node.connect(audio.destination); merger.connect(node);
      microphoneSource.connect(merger, 0, 0); systemSource.connect(merger, 0, 1);
    } catch (error) {
      if (!aborter.signal.aborted) fail(mappedError(error, fallback));
      closeAudio(); await removeOwnedFile().catch(() => undefined);
      throw failure ?? error;
    }
  }

  async function finish(): Promise<RecordedMeetingCapture> {
    check();
    if (state !== "recording" || (!node && automaticFrames === null)) throw new MeetingCaptureError("capture_failed");
    state = "stopping";
    let deadline: ReturnType<typeof setTimeout> | undefined;
    try {
      const stopped = automaticFrames === null ? new Promise<number>((resolve) => { stoppedResolve = resolve; }) : Promise.resolve(automaticFrames);
      if (automaticFrames === null) {
        deadline = setTimeout(() => fail(new MeetingCaptureError("device_interrupted")), 5000);
        node?.port.postMessage({ type: "stop" });
      }
      const frames = await abortable(stopped); clearTimeout(deadline);
      closeAudio();
      await abortable(writeTail); check();
      if (!frames) throw new MeetingCaptureError("empty_recording");
      if (frames !== writtenFrames || !writer || !fileHandle) throw new MeetingCaptureError("capture_failed");
      const currentWriter = writer;
      await currentWriter.write({ type: "write", position: 0, data: encodeStereoWavHeader(sampleRate, frames) }); check();
      await currentWriter.close(); writer = null; check();
      const file = await fileHandle.getFile(); check();
      if (file.size !== frames * CAPTURE_FRAME_BYTES + 44) throw new MeetingCaptureError("capture_failed");
      state = "done"; detach();
      return { file, frameCount: frames, sampleRate, durationSeconds: frames / sampleRate, dispose: removeOwnedFile };
    } catch (error) {
      if (!aborter.signal.aborted) fail(mappedError(error, "storage_unavailable"));
      await removeOwnedFile().catch(() => undefined);
      throw failure ?? error;
    } finally { clearTimeout(deadline); stoppedResolve = null; }
  }
  function stop(): Promise<RecordedMeetingCapture> { if (!stopResult) stopResult = finish(); return stopResult; }
  function setMicrophoneMuted(muted: boolean) { node?.port.postMessage({ type: "microphone", muted }); }
  return { start, stop, cancel, setMicrophoneMuted, get sampleRate() { return sampleRate; } };
}
