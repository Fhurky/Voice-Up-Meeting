import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useIntl } from "@/contexts/IntlContext";
import { SpeakerResultCard } from "@/components/SpeakerResultCard";
import { Icon } from "@/components/ui/Icon";
import { ApiError } from "@/lib/apiClient";
import { recordingTime } from "@/lib/meetingErrors";
import { createMicrophoneCapture, listMicrophoneDevices, microphoneSupportError, MicrophoneCaptureError,
  type MicrophoneCapture, type MicrophoneCaptureProgress, type RecordedMicrophoneFile } from "@/lib/microphoneCapture";
import { errorMessageKey, jobErrorKey } from "@/lib/speakerErrors";
import { SpeakerService, type SpeakerJob, type SpeakerProfile, type SpeakerResult } from "@/services/speakers";

/** The enrollment API accepts at most 120 seconds; capture stops there automatically. */
export const ENROLLMENT_MAX_SECONDS = 120;
/** Enrollment needs at least 10 seconds of usable speech, so shorter recordings are not sent. */
export const ENROLLMENT_MIN_SECONDS = 10;
/** A peak RMS level below this means the microphone delivered no audible signal. */
export const ENROLLMENT_SILENCE_LEVEL = 0.002;
const POLL_LIMIT = 180;

type Session = {
  capture: MicrophoneCapture; controller: AbortController; recording?: RecordedMicrophoneFile; stopping?: boolean;
  uploadKey: string; jobKey: string; recordingId?: string; job?: SpeakerJob; peak: number;
};
type Phase = "idle" | "requesting" | "recording" | "stopping" | "uploading" | "creating" | "analyzing" | "ready"
  | "succeeded" | "failed" | "cancelling";
type Props = { profile?: SpeakerProfile; onEnrolled: () => void; onBusyChange?: (busy: boolean) => void };
const microphonePhases = new Set<Phase>(["idle", "requesting", "recording", "stopping", "ready", "cancelling"]);

function wait(milliseconds: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, milliseconds);
    signal.addEventListener("abort", () => { clearTimeout(timer); reject(signal.reason); }, { once: true });
  });
}

export function SpeakerMicrophoneEnrollment({ profile, onEnrolled, onBusyChange }: Props) {
  const { t } = useIntl();
  const [phase, setPhase] = useState<Phase>("idle");
  const [name, setName] = useState("");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [device, setDevice] = useState("");
  const [error, setError] = useState<{ key: string; values?: Record<string, string | number> } | null>(null);
  const [progress, setProgress] = useState<MicrophoneCaptureProgress>({ elapsedSeconds: 0, bufferedBytes: 0, level: 0 });
  const [limitReached, setLimitReached] = useState(false);
  const [result, setResult] = useState<SpeakerResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const active = useRef<Session | null>(null);
  const mounted = useRef(false);
  const callbacks = useRef({ onEnrolled, onBusyChange });
  useEffect(() => { callbacks.current = { onEnrolled, onBusyChange }; }, [onEnrolled, onBusyChange]);
  const support = microphoneSupportError();

  function busy(value: boolean) { callbacks.current.onBusyChange?.(value); }
  async function release(session: Session) {
    session.controller.abort();
    try { await session.capture.cancel(); }
    finally { await session.recording?.dispose(); }
  }
  useEffect(() => {
    mounted.current = true;
    let present = true;
    const refresh = () => { void listMicrophoneDevices().then((items) => { if (present) setDevices(items); }).catch(() => {}); };
    refresh(); navigator.mediaDevices?.addEventListener?.("devicechange", refresh);
    return () => {
      present = false; mounted.current = false;
      navigator.mediaDevices?.removeEventListener?.("devicechange", refresh);
      const session = active.current; active.current = null;
      if (session) { void release(session).catch(() => {}); callbacks.current.onBusyChange?.(false); }
    };
  }, []);

  function finish(session: Session, next: Phase, failure: string | null, values?: Record<string, string | number>) {
    if (active.current !== session) return;
    active.current = null;
    void release(session).catch(() => {});
    setPhase(next); setError(failure ? { key: failure, values } : null); busy(false);
  }
  async function start() {
    if (active.current || support) return;
    const normalized = name.trim().replace(/\s+/g, " ");
    if (!profile && !normalized) { setError({ key: "speaker.error.name_required" }); return; }
    setError(null); setResult(null); setJobId(null); setLimitReached(false);
    setProgress({ elapsedSeconds: 0, bufferedBytes: 0, level: 0 });
    setPhase("requesting"); busy(true);
    const session: Session = {
      controller: new AbortController(), uploadKey: crypto.randomUUID(), jobKey: crypto.randomUUID(), peak: 0,
      capture: createMicrophoneCapture({ deviceId: device || undefined, maxSeconds: ENROLLMENT_MAX_SECONDS,
        onProgress: (value) => { if (active.current === session) { session.peak = Math.max(session.peak, value.level); setProgress(value); } },
        onError: (failure) => finish(session, "idle", `microphone.error.${failure.code}`),
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
      finish(session, "idle", `microphone.error.${failure instanceof MicrophoneCaptureError ? failure.code : "capture_failed"}`);
    }
  }
  async function stop(session = active.current) {
    if (!session || active.current !== session || session.stopping || session.recording) return;
    session.stopping = true; setPhase("stopping");
    try {
      const recording = await session.capture.stop();
      if (active.current !== session) { await recording.dispose(); return; }
      session.recording = recording;
      if (session.peak < ENROLLMENT_SILENCE_LEVEL) { finish(session, "failed", "speaker.microphone.silent"); return; }
      if (recording.durationSeconds < ENROLLMENT_MIN_SECONDS) {
        finish(session, "failed", "speaker.microphone.tooShort", { seconds: Math.floor(recording.durationSeconds) }); return;
      }
      await analyze(session);
    } catch (failure) {
      finish(session, "idle", `microphone.error.${failure instanceof MicrophoneCaptureError ? failure.code : "capture_failed"}`);
    }
  }
  async function analyze(session: Session) {
    if (active.current !== session) return;
    const signal = session.controller.signal;
    setError(null);
    try {
      if (!session.job) {
        if (!session.recordingId) {
          if (!session.recording) return;
          setPhase("uploading");
          session.recordingId = (await SpeakerService.upload(session.recording.file, session.uploadKey, signal)).public_id;
        }
        if (active.current !== session) return;
        setPhase("creating");
        const normalized = name.trim().replace(/\s+/g, " ");
        session.job = await SpeakerService.createJob({ recording_public_id: session.recordingId, purpose: "enroll",
          ...(profile ? { profile_public_id: profile.public_id } : { name: normalized }) }, session.jobKey, signal);
        if (active.current !== session) return;
        setJobId(session.job.public_id);
        await session.recording?.dispose(); session.recording = undefined;
      }
      setPhase("analyzing");
      for (let polls = 0; polls < POLL_LIMIT; polls += 1) {
        const job: SpeakerJob = await SpeakerService.job(session.job.public_id, signal);
        if (active.current !== session) return;
        if (job.status === "succeeded" && job.result) {
          setResult(job.result); finish(session, "succeeded", null); callbacks.current.onEnrolled(); return;
        }
        if (job.status === "failed") { finish(session, "failed", jobErrorKey(job.error?.code ?? "unknown")); return; }
        await wait(Math.min(10_000, 2_000 + polls * 250), signal);
      }
      setError({ key: "speaker.jobs.pollingPaused" }); setPhase("ready");
    } catch (failure) {
      if (active.current !== session || signal.aborted) return;
      if (failure instanceof ApiError && failure.code === "recording_expired") {
        finish(session, "failed", errorMessageKey(failure)); return;
      }
      setError({ key: errorMessageKey(failure) }); setPhase("ready");
    }
  }
  async function cancel() {
    const session = active.current;
    if (!session) return;
    active.current = null; setPhase("cancelling");
    await release(session).catch(() => {});
    if (!mounted.current) return;
    setPhase("idle"); setError(null); setLimitReached(false); setProgress({ elapsedSeconds: 0, bufferedBytes: 0, level: 0 }); busy(false);
  }
  function reset() { setPhase("idle"); setError(null); setResult(null); setJobId(null); setLimitReached(false); setProgress({ elapsedSeconds: 0, bufferedBytes: 0, level: 0 }); }

  const running = !["idle", "succeeded", "failed"].includes(phase);
  const capturing = phase === "requesting" || phase === "recording" || phase === "stopping";
  const status = microphonePhases.has(phase) ? `microphone.phase.${phase}` : `speaker.microphone.phase.${phase}`;
  return <section className={`microphone-recorder${phase === "recording" ? " microphone-recording" : ""}`} aria-label={t("speaker.microphone.title")}
    data-recording-state={phase} data-recording-seconds={progress.elapsedSeconds}>
    {profile ? <p className="target-profile">{t("speaker.profiles.target")} <strong>{profile.name}</strong></p> : <div className="field-group">
      <label htmlFor="microphone-speaker-name">{t("speaker.profiles.name")}</label>
      <input id="microphone-speaker-name" value={name} onChange={(event) => setName(event.target.value)} required maxLength={120} disabled={running} autoComplete="off" />
    </div>}
    <div className="form-field"><label htmlFor="enrollment-microphone">{t("microphone.device")}</label>
      <select id="enrollment-microphone" value={device} disabled={running || Boolean(support)} onChange={(event) => setDevice(event.target.value)}>
        <option value="">{t("microphone.defaultDevice")}</option>
        {devices.filter((item) => item.deviceId && item.deviceId !== "default").map((item, index) => <option key={item.deviceId} value={item.deviceId}>{item.label || t("microphone.deviceNumber", { number: index + 1 })}</option>)}
      </select></div>
    <p className="field-hint">{t("speaker.microphone.guide")}</p>
    {capturing && <figure className="enrollment-script">
      <figcaption>{t("speaker.microphone.scriptLabel")}</figcaption>
      <blockquote>{t("speaker.microphone.script")}</blockquote>
      <p className="field-hint">{t("speaker.microphone.freeSpeech")}</p>
    </figure>}
    <div className="microphone-display">
      <span className="microphone-symbol"><Icon name="microphone" size={28} /></span>
      <div><p className="microphone-state" role="status">{t(status)}</p>
        <output className="microphone-timer" aria-label={t("microphone.duration")} aria-live="off">{recordingTime(progress.elapsedSeconds)}</output>
        <p className="field-hint">{t("speaker.microphone.target", { max: ENROLLMENT_MAX_SECONDS })}</p></div>
      <meter className="microphone-level" min="0" max="1" value={phase === "recording" ? progress.level : 0} aria-label={t("microphone.level")} />
    </div>
    {limitReached && <p className="notice" role="status">{t("speaker.microphone.limitReached", { max: ENROLLMENT_MAX_SECONDS })}</p>}
    {(phase === "analyzing" || phase === "ready") && jobId && <p className="field-hint">{t("speaker.microphone.keepOpen")} <Link className="text-link" to={`/speaker-jobs/${encodeURIComponent(jobId)}`}>{t("speaker.microphone.viewJob")}</Link></p>}
    {(error || support) && <p className="error-message" role="alert">{t(error?.key ?? `microphone.error.${support}`, error?.values)}</p>}
    {phase === "failed" && <p className="notice">{t("speaker.microphone.failureHint")}</p>}
    {phase === "succeeded" && result && <SpeakerResultCard result={result} />}
    <div className="action-row">
      {(phase === "idle" || phase === "failed") && <button type="button" disabled={Boolean(support)} onClick={() => void start()}><Icon name="microphone" size={18} />{t(phase === "failed" ? "speaker.microphone.recordAgain" : "microphone.start")}</button>}
      {phase === "recording" && <button type="button" onClick={() => void stop()}><Icon name="stop" size={16} />{t("speaker.microphone.stop")}</button>}
      {phase === "ready" && <button type="button" onClick={() => { const session = active.current; if (session) void analyze(session); }}>{t("common.retry")}</button>}
      {phase === "succeeded" && <button type="button" className="button-secondary" onClick={reset}>{t("speaker.microphone.recordAnother")}</button>}
      {running && <button type="button" className="button-secondary" disabled={phase === "cancelling"} onClick={() => void cancel()}>{t("microphone.cancel")}</button>}
    </div>
  </section>;
}
