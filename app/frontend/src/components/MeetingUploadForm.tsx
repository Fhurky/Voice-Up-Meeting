import { useContext, useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { MeetingService, type MeetingCreate } from "@/services/meetings";
import { extractMeetingAudio, isMediaContainer } from "@/lib/mediaAudio";
import { meetingErrorKey, validateMeetingFile } from "@/lib/meetingErrors";
import { MeetingUploadContext } from "@/contexts/meetingUploadSelection";
import { Icon } from "@/components/ui/Icon";
import { MeetingMicrophoneRecorder } from "@/components/MeetingMicrophoneRecorder";
import { MeetingParticipantPicker } from "@/components/MeetingParticipantPicker";
import { uploadMeeting, type UploadProgress } from "@/services/meetingUpload";

export function MeetingUploadForm({ initialSource = "file", onClose }: { initialSource?: "file" | "microphone"; onClose?: () => void }) {
  const { t } = useIntl();
  const { hasPermission } = useAuth();
  const navigate = useNavigate();
  const selection = useContext(MeetingUploadContext);
  if (!selection) throw new Error("MeetingUploadContext is required");
  const { setSelection } = selection;
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState<"file" | "microphone">(initialSource);
  const [language, setLanguage] = useState<NonNullable<MeetingCreate["language"]>>("tr");
  const [participants, setParticipants] = useState("");
  const [speakers, setSpeakers] = useState("");
  const [subject, setSubject] = useState("");
  const [questions, setQuestions] = useState<{ id: number; text: string }[]>([]);
  const [focusedQuestion, setFocusedQuestion] = useState<number | null>(null);
  const [removedQuestions, setRemovedQuestions] = useState(0);
  const nextQuestion = useRef(0);
  const addQuestion = useRef<HTMLButtonElement>(null);
  const contextOptions = useRef<HTMLDetailsElement>(null);
  const [roster, setRoster] = useState<string[]>([]);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [cpuMode, setCpuMode] = useState(false);
  const extracted = useRef<{ source: File; audio: File } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const attempt = useRef<{ fingerprint: string; key: string } | null>(null);
  const recordingMeeting = useRef<string | null>(null);
  const countOptions = useRef<HTMLDetailsElement>(null);
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    const reading = new AbortController();
    MeetingService.processingMode(reading.signal).then((mode) => { if (!reading.signal.aborted) setCpuMode(mode.processing_device === "cpu"); }).catch(() => {});
    return () => reading.abort();
  }, []);
  // The add button may have been disabled at the limit until this removal rendered.
  useEffect(() => { if (removedQuestions) addQuestion.current?.focus(); }, [removedQuestions]);

  const normalizeText = (value: string) => value.trim().replace(/\s+/g, " ");
  const enteredQuestions = () => questions.map((question) => normalizeText(question.text)).filter(Boolean);

  function validateOptions() {
    const normalizedTitle = title.trim().replace(/\s+/g, " ");
    const validCount = (value: string) => !value || (/^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 1000);
    if (!normalizedTitle || normalizedTitle.length > 120 || !validCount(participants) || !validCount(speakers)) { if (countOptions.current) countOptions.current.open = true; setError("meeting.error.validation_error"); form.current?.reportValidity(); return false; }
    if (participants && speakers && Number(speakers) > Number(participants)) { if (countOptions.current) countOptions.current.open = true; setError("meeting.error.counts"); return false; }
    if (participants && roster.length > Number(participants)) { if (countOptions.current) countOptions.current.open = true; setError("meeting.error.rosterCount"); return false; }
    const entered = enteredQuestions();
    if (new Set(entered.map((value) => value.toLocaleLowerCase())).size !== entered.length) { if (contextOptions.current) contextOptions.current.open = true; setError("meeting.error.duplicateQuestion"); return false; }
    setError(null); return true;
  }
  async function create(sourceFile: File, signal: AbortSignal) {
    const request: MeetingCreate = { title: title.trim().replace(/\s+/g, " "), format: /\.flac$/i.test(sourceFile.name) ? "FLAC" : "WAV", size_bytes: sourceFile.size,
      language, participant_count: participants ? Number(participants) : null, expected_speakers: speakers ? Number(speakers) : null,
      auto_enroll: hasPermission("speaker_profiles:write") && remember, participant_profile_ids: roster,
      subject: normalizeText(subject) || null, questions: enteredQuestions() };
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
      let upload = file;
      if (isMediaContainer(file)) {
        // A retry after a lost response keeps the same audio instead of decoding the video again.
        if (extracted.current?.source !== file) {
          setExtracting(true);
          extracted.current = { source: file, audio: await extractMeetingAudio(file) };
        }
        upload = extracted.current.audio;
      }
      setExtracting(false);
      const result = await create(upload, active.signal);
      if (!active.signal.aborted) {
        setSelection({ meetingId: result.public_id, file: upload });
        void navigate(`/meetings/${result.public_id}`);
      }
    } catch (failure) { if (!active.signal.aborted) setError(meetingErrorKey(failure)); }
    finally { controller.current = null; setExtracting(false); if (!active.signal.aborted) setBusy(false); }
  }

  return <section className="panel meeting-upload-panel" aria-labelledby="meeting-upload-heading">
    <div className="section-heading"><h2 id="meeting-upload-heading">{t("meeting.new")}</h2>
      {onClose && <button type="button" className="button-quiet" disabled={busy} onClick={onClose}>{t("common.cancel")}</button>}</div>
    {cpuMode && <p className="notice" role="status">{t("meeting.cpuMode")}</p>}
    <div className="recording-source-switch" role="group" aria-label={t("microphone.source")}>
      <button type="button" className="button-secondary" aria-pressed={source === "file"} disabled={busy} onClick={() => { setSource("file"); setError(null); }}><Icon name="upload" size={18} />{t("microphone.fileSource")}</button>
      <button type="button" className="button-secondary" aria-pressed={source === "microphone"} disabled={busy} onClick={() => { setSource("microphone"); setError(null); }}><Icon name="microphone" size={18} />{t("microphone.microphoneSource")}</button>
    </div>
    <form ref={form} className="audio-form" aria-label={t("meeting.uploadForm")} onSubmit={(event) => void submit(event)}>
      {source === "file" && <><div className="upload-surface">
        <label htmlFor="meeting-file">{t("meeting.file")}</label>
        <input id="meeting-file" type="file" accept=".wav,.flac,.mp4,.m4a,audio/wav,audio/flac,video/mp4,audio/mp4" required disabled={busy} aria-describedby="meeting-limits" onChange={(event) => { setFile(event.target.files?.[0] ?? null); attempt.current = null; setError(null); }} />
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
      <details ref={contextOptions} className="form-options" onInvalid={(event) => { event.currentTarget.open = true; }}>
        <summary><span>{t("meeting.context.title")}</span><span>{t("meeting.context.summary")}</span></summary>
        <div className="form-field"><label htmlFor="meeting-subject">{t("meeting.context.subject")}</label>
          <textarea id="meeting-subject" rows={2} maxLength={500} value={subject} disabled={busy} onChange={(event) => setSubject(event.target.value)} /></div>
        <fieldset className="question-list" disabled={busy}>
          <legend>{t("meeting.context.questions")}</legend>
          {questions.map((question, index) => <div className="question-row" key={question.id}>
            <input aria-label={t("meeting.context.question", { number: index + 1 })} maxLength={500} value={question.text} autoFocus={question.id === focusedQuestion}
              onChange={(event) => { const text = event.target.value; setQuestions((rows) => rows.map((row) => row.id === question.id ? { ...row, text } : row)); setError(null); }} />
            <button type="button" className="button-quiet" aria-label={t("meeting.context.removeQuestion", { number: index + 1 })}
              onClick={() => { setQuestions((rows) => rows.filter((row) => row.id !== question.id)); setError(null); setFocusedQuestion(null); setRemovedQuestions((count) => count + 1); }}>{t("meeting.context.remove")}</button>
          </div>)}
          <button ref={addQuestion} type="button" className="button-secondary" disabled={questions.length >= 20}
            onClick={() => { const id = nextQuestion.current++; setFocusedQuestion(id); setQuestions((rows) => [...rows, { id, text: "" }]); }}>{t("meeting.context.addQuestion")}</button>
        </fieldset>
        <p className="field-hint">{t("meeting.context.hint")}</p>
      </details>
      <details ref={countOptions} className="form-options" onInvalid={(event) => { event.currentTarget.open = true; }}>
        <summary><span>{t("meeting.advancedOptions")}</span><span>{t("meeting.advancedSummary")}</span></summary>
        {hasPermission("speaker_profiles:read") ? <MeetingParticipantPicker selected={roster} disabled={busy} onChange={(value) => { setRoster(value); setError(null); }} /> : <p className="field-hint">{t("meeting.roster.permission")}</p>}
        <div className="form-grid">
          <div className="form-field"><label htmlFor="meeting-participants">{t("meeting.participants")}</label>
            <input id="meeting-participants" type="number" min="1" max="1000" step="1" value={participants} disabled={busy} aria-describedby="meeting-count-hint" onChange={(event) => setParticipants(event.target.value)} /></div>
          <div className="form-field"><label htmlFor="meeting-speakers">{t("meeting.expectedSpeakers")}</label>
            <input id="meeting-speakers" type="number" min="1" max="1000" step="1" value={speakers} disabled={busy} aria-describedby="meeting-count-hint" onChange={(event) => setSpeakers(event.target.value)} /></div>
        </div>
        <p id="meeting-count-hint" className="field-hint">{t("meeting.countHint")}</p>
        <div className="memory-option">
          {hasPermission("speaker_profiles:write") ? <label className="checkbox-label"><input type="checkbox" checked={remember} disabled={busy} aria-describedby="meeting-memory-hint" onChange={(event) => setRemember(event.target.checked)} />{t("meeting.remember")}</label> : <p className="field-hint">{t("meeting.memoryPermission")}</p>}
          <p id="meeting-memory-hint" className="field-hint">{t("meeting.memoryHint")}</p>
        </div>
      </details>
      {extracting && <p className="field-hint" role="status">{t("meeting.extractingAudio")}</p>}
      {error && <p className="error-message" role="alert">{t(error)}</p>}
      {source === "file" ? <button type="submit" disabled={busy || !file || !title.trim()}><Icon name="upload" size={18} />{t(busy ? "meeting.creating" : "meeting.start")}</button> :
        <MeetingMicrophoneRecorder onBeforeStart={validateOptions} onBusyChange={setBusy} onAnalyze={analyzeRecording} onAbandon={abandonRecording} onComplete={(result) => { recordingMeeting.current = null; void navigate(`/meetings/${result.public_id}`); }} />}
    </form>
  </section>;
}
