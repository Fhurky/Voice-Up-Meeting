import { useContext, useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { MeetingService, type MeetingCreate } from "@/services/meetings";
import { meetingErrorKey, validateMeetingFile } from "@/lib/meetingErrors";
import { MeetingUploadContext } from "@/contexts/meetingUploadSelection";

export function MeetingUploadForm() {
  const { t } = useIntl();
  const { hasPermission } = useAuth();
  const navigate = useNavigate();
  const selection = useContext(MeetingUploadContext);
  if (!selection) throw new Error("MeetingUploadContext is required");
  const { setSelection } = selection;
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState<NonNullable<MeetingCreate["language"]>>("tr");
  const [participants, setParticipants] = useState("");
  const [speakers, setSpeakers] = useState("");
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const attempt = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (controller.current || !file) return;
    const invalidFile = validateMeetingFile(file);
    if (invalidFile) { setError(invalidFile); return; }
    const normalizedTitle = title.trim().replace(/\s+/g, " ");
    const validCount = (value: string) => !value || (/^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 1000);
    if (!normalizedTitle || normalizedTitle.length > 120 || !validCount(participants) || !validCount(speakers)) { setError("meeting.error.validation_error"); return; }
    if (participants && speakers && Number(speakers) > Number(participants)) { setError("meeting.error.counts"); return; }
    const request: MeetingCreate = { title: normalizedTitle, format: /\.flac$/i.test(file.name) ? "FLAC" : "WAV", size_bytes: file.size,
      language, participant_count: participants ? Number(participants) : null, expected_speakers: speakers ? Number(speakers) : null,
      auto_enroll: hasPermission("speaker_profiles:write") && remember };
    const fingerprint = JSON.stringify([request, file.name, file.lastModified]);
    if (attempt.current?.fingerprint !== fingerprint) attempt.current = { fingerprint, key: crypto.randomUUID() };
    const active = new AbortController(); controller.current = active;
    setBusy(true); setError(null);
    try {
      const result = await MeetingService.create(request, attempt.current.key, active.signal);
      if (!active.signal.aborted) {
        setSelection({ meetingId: result.public_id, file });
        void navigate(`/meetings/${result.public_id}`);
      }
    } catch (failure) { if (!active.signal.aborted) setError(meetingErrorKey(failure)); }
    finally { controller.current = null; if (!active.signal.aborted) setBusy(false); }
  }

  return <section className="panel">
    <h2>{t("meeting.new")}</h2><p className="muted">{t("meeting.uploadHint")}</p>
    <form className="audio-form" aria-label={t("meeting.uploadForm")} onSubmit={(event) => void submit(event)}>
      <label htmlFor="meeting-title">{t("meeting.titleLabel")}</label>
      <input id="meeting-title" value={title} maxLength={120} required disabled={busy} onChange={(event) => setTitle(event.target.value)} />
      <label htmlFor="meeting-file">{t("meeting.file")}</label>
      <input id="meeting-file" type="file" accept=".wav,.flac,audio/wav,audio/flac" required disabled={busy} aria-describedby="meeting-limits" onChange={(event) => { setFile(event.target.files?.[0] ?? null); attempt.current = null; setError(null); }} />
      <p id="meeting-limits" className="field-hint">{t("meeting.limits")}</p>
      <label htmlFor="meeting-language">{t("meeting.language")}</label>
      <select id="meeting-language" value={language} disabled={busy} onChange={(event) => setLanguage(event.target.value === "en" ? "en" : event.target.value === "auto" ? "auto" : "tr")}>
        <option value="tr">{t("meeting.language.tr")}</option><option value="en">{t("meeting.language.en")}</option><option value="auto">{t("meeting.language.auto")}</option>
      </select>
      <label htmlFor="meeting-participants">{t("meeting.participants")}</label>
      <input id="meeting-participants" type="number" min="1" max="1000" step="1" value={participants} disabled={busy} aria-describedby="meeting-count-hint" onChange={(event) => setParticipants(event.target.value)} />
      <label htmlFor="meeting-speakers">{t("meeting.expectedSpeakers")}</label>
      <input id="meeting-speakers" type="number" min="1" max="1000" step="1" value={speakers} disabled={busy} aria-describedby="meeting-count-hint" onChange={(event) => setSpeakers(event.target.value)} />
      <p id="meeting-count-hint" className="field-hint">{t("meeting.countHint")}</p>
      {hasPermission("speaker_profiles:write") ? <label className="checkbox-label"><input type="checkbox" checked={remember} disabled={busy} onChange={(event) => setRemember(event.target.checked)} />{t("meeting.remember")}</label> : <p className="field-hint">{t("meeting.memoryPermission")}</p>}
      <p className="field-hint">{t("meeting.memoryHint")}</p>
      {error && <p className="error-message" role="alert">{t(error)}</p>}
      <button type="submit" disabled={busy || !file || !title.trim()}>{t(busy ? "meeting.creating" : "meeting.start")}</button>
    </form>
  </section>;
}
