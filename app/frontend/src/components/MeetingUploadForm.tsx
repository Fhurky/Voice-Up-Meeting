import { useContext, useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { MeetingService, type MeetingCreate } from "@/services/meetings";
import { meetingErrorKey, validateMeetingFile } from "@/lib/meetingErrors";
import { MeetingUploadContext } from "@/contexts/meetingUploadSelection";
import { Icon } from "@/components/ui/Icon";
import { MeetingMicrophoneRecorder } from "@/components/MeetingMicrophoneRecorder";
import { uploadMeeting, type UploadProgress } from "@/services/meetingUpload";

export function MeetingUploadForm() {
  const { t } = useIntl();
  const { hasPermission } = useAuth();
  const navigate = useNavigate();
  const selection = useContext(MeetingUploadContext);
  if (!selection) throw new Error("MeetingUploadContext is required");
  const { setSelection } = selection;
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState<"file" | "microphone">("file");
  const [language, setLanguage] = useState<NonNullable<MeetingCreate["language"]>>("tr");
  const [participants, setParticipants] = useState("");
  const [speakers, setSpeakers] = useState("");
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const attempt = useRef<{ fingerprint: string; key: string } | null>(null);
  const recordingMeeting = useRef<string | null>(null);
  const countOptions = useRef<HTMLDetailsElement>(null);
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => () => controller.current?.abort(), []);

  function validateOptions() {
    const normalizedTitle = title.trim().replace(/\s+/g, " ");
    const validCount = (value: string) => !value || (/^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 1000);
    if (!normalizedTitle || normalizedTitle.length > 120 || !validCount(participants) || !validCount(speakers)) { if (countOptions.current) countOptions.current.open = true; setError("meeting.error.validation_error"); form.current?.reportValidity(); return false; }
    if (participants && speakers && Number(speakers) > Number(participants)) { if (countOptions.current) countOptions.current.open = true; setError("meeting.error.counts"); return false; }
    setError(null); return true;
  }
  async function create(sourceFile: File, signal: AbortSignal) {
    const request: MeetingCreate = { title: title.trim().replace(/\s+/g, " "), format: /\.flac$/i.test(sourceFile.name) ? "FLAC" : "WAV", size_bytes: sourceFile.size,
      language, participant_count: participants ? Number(participants) : null, expected_speakers: speakers ? Number(speakers) : null,
      auto_enroll: hasPermission("speaker_profiles:write") && remember };
    const fingerprint = JSON.stringify([request, sourceFile.name, sourceFile.lastModified]);
    if (attempt.current?.fingerprint !== fingerprint) attempt.current = { fingerprint, key: crypto.randomUUID() };
    return MeetingService.create(request, attempt.current.key, signal);
  }
  async function analyzeRecording(sourceFile: File, signal: AbortSignal, progress: (value: UploadProgress) => void) {
    // Keep the bounded create response so cancellation can release a committed upload slot.
    const result = await create(sourceFile, new AbortController().signal);
    if (signal.aborted) {
      void MeetingService.cancel(result.public_id).catch(() => {});
      throw new DOMException("Aborted", "AbortError");
    }
    recordingMeeting.current = result.public_id;
    // A lost completion response may return the already queued meeting on retry.
    if (result.status !== "uploading") return result;
    return uploadMeeting(result, sourceFile, progress, signal);
  }
  function abandonRecording() {
    const publicId = recordingMeeting.current; recordingMeeting.current = null;
    if (publicId) void MeetingService.cancel(publicId).catch(() => {});
    attempt.current = null;
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (source !== "file" || controller.current || !file) return;
    const invalidFile = validateMeetingFile(file);
    if (invalidFile) { setError(invalidFile); return; }
    if (!validateOptions()) return;
    const active = new AbortController(); controller.current = active;
    setBusy(true); setError(null);
    try {
      const result = await create(file, active.signal);
      if (!active.signal.aborted) {
        setSelection({ meetingId: result.public_id, file });
        void navigate(`/meetings/${result.public_id}`);
      }
    } catch (failure) { if (!active.signal.aborted) setError(meetingErrorKey(failure)); }
    finally { controller.current = null; if (!active.signal.aborted) setBusy(false); }
  }

  return <section className="panel meeting-upload-panel">
    <p className="eyebrow">{t("meeting.uploadEyebrow")}</p>
    <h2>{t("meeting.new")}</h2><p className="muted">{t("microphone.sourceHint")}</p>
    <div className="recording-source-switch" role="group" aria-label={t("microphone.source")}>
      <button type="button" className="button-secondary" aria-pressed={source === "file"} disabled={busy} onClick={() => { setSource("file"); setError(null); }}><Icon name="upload" size={18} />{t("microphone.fileSource")}</button>
      <button type="button" className="button-secondary" aria-pressed={source === "microphone"} disabled={busy} onClick={() => { setSource("microphone"); setError(null); }}><Icon name="microphone" size={18} />{t("microphone.microphoneSource")}</button>
    </div>
    <form ref={form} className="audio-form" aria-label={t("meeting.uploadForm")} onSubmit={(event) => void submit(event)}>
      {source === "file" && <><div className="upload-surface">
        <span className="upload-surface-icon"><Icon name={file ? "file" : "upload"} size={24} /></span>
        <p className="upload-surface-title">{t("meeting.chooseFile")}</p>
        <p className="field-hint">{t("meeting.fileTypes")}</p>
        <label htmlFor="meeting-file">{t("meeting.file")}</label>
        <input id="meeting-file" type="file" accept=".wav,.flac,audio/wav,audio/flac" required disabled={busy} aria-describedby="meeting-limits" onChange={(event) => { setFile(event.target.files?.[0] ?? null); attempt.current = null; setError(null); }} />
        {file && <p className="upload-file-name" role="status">{file.name}</p>}
      </div>
      <p id="meeting-limits" className="field-hint">{t("meeting.limits")}</p></>}
      <div className="form-grid">
        <div className="form-field"><label htmlFor="meeting-title">{t("meeting.titleLabel")}</label>
          <input id="meeting-title" value={title} maxLength={120} required disabled={busy} placeholder={t("meeting.titlePlaceholder")} onChange={(event) => setTitle(event.target.value)} /></div>
        <div className="form-field"><label htmlFor="meeting-language">{t("meeting.language")}</label>
          <select id="meeting-language" value={language} disabled={busy} onChange={(event) => setLanguage(event.target.value === "en" ? "en" : event.target.value === "auto" ? "auto" : "tr")}>
            <option value="tr">{t("meeting.language.tr")}</option><option value="en">{t("meeting.language.en")}</option><option value="auto">{t("meeting.language.auto")}</option>
          </select></div>
      </div>
      <details ref={countOptions} className="form-options" onInvalid={(event) => { event.currentTarget.open = true; }}>
        <summary><span>{t("meeting.advancedOptions")}</span><span className="field-hint">{t("meeting.optional")}</span></summary>
        <div className="form-grid">
          <div className="form-field"><label htmlFor="meeting-participants">{t("meeting.participants")}</label>
            <input id="meeting-participants" type="number" min="1" max="1000" step="1" value={participants} disabled={busy} aria-describedby="meeting-count-hint" onChange={(event) => setParticipants(event.target.value)} /></div>
          <div className="form-field"><label htmlFor="meeting-speakers">{t("meeting.expectedSpeakers")}</label>
            <input id="meeting-speakers" type="number" min="1" max="1000" step="1" value={speakers} disabled={busy} aria-describedby="meeting-count-hint" onChange={(event) => setSpeakers(event.target.value)} /></div>
        </div>
        <p id="meeting-count-hint" className="field-hint">{t("meeting.countHint")}</p>
      </details>
      <div className="memory-option">
        {hasPermission("speaker_profiles:write") ? <label className="checkbox-label"><input type="checkbox" checked={remember} disabled={busy} aria-describedby="meeting-memory-hint" onChange={(event) => setRemember(event.target.checked)} />{t("meeting.remember")}</label> : <p className="field-hint">{t("meeting.memoryPermission")}</p>}
        <p id="meeting-memory-hint" className="field-hint">{t("meeting.memoryHint")}</p>
      </div>
      {error && <p className="error-message" role="alert">{t(error)}</p>}
      {source === "file" ? <button type="submit" disabled={busy || !file || !title.trim()}><Icon name="upload" size={18} />{t(busy ? "meeting.creating" : "meeting.start")}</button> :
        <MeetingMicrophoneRecorder onBeforeStart={validateOptions} onBusyChange={setBusy} onAnalyze={analyzeRecording} onAbandon={abandonRecording} onComplete={(result) => { recordingMeeting.current = null; void navigate(`/meetings/${result.public_id}`); }} />}
    </form>
  </section>;
}
