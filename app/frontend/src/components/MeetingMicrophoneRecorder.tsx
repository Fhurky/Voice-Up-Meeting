import { useEffect, useRef, useState } from "react";
import { useIntl } from "@/contexts/IntlContext";
import { Icon } from "@/components/ui/Icon";
import { meetingErrorKey, recordingTime } from "@/lib/meetingErrors";
import { createMicrophoneCapture, listMicrophoneDevices, microphoneSupportError, MicrophoneCaptureError,
  type MicrophoneCapture, type MicrophoneCaptureProgress, type RecordedMicrophoneFile } from "@/lib/microphoneCapture";
import type { Meeting } from "@/services/meetings";
import type { UploadProgress } from "@/services/meetingUpload";

type Session = { capture: MicrophoneCapture; controller: AbortController; recording?: RecordedMicrophoneFile; stopping?: boolean };
type Phase = "idle" | "requesting" | "recording" | "stopping" | "uploading" | "ready" | "cancelling";
type Props = {
  onBeforeStart: () => boolean;
  onBusyChange: (busy: boolean) => void;
  onAnalyze: (file: File, signal: AbortSignal, progress: (value: UploadProgress) => void) => Promise<Meeting>;
  onComplete: (meeting: Meeting) => void;
  onAbandon?: () => void;
};

export function MeetingMicrophoneRecorder({ onBeforeStart, onBusyChange, onAnalyze, onComplete, onAbandon }: Props) {
  const { t, locale } = useIntl();
  const [phase, setPhase] = useState<Phase>("idle");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [device, setDevice] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<MicrophoneCaptureProgress>({ elapsedSeconds: 0, bufferedBytes: 0, level: 0 });
  const [upload, setUpload] = useState<UploadProgress | null>(null);
  const [limitReached, setLimitReached] = useState(false);
  const active = useRef<Session | null>(null);
  const mounted = useRef(false);
  const abandon = useRef(onAbandon);
  const busyChange = useRef(onBusyChange);
  useEffect(() => { abandon.current = onAbandon; busyChange.current = onBusyChange; }, [onAbandon, onBusyChange]);
  const support = microphoneSupportError();

  async function release(session: Session) {
    session.controller.abort();
    abandon.current?.();
    try { await session.capture.cancel(); }
    finally { await session.recording?.dispose(); }
  }
  useEffect(() => {
    mounted.current = true;
    let present = true;
    const refresh = () => { void listMicrophoneDevices().then((items) => { if (present) setDevices(items); }).catch(() => {}); };
    const leave = () => {
      const session = active.current; active.current = null;
      if (!session) return;
      void release(session).catch(() => {});
      if (mounted.current) { setPhase("idle"); setError("microphone.error.device_interrupted"); busyChange.current(false); }
    };
    refresh(); navigator.mediaDevices?.addEventListener?.("devicechange", refresh);
    window.addEventListener("pagehide", leave); window.addEventListener("beforeunload", leave);
    return () => {
      present = false; mounted.current = false;
      navigator.mediaDevices?.removeEventListener?.("devicechange", refresh);
      window.removeEventListener("pagehide", leave); window.removeEventListener("beforeunload", leave);
      leave();
    };
  }, []);

  function fail(session: Session, key: string) {
    if (active.current !== session) return;
    active.current = null;
    void release(session).catch(() => {});
    setPhase("idle"); setError(key); onBusyChange(false);
  }
  async function start() {
    if (active.current || support || !onBeforeStart()) return;
    setError(null); setProgress({ elapsedSeconds: 0, bufferedBytes: 0, level: 0 }); setUpload(null); setLimitReached(false);
    setPhase("requesting"); onBusyChange(true);
    const session: Session = {
      controller: new AbortController(),
      capture: createMicrophoneCapture({ deviceId: device || undefined,
        onProgress: (value) => { if (active.current === session) setProgress(value); },
        onError: (failure) => fail(session, `microphone.error.${failure.code}`),
        onLimit: () => { if (active.current === session) { setLimitReached(true); void stop(session); } },
      }),
    };
    active.current = session;
    try {
      await session.capture.start();
      if (active.current !== session) return;
      setPhase("recording");
      void listMicrophoneDevices().then((items) => { if (active.current === session) setDevices(items); }).catch(() => {});
    } catch (failure) {
      const code = failure instanceof MicrophoneCaptureError ? failure.code : "capture_failed";
      fail(session, `microphone.error.${code}`);
    }
  }
  async function analyze(session: Session) {
    if (!session.recording || active.current !== session) return;
    setPhase("uploading"); setError(null); setUpload(null);
    try {
      const result = await onAnalyze(session.recording.file, session.controller.signal,
        (value) => { if (active.current === session) setUpload(value); });
      if (active.current !== session || session.controller.signal.aborted) return;
      await session.recording.dispose();
      if (active.current !== session) return;
      active.current = null; setPhase("idle"); onBusyChange(false); onComplete(result);
    } catch (failure) {
      if (active.current !== session || session.controller.signal.aborted) return;
      setError(meetingErrorKey(failure)); setPhase("ready");
    }
  }
  async function stop(session = active.current) {
    if (!session || active.current !== session || session.stopping || session.recording) return;
    session.stopping = true;
    setPhase("stopping");
    try {
      const recording = await session.capture.stop();
      if (active.current !== session) { await recording.dispose(); return; }
      session.recording = recording;
      await analyze(session);
    } catch (failure) {
      const code = failure instanceof MicrophoneCaptureError ? failure.code : "capture_failed";
      fail(session, `microphone.error.${code}`);
    }
  }
  async function cancel() {
    const session = active.current;
    if (!session) return;
    active.current = null; setPhase("cancelling");
    await release(session).catch(() => {});
    if (!mounted.current) return;
    setPhase("idle"); setError(null); setLimitReached(false); setProgress({ elapsedSeconds: 0, bufferedBytes: 0, level: 0 }); onBusyChange(false);
  }
  const running = phase !== "idle";
  const total = active.current?.recording?.file.size ?? 1;
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  return <section className={`microphone-recorder${phase === "recording" ? " microphone-recording" : ""}`} aria-label={t("microphone.title")} data-recording-state={phase} data-recording-seconds={progress.elapsedSeconds}>
    <div className="form-field"><label htmlFor="meeting-microphone">{t("microphone.device")}</label>
      <select id="meeting-microphone" value={device} disabled={running || Boolean(support)} onChange={(event) => setDevice(event.target.value)}>
        <option value="">{t("microphone.defaultDevice")}</option>
        {devices.filter((item) => item.deviceId && item.deviceId !== "default").map((item, index) => <option key={item.deviceId} value={item.deviceId}>{item.label || t("microphone.deviceNumber", { number: index + 1 })}</option>)}
      </select></div>
    <p className="field-hint">{t("microphone.scopeHint")}</p>
    <div className="microphone-display">
      <span className="microphone-symbol"><Icon name="microphone" size={28} /></span>
      <div><p className="microphone-state" role="status">{t(`microphone.phase.${phase}`)}</p>
        <output className="microphone-timer" aria-label={t("microphone.duration")} aria-live="off">{recordingTime(progress.elapsedSeconds)}</output></div>
      <meter className="microphone-level" min="0" max="1" value={phase === "recording" ? progress.level : 0} aria-label={t("microphone.level")} />
    </div>
    <p className="field-hint">{t("microphone.keepOpen")}</p>
    {limitReached && <p className="notice" role="status">{t("microphone.limitReached")}</p>}
    {phase === "uploading" && <div className="upload-progress">
      <label htmlFor="microphone-upload-progress">{upload ? t("meeting.uploadProgress", { uploaded: number.format(upload.uploadedBytes / 1024 ** 2), total: number.format(total / 1024 ** 2) }) : t("meeting.creating")}</label>
      <progress id="microphone-upload-progress" value={upload?.uploadedBytes ?? 0} max={total} />
      {upload && <p role="status">{t(`meeting.upload.${upload.phase}`)}</p>}
    </div>}
    {(error || support) && <p className="error-message" role="alert">{t(error ?? `microphone.error.${support}`)}</p>}
    {phase === "ready" && <p className="notice">{t("microphone.retryHint")}</p>}
    <div className="action-row">
      {phase === "idle" && <button type="button" disabled={Boolean(support)} onClick={() => void start()}><Icon name="microphone" size={18} />{t("microphone.start")}</button>}
      {phase === "recording" && <button type="button" onClick={() => void stop()}><Icon name="stop" size={16} />{t("microphone.stop")}</button>}
      {phase === "ready" && <button type="button" onClick={() => { const session = active.current; if (session) void analyze(session); }}>{t("microphone.retry")}</button>}
      {running && <button type="button" className="button-secondary" disabled={phase === "cancelling"} onClick={() => void cancel()}>{t("microphone.cancel")}</button>}
    </div>
  </section>;
}
