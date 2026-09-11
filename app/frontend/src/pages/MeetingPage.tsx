import { useContext, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { MeetingResults } from "@/components/MeetingResults";
import { MeetingSourceUpload } from "@/components/MeetingSourceUpload";
import { ApiError } from "@/lib/apiClient";
import { meetingErrorKey, recordingTime } from "@/lib/meetingErrors";
import { MeetingService, type Meeting } from "@/services/meetings";
import { MeetingUploadContext } from "@/contexts/meetingUploadSelection";

function MeetingDetail({ publicId }: { publicId: string }) {
  const { t, locale } = useIntl();
  const { hasPermission } = useAuth();
  const navigate = useNavigate();
  const selection = useContext(MeetingUploadContext);
  const [initialFile, setInitialFile] = useState<File | null>(() => selection?.selection?.meetingId === publicId ? selection.selection.file : null);
  const clearSelection = selection?.setSelection;
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [revision, setRevision] = useState(0);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [confirmation, setConfirmation] = useState<"cancel" | "delete" | null>(null);
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const mutation = useRef<AbortController | null>(null);
  useEffect(() => () => mutation.current?.abort(), []);
  useEffect(() => { if (confirmation) dialog.current?.focus(); }, [confirmation]);
  useEffect(() => () => clearSelection?.((current) => current?.meetingId === publicId ? null : current), [publicId, clearSelection]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let failures = 0;
    async function poll() {
      try {
        const result = await MeetingService.get(publicId, controller.signal);
        if (controller.signal.aborted) return;
        setMeeting(result); setRevision((value) => value + 1); setError(null); setPaused(false); failures = 0;
        if (["uploading", "queued", "running", "finalizing"].includes(result.status)) timer = setTimeout(() => void poll(), 5000);
      } catch (failure) {
        if (controller.signal.aborted) return;
        setError(meetingErrorKey(failure)); failures += 1;
        if (failures >= 3 || (failure instanceof ApiError && [401, 403, 404, 410].includes(failure.status))) setPaused(true);
        else timer = setTimeout(() => void poll(), 5000 * failures);
      }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [publicId, reload]);

  async function action(kind: "cancel" | "delete" | "retry") {
    if (mutation.current) return;
    const controller = new AbortController(); mutation.current = controller; setBusy(true); setError(null);
    try {
      if (kind === "delete") {
        await MeetingService.remove(publicId, controller.signal);
        if (!controller.signal.aborted) void navigate("/meetings", { replace: true });
      } else {
        const updated = await MeetingService[kind](publicId, controller.signal);
        if (!controller.signal.aborted) { setMeeting(updated); setConfirmation(null); setReload((value) => value + 1); trigger.current?.focus(); }
      }
    } catch (failure) { if (!controller.signal.aborted) setError(meetingErrorKey(failure)); }
    finally { mutation.current = null; if (!controller.signal.aborted) setBusy(false); }
  }
  const run = hasPermission("meeting_analysis:run");
  const number = new Intl.NumberFormat(locale);
  return <SpeakerLayout titleKey="meeting.detailTitle">
    <p><Link className="text-link" to="/meetings">{t("meeting.back")}</Link></p>
    <div className="section-heading"><h2 className="meeting-name">{meeting?.title}</h2><button className="button-secondary" onClick={() => setReload((value) => value + 1)}>{t("common.refresh")}</button></div>
    {error && <p className="error-message" role="alert">{t(error)}</p>}
    {paused && <p className="notice">{t("meeting.pollPaused")}</p>}
    {!meeting && !error && <p role="status">{t("common.loading")}</p>}
    {meeting && <>
      <section className="panel job-status" aria-label={t("meeting.detailTitle")}>
        <p role="status"><span className={`status-badge status-${meeting.status}`} data-meeting-status={meeting.status}>{t(`meeting.status.${meeting.status}`)}</span></p>
        {(["queued", "running", "finalizing"] as string[]).includes(meeting.status) && <p>{t(`meeting.statusHint.${meeting.status}`)}</p>}
        {meeting.error_code && <p className="error-message" role="alert">{t(meetingErrorKey(new ApiError(503, "Meeting analysis failed", meeting.error_code)))}</p>}
        <dl className="compact-details">
          <div><dt>{t("meeting.duration")}</dt><dd>{meeting.duration_seconds == null ? t("meeting.unset") : recordingTime(meeting.duration_seconds)}</dd></div>
          <div><dt>{t("meeting.processed")}</dt><dd>{recordingTime(meeting.processed_seconds)}</dd></div>
          <div><dt>{t("meeting.observed")}</dt><dd>{number.format(meeting.observed_speakers)}</dd></div>
        </dl>
        <p className="field-hint">{t("meeting.countSummary", { participants: meeting.participant_count == null ? t("meeting.unset") : number.format(meeting.participant_count), speakers: meeting.expected_speakers == null ? t("meeting.unset") : number.format(meeting.expected_speakers) })}</p>
        {meeting.count_mismatch && <p className="notice" role="alert">{t("meeting.countMismatch")}</p>}
        {!meeting.source_available && meeting.status !== "uploading" && <p className="field-hint">{t("meeting.sourceUnavailable")}</p>}
        {run && <div className="action-row">
          {meeting.status === "failed" && meeting.source_available && (!meeting.auto_enroll || hasPermission("speaker_profiles:write")) && <button disabled={busy} onClick={() => void action("retry")}>{t("common.retry")}</button>}
          {!["succeeded", "cancelled"].includes(meeting.status) && <button disabled={busy} className="button-secondary" onClick={(event) => { trigger.current = event.currentTarget; setConfirmation("cancel"); }}>{t("meeting.cancel")}</button>}
          <button disabled={busy} className="button-danger-quiet" onClick={(event) => { trigger.current = event.currentTarget; setConfirmation("delete"); }}>{t("common.delete")}</button>
        </div>}
        {confirmation && <div ref={dialog} className="inline-action danger-panel" role="alertdialog" tabIndex={-1} aria-labelledby="meeting-confirm-title" aria-describedby="meeting-confirm-hint" onKeyDown={(event) => {
          if (event.key === "Escape" && !busy) { setConfirmation(null); trigger.current?.focus(); }
        }}>
          <h3 id="meeting-confirm-title">{t(`meeting.${confirmation}Title`)}</h3><p id="meeting-confirm-hint">{t(`meeting.${confirmation}Hint`)}</p>
          <div className="action-row"><button disabled={busy} className="button-danger" onClick={() => void action(confirmation)}>{t(`meeting.${confirmation}Confirm`)}</button><button disabled={busy} className="button-secondary" onClick={() => { setConfirmation(null); trigger.current?.focus(); }}>{t("common.cancel")}</button></div>
        </div>}
      </section>
      {meeting.status === "uploading" && run && <MeetingSourceUpload meeting={meeting} initialFile={initialFile} onComplete={(updated) => { setInitialFile(null); clearSelection?.(null); setMeeting(updated); setReload((value) => value + 1); }} />}
      {meeting.status !== "uploading" && <MeetingResults key={meeting.public_id} meeting={meeting} revision={revision} />}
      <p className="field-hint">{t("meeting.retention")}</p>
    </>}
  </SpeakerLayout>;
}

export default function MeetingPage() {
  const { publicId = "" } = useParams();
  return <MeetingDetail key={publicId} publicId={publicId} />;
}
