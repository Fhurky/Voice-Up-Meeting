import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useIntl } from "@/contexts/IntlContext";
import { meetingErrorKey, validateMeetingFile } from "@/lib/meetingErrors";
import { uploadMeeting, type UploadProgress } from "@/services/meetingUpload";
import type { Meeting } from "@/services/meetings";

export function MeetingSourceUpload({ meeting, initialFile, onComplete }: { meeting: Meeting; initialFile: File | null; onComplete: (meeting: Meeting) => void }) {
  const { t, locale } = useIntl();
  const [file, setFile] = useState<File | null>(initialFile);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const activeMeeting = useRef(meeting);
  const completed = useRef(onComplete);
  useEffect(() => { activeMeeting.current = meeting; completed.current = onComplete; }, [meeting, onComplete]);
  useEffect(() => () => { controller.current?.abort(); controller.current = null; }, []);

  const start = useCallback(async (source: File) => {
    if (controller.current) return;
    const invalid = validateMeetingFile(source);
    if (invalid) { setError(invalid); return; }
    const active = new AbortController(); controller.current = active;
    setBusy(true); setError(null);
    try {
      const result = await uploadMeeting(activeMeeting.current, source, (value) => { if (!active.signal.aborted) setProgress(value); }, active.signal);
      if (!active.signal.aborted) completed.current(result);
    } catch (failure) { if (!active.signal.aborted) setError(meetingErrorKey(failure)); }
    finally { if (controller.current === active) { controller.current = null; setBusy(false); } }
  }, []);
  // Keep a source File reference only; audio bytes are read by the bounded uploader.
  useEffect(() => {
    if (!initialFile) return;
    const timer = setTimeout(() => void start(initialFile), 0);
    return () => clearTimeout(timer);
  }, [initialFile, start]);
  function pause() { controller.current?.abort(); controller.current = null; setBusy(false); }
  function submit(event: FormEvent) { event.preventDefault(); if (file) void start(file); }
  const uploaded = progress?.uploadedBytes ?? meeting.uploaded_bytes;
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  return <section className="panel">
    <h2>{t("meeting.resume")}</h2>
    {!initialFile && <p className="muted">{t("meeting.resumeHint")}</p>}
    <form className="audio-form" onSubmit={submit} aria-label={t("meeting.uploadForm")}>
      <label htmlFor="meeting-source">{t("meeting.file")}</label>
      <input id="meeting-source" type="file" accept=".wav,.flac,audio/wav,audio/flac" disabled={busy} onChange={(event) => { setFile(event.target.files?.[0] ?? null); setError(null); }} />
      {file && <p className="field-hint">{file.name}</p>}
      <p className="field-hint">{t("meeting.limits")}</p>
      <label htmlFor="meeting-upload-progress">{t("meeting.uploadProgress", { uploaded: number.format(uploaded / 1024 ** 2), total: number.format(meeting.size_bytes / 1024 ** 2) })}</label>
      <progress id="meeting-upload-progress" value={uploaded} max={meeting.size_bytes} />
      {busy && progress && <p role="status">{t(`meeting.upload.${progress.phase}`)}</p>}
      {error && <p className="error-message" role="alert">{t(error)}</p>}
      <div className="action-row">{busy ? <button type="button" className="button-secondary" onClick={pause}>{t("meeting.pauseUpload")}</button> : <button type="submit" disabled={!file}>{t("meeting.resume")}</button>}</div>
    </form>
  </section>;
}
