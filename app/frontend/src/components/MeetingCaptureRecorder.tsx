import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useIntl } from "@/contexts/IntlContext";
import { Icon } from "@/components/ui/Icon";
import { CaptureUploader, type CaptureUploadState } from "@/lib/captureUpload";
import { createMeetingCapture, meetingCaptureSupportError, MeetingCaptureError,
  type MeetingCapture, type MeetingCaptureProgress } from "@/lib/meetingCapture";
import { meetingErrorKey, recordingTime } from "@/lib/meetingErrors";
import { listMicrophoneDevices } from "@/lib/microphoneCapture";
import { MeetingService, type Meeting, type MeetingCaptureCreate } from "@/services/meetings";
import { captureTransport } from "@/services/meetingCaptureTransport";

type Phase = "idle" | "requesting" | "recording" | "finishing" | "failed";
type Session = { capture: MeetingCapture; uploader: CaptureUploader; meetingId?: string; stopping?: boolean };
type Props = {
  onBeforeStart: () => boolean;
  request: () => Omit<MeetingCaptureCreate, "sample_rate">;
  onBusyChange: (busy: boolean) => void;
  onComplete: (meeting: Meeting) => void;
};
const IDLE_PROGRESS: MeetingCaptureProgress = {
  elapsedSeconds: 0, bufferedBytes: 0, levels: [0, 0], silentSeconds: [0, 0],
  microphoneSilent: false, systemSilent: false, echo: false, microphoneLost: false,
};

/** Records this computer's microphone and the Teams audio it plays, streaming both while the meeting runs (PRD 037). */
export function MeetingCaptureRecorder({ onBeforeStart, request, onBusyChange, onComplete }: Props) {
  const { t } = useIntl();
  const [phase, setPhase] = useState<Phase>("idle");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [device, setDevice] = useState("");
  const [informed, setInformed] = useState(false);
  const [muted, setMuted] = useState(false);
  const [progress, setProgress] = useState<MeetingCaptureProgress>(IDLE_PROGRESS);
  const [upload, setUpload] = useState<CaptureUploadState | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const active = useRef<Session | null>(null);
  const busyChange = useRef(onBusyChange);
  useEffect(() => { busyChange.current = onBusyChange; }, [onBusyChange]);
  const support = meetingCaptureSupportError();

  useEffect(() => {
    let present = true;
    const refresh = () => { void listMicrophoneDevices().then((items) => { if (present) setDevices(items); }).catch(() => {}); };
    refresh(); navigator.mediaDevices?.addEventListener?.("devicechange", refresh);
    return () => {
      present = false;
      navigator.mediaDevices?.removeEventListener?.("devicechange", refresh);
      // Leaving the page ends local capture; what reached the server can still be processed.
      const session = active.current; active.current = null;
      if (session) void session.capture.cancel().catch(() => {});
    };
  }, []);

  function stopWithError(session: Session, key: string) {
    if (active.current !== session) return;
    active.current = null;
    void session.capture.cancel().catch(() => {});
    setError(key); setPhase(session.meetingId ? "failed" : "idle"); busyChange.current(false);
  }

  function start() {
    if (active.current || support || !informed || !onBeforeStart()) return;
    setError(null); setNotice(null); setProgress(IDLE_PROGRESS); setUpload(null); setMuted(false); setMeetingId(null);
    let resolveMeeting!: (id: string) => void;
    let rejectMeeting!: (reason: unknown) => void;
    const meeting = new Promise<string>((resolve, reject) => { resolveMeeting = resolve; rejectMeeting = reject; });
    void meeting.catch(() => {});
    const uploader = new CaptureUploader({ send: captureTransport(meeting), onState: (state) => { if (active.current === session) setUpload(state); } });
    const session: Session = {
      uploader,
      capture: createMeetingCapture({
        deviceId: device || undefined,
        onProgress: (value) => { if (active.current === session) setProgress(value); },
        onPart: (part) => { if (active.current === session) uploader.add(part); },
        onError: (failure) => stopWithError(session, `capture.error.${failure.code}`),
        onShareEnded: () => { if (active.current === session) { setNotice("capture.shareEnded"); void finish(session); } },
        onLimit: () => { if (active.current === session) { setNotice("capture.limitReached"); void finish(session); } },
      }),
    };
    active.current = session;
    setPhase("requesting"); onBusyChange(true);
    // The screen picker needs this click's activation, so capture starts before any network call.
    const started = session.capture.start();
    void (async () => {
      try { await started; }
      catch (failure) {
        rejectMeeting(failure);
        stopWithError(session, `capture.error.${failure instanceof MeetingCaptureError ? failure.code : "capture_failed"}`);
        return;
      }
      try {
        const created = await MeetingService.createCapture({ ...request(), sample_rate: session.capture.sampleRate }, crypto.randomUUID());
        if (active.current !== session) { void MeetingService.cancel(created.public_id).catch(() => {}); return; }
        session.meetingId = created.public_id; setMeetingId(created.public_id);
        resolveMeeting(created.public_id);
        setPhase("recording");
      } catch (failure) {
        rejectMeeting(failure);
        stopWithError(session, meetingErrorKey(failure));
      }
    })();
  }

  async function finish(session = active.current) {
    if (!session || active.current !== session || session.stopping || !session.meetingId) return;
    session.stopping = true;
    setPhase("finishing");
    let recorded;
    try { recorded = await session.capture.stop(); }
    catch (failure) {
      stopWithError(session, `capture.error.${failure instanceof MeetingCaptureError ? failure.code : "capture_failed"}`);
      return;
    }
    try {
      const sent = await session.uploader.drain(recorded.file);
      const meeting = await MeetingService.completeCapture(session.meetingId, { frames: sent.frameCount, chain_sha256: sent.chainSha256 });
      await recorded.dispose();
      if (active.current !== session) return;
      active.current = null; setPhase("idle"); onBusyChange(false); onComplete(meeting);
    } catch {
      await recorded.dispose().catch(() => {});
      stopWithError(session, "capture.error.upload_failed");
    }
  }

  function toggleMicrophone(value: boolean) {
    setMuted(value);
    active.current?.capture.setMicrophoneMuted(value);
  }

  const recording = phase === "recording";
  const warnings = recording ? [
    progress.microphoneLost && "capture.warning.microphoneLost",
    progress.systemSilent && "capture.warning.systemSilent",
    !muted && !progress.microphoneLost && progress.microphoneSilent && "capture.warning.microphoneSilent",
    progress.echo && "capture.warning.echo",
  ].filter((value): value is string => Boolean(value)) : [];
  return <section className={`microphone-recorder${recording ? " microphone-recording" : ""}`} aria-label={t("capture.title")}
    data-capture-state={phase} data-capture-seconds={progress.elapsedSeconds}>
    <ul className="field-hint capture-guidance">
      <li>{t("capture.howTo")}</li>
      <li>{t("capture.headset")}</li>
      <li>{t("capture.teamsMute")}</li>
    </ul>
    <div className="form-field"><label htmlFor="capture-microphone">{t("microphone.device")}</label>
      <select id="capture-microphone" value={device} disabled={phase !== "idle" || Boolean(support)} onChange={(event) => setDevice(event.target.value)}>
        <option value="">{t("microphone.defaultDevice")}</option>
        {devices.filter((item) => item.deviceId && item.deviceId !== "default").map((item, index) => <option key={item.deviceId} value={item.deviceId}>{item.label || t("microphone.deviceNumber", { number: index + 1 })}</option>)}
      </select></div>
    <label className="checkbox-label"><input type="checkbox" checked={informed} disabled={phase !== "idle"} aria-describedby="capture-consent-hint"
      onChange={(event) => setInformed(event.target.checked)} />{t("capture.consent")}</label>
    <p id="capture-consent-hint" className="field-hint">{t("capture.consentHint")}</p>
    <div className="microphone-display">
      <span className="microphone-symbol"><Icon name="audio" size={28} /></span>
      <div><p className="microphone-state" role="status">{t(`capture.phase.${phase}`)}</p>
        <output className="microphone-timer" aria-label={t("microphone.duration")} aria-live="off">{recordingTime(progress.elapsedSeconds)}</output></div>
      <div className="capture-levels">
        <label>{t("capture.microphoneLevel")}<meter className="microphone-level" min="0" max="1" value={recording ? Math.min(1, progress.levels[0] * 4) : 0} /></label>
        <label>{t("capture.systemLevel")}<meter className="microphone-level" min="0" max="1" value={recording ? Math.min(1, progress.levels[1] * 4) : 0} /></label>
      </div>
    </div>
    {recording && <label className="checkbox-label"><input type="checkbox" checked={muted} onChange={(event) => toggleMicrophone(event.target.checked)} />{t("capture.microphoneMute")}</label>}
    {warnings.length > 0 && <ul className="notice" role="status">{warnings.map((key) => <li key={key}>{t(key)}</li>)}</ul>}
    {recording && upload?.waitingForFile && <p className="notice" role="status">{t("capture.uploadWaitingForFile")}</p>}
    {recording && upload?.retrying && !upload.waitingForFile && <p className="notice" role="status">{t("capture.uploadRetrying")}</p>}
    {notice && <p className="notice" role="status">{t(notice)}</p>}
    {(error || support) && <p className="error-message" role="alert">{t(error ?? `capture.error.${support}`)}</p>}
    {phase === "failed" && meetingId && <p className="notice"><Link to={`/meetings/${meetingId}`}>{t("capture.openMeeting")}</Link></p>}
    <div className="action-row">
      {(phase === "idle" || phase === "failed") && <button type="button" disabled={Boolean(support) || !informed} onClick={start}><Icon name="microphone" size={18} />{t("capture.start")}</button>}
      {recording && <button type="button" onClick={() => void finish()}><Icon name="stop" size={16} />{t("capture.finish")}</button>}
    </div>
  </section>;
}
