import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { MeetingPagination } from "@/components/MeetingPagination";
import { meetingErrorKey, recordingTime } from "@/lib/meetingErrors";
import { MeetingService, type Meeting, type MeetingSpeaker } from "@/services/meetings";

export function MeetingResults({ meeting, revision }: { meeting: Meeting; revision: number }) {
  const { t, locale } = useIntl();
  const { hasPermission } = useAuth();
  const [speakerPage, setSpeakerPage] = useState<Awaited<ReturnType<typeof MeetingService.speakers>> | null>(null);
  const [transcriptPage, setTranscriptPage] = useState<Awaited<ReturnType<typeof MeetingService.transcript>> | null>(null);
  const [speakerOffset, setSpeakerOffset] = useState(0);
  const [textOffset, setTextOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<MeetingSpeaker | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const mutation = useRef<AbortController | null>(null);
  const renameTrigger = useRef<HTMLButtonElement | null>(null);
  useEffect(() => () => mutation.current?.abort(), []);
  useEffect(() => { if (editing) input.current?.focus(); }, [editing]);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      MeetingService.speakers(meeting.public_id, speakerOffset, controller.signal),
      MeetingService.transcript(meeting.public_id, textOffset, controller.signal),
    ]).then(([speakers, transcript]) => {
      if (!controller.signal.aborted) { setSpeakerPage(speakers); setTranscriptPage(transcript); setError(null); }
    }).catch((failure: unknown) => { if (!controller.signal.aborted) setError(meetingErrorKey(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [meeting.public_id, revision, speakerOffset, textOffset, refresh]);

  const label = (speaker: MeetingSpeaker) => speaker.profile_name || speaker.display_name || t("meeting.speakerLabel", { number: new Intl.NumberFormat(locale).format(speaker.ordinal + 1) });
  function closeEditor() { setEditing(null); setSaveError(null); renameTrigger.current?.focus(); }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!editing || mutation.current) return;
    const normalized = name.trim().replace(/\s+/g, " ");
    if (!normalized || normalized.length > 120) { setSaveError("speaker.error.name_required"); return; }
    const controller = new AbortController(); mutation.current = controller; setSaving(true); setSaveError(null);
    try {
      await MeetingService.rename(meeting.public_id, editing.public_id, { name: normalized, version: editing.version, profile_updated_at: editing.profile_updated_at }, controller.signal);
      if (!controller.signal.aborted) { closeEditor(); setLoading(true); setRefresh((value) => value + 1); }
    } catch (failure) { if (!controller.signal.aborted) setSaveError(meetingErrorKey(failure)); }
    finally { mutation.current = null; if (!controller.signal.aborted) setSaving(false); }
  }

  return <>
    {error && <div className="error-message" role="alert"><p>{t(error)}</p><button onClick={() => { setLoading(true); setRefresh((value) => value + 1); }}>{t("common.refresh")}</button></div>}
    {loading && !speakerPage && <p role="status">{t("common.loading")}</p>}
    <div className="meeting-results">
      <section className="panel" aria-labelledby="meeting-speakers-heading" aria-busy={loading}>
        <h2 id="meeting-speakers-heading">{t("meeting.speakers")}</h2>
        {speakerPage?.items.length === 0 && <p className="empty-card">{t("meeting.speakersEmpty")}</p>}
        <ul className="profiles">{speakerPage?.items.map((speaker) => <li key={speaker.public_id} className="profile-card" data-speaker-id={speaker.public_id} data-profile-id={speaker.profile_public_id ?? ""}>
          <h3>{label(speaker)}</h3>
          <p className={`status-badge status-${speaker.decision === "profile_pending" || speaker.decision === "ambiguous" ? "queued" : "succeeded"}`}>{t(`meeting.decision.${speaker.decision}`)}</p>
          {speaker.profile_deleted && <p className="notice">{t("meeting.profileDeleted")}</p>}
          {speaker.decision === "profile_pending" && <p className="field-hint">{t("meeting.pendingHint")}</p>}
          {speaker.decision === "ambiguous" && <p className="field-hint">{t("meeting.ambiguousHint")}</p>}
          <p className="field-hint">{t("meeting.speech", { seconds: new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(speaker.speech_seconds) })}</p>
          {hasPermission("meeting_analysis:run") && (!speaker.profile_public_id || hasPermission("speaker_profiles:write")) && <button className="button-secondary" onClick={(event) => {
            renameTrigger.current = event.currentTarget; setEditing(speaker); setName(speaker.profile_name || speaker.display_name || ""); setSaveError(null);
          }}>{t("common.rename")}</button>}
        </li>)}</ul>
        {speakerPage && <MeetingPagination label={t("meeting.speakers")} offset={speakerOffset} total={speakerPage.total} limit={20} onChange={(value) => { setLoading(true); setSpeakerOffset(value); }} />}
        {editing && <form className="inline-action" aria-label={t("common.rename")} onSubmit={(event) => void save(event)}>
          <h3>{label(editing)}</h3>
          <p className="field-hint">{t(editing.profile_public_id ? "meeting.profileNameHint" : "meeting.localNameHint")}</p>
          <label htmlFor="meeting-speaker-name">{t("meeting.speakerName")}</label>
          <input ref={input} id="meeting-speaker-name" value={name} maxLength={120} required disabled={saving} onChange={(event) => setName(event.target.value)} />
          {saveError && <p role="alert" className="error-message">{t(saveError)}</p>}
          {saveError === "meeting.error.name_conflict" && <button type="button" className="button-secondary" disabled={saving} onClick={() => { closeEditor(); setLoading(true); setRefresh((value) => value + 1); }}>{t("common.refresh")}</button>}
          <div className="action-row"><button disabled={saving || !name.trim()} type="submit">{t("common.save")}</button><button className="button-secondary" disabled={saving} type="button" onClick={closeEditor}>{t("common.cancel")}</button></div>
        </form>}
      </section>
      <section className="panel" aria-labelledby="meeting-transcript-heading" aria-busy={loading}>
        <h2 id="meeting-transcript-heading">{t("meeting.transcript")}</h2>
        {transcriptPage?.provisional && <p className="notice">{t("meeting.provisional")}</p>}
        {transcriptPage?.items.length === 0 && <p className="empty-card">{t("meeting.transcriptEmpty")}</p>}
        <ol className="meeting-transcript">{transcriptPage?.items.map((turn) => <li key={turn.public_id} data-transcript-id={turn.public_id}>
          <div className="section-heading"><strong>{turn.speaker_name || (turn.speaker_ordinal != null ? t("meeting.speakerLabel", { number: new Intl.NumberFormat(locale).format(turn.speaker_ordinal + 1) }) : t("meeting.unknownSpeaker"))}</strong>
            <span className="muted meeting-timestamp">{recordingTime(turn.start_seconds)}–{recordingTime(turn.end_seconds)}</span></div>
          <p lang={turn.language}>{turn.text}</p>
          {(turn.overlap || turn.uncertain) && <div className="action-row">{turn.overlap && <span className="status-badge status-queued">{t("meeting.overlap")}</span>}{turn.uncertain && <span className="status-badge status-queued">{t("meeting.uncertain")}</span>}</div>}
        </li>)}</ol>
        {transcriptPage && <MeetingPagination label={t("meeting.transcript")} offset={textOffset} total={transcriptPage.total} limit={50} onChange={(value) => { setLoading(true); setTextOffset(value); }} />}
      </section>
    </div>
  </>;
}
