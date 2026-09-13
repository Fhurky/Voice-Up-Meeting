import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { MeetingPagination } from "@/components/MeetingPagination";
import { MeetingAudioReview } from "@/components/MeetingAudioReview";
import { MeetingTextReview } from "@/components/MeetingTextReview";
import { CorrectedTranscriptText } from "@/components/CorrectedTranscriptText";
import { meetingErrorKey, recordingTime } from "@/lib/meetingErrors";
import { MeetingService, type Meeting, type MeetingSpeaker, type MeetingTranscript } from "@/services/meetings";
import { Icon } from "@/components/ui/Icon";
import { SpeakerAvatar } from "@/components/ui/SpeakerAvatar";

const reasonKeys: Readonly<Record<string, string>> = {
  insufficient_speech: "meeting.reason.insufficientSpeech", inconsistent_audio: "meeting.reason.inconsistentAudio",
  clipped_audio: "meeting.reason.clippedAudio", invalid_audio: "meeting.reason.invalidAudio",
  insufficient_margin: "meeting.reason.insufficientMargin", below_match_threshold: "meeting.reason.belowMatch",
  overlapping_identity_conflict: "meeting.reason.overlapConflict", reconciliation_ambiguous: "meeting.reason.reconciliation",
  automatic_memory_disabled: "meeting.reason.memoryDisabled", matched: "meeting.reason.matched",
  new_profile_created: "meeting.reason.enrolled", no_profiles: "meeting.reason.noProfiles",
  below_new_threshold: "meeting.reason.unknown",
};

export function MeetingResults({ meeting, revision }: { meeting: Meeting; revision: number }) {
  const { user } = useAuth();
  return <MeetingResultsContent key={`${meeting.public_id}:${user?.public_id}:${user?.tenant_id}`} meeting={meeting} revision={revision} />;
}

function MeetingResultsContent({ meeting, revision }: { meeting: Meeting; revision: number }) {
  const { t, locale } = useIntl();
  const { hasPermission, user } = useAuth();
  const [speakerPage, setSpeakerPage] = useState<Awaited<ReturnType<typeof MeetingService.speakers>> | null>(null);
  const [transcriptPage, setTranscriptPage] = useState<Awaited<ReturnType<typeof MeetingService.transcript>> | null>(null);
  const [speakerOffset, setSpeakerOffset] = useState(0);
  const [textOffset, setTextOffset] = useState(0);
  const [selection, setSelection] = useState<{ scope: string; turn: MeetingTranscript } | null>(null);
  const [review, setReview] = useState<{ scope: string; transcriptId: string } | null>(null);
  const [correctionSaved, setCorrectionSaved] = useState(false);
  const selectionScope = `${meeting.public_id}:${speakerOffset}:${textOffset}:${user?.public_id}:${user?.tenant_id}`;
  const listenTrigger = useRef<HTMLButtonElement | null>(null);
  const reviewTrigger = useRef<HTMLButtonElement | null>(null);
  const canReview = Boolean(user && hasPermission("meeting_analysis:read") && hasPermission("meeting_analysis:run") && meeting.status === "succeeded" && transcriptPage && !transcriptPage.provisional);
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
    <nav className="result-view-nav" aria-label={t("meeting.detailTitle")}>
      <a href="#meeting-transcript-heading"><Icon name="audio" size={16} />{t("meeting.transcript")}</a>
      <a href="#meeting-speakers-heading"><Icon name="users" size={16} />{t("meeting.speakers")}</a>
    </nav>
    <div className="meeting-results">
      <section className="panel meeting-speaker-panel" aria-labelledby="meeting-speakers-heading" aria-busy={loading}>
        <div className="section-heading"><h2 id="meeting-speakers-heading" tabIndex={-1}>{t("meeting.speakers")}</h2>{speakerPage && <span className="count-badge">{new Intl.NumberFormat(locale).format(speakerPage.total)}</span>}</div>
        <p className="field-hint">{t("meeting.speakersHint")}</p>
        {speakerPage?.items.length === 0 && <p className="empty-card">{t("meeting.speakersEmpty")}</p>}
        <ul className="profiles">{speakerPage?.items.map((speaker) => <li key={speaker.public_id} className="profile-card meeting-speaker-card" data-speaker-id={speaker.public_id} data-profile-id={speaker.profile_public_id ?? ""}>
          <div className="speaker-card-heading"><SpeakerAvatar name={label(speaker)} index={speaker.ordinal} /><div className="speaker-card-copy"><h3>{label(speaker)}</h3>
            <p className="field-hint">{t("meeting.speech", { seconds: new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(speaker.speech_seconds) })}</p></div></div>
          <p className={`status-badge status-${speaker.decision === "profile_pending" || speaker.decision === "ambiguous" ? "queued" : "succeeded"}`}>{t(`meeting.decision.${speaker.decision}`)}</p>
          {speaker.profile_deleted && <p className="notice">{t("meeting.profileDeleted")}</p>}
          {speaker.decision === "profile_pending" && <p className="field-hint">{t("meeting.pendingHint")}</p>}
          {speaker.decision === "ambiguous" && <p className="field-hint">{t("meeting.ambiguousHint")}</p>}
          {Object.hasOwn(reasonKeys, speaker.reason) && <p className="field-hint">{t(reasonKeys[speaker.reason])}</p>}
          {hasPermission("meeting_analysis:run") && (!speaker.profile_public_id || hasPermission("speaker_profiles:write")) && <button className="button-quiet" onClick={(event) => {
            renameTrigger.current = event.currentTarget; setEditing(speaker); setName(speaker.profile_name || speaker.display_name || ""); setSaveError(null);
          }}>{t("common.rename")}</button>}
        </li>)}</ul>
        {speakerPage && <MeetingPagination label={t("meeting.speakers")} offset={speakerOffset} total={speakerPage.total} limit={20} onChange={(value) => { setSelection(null); setReview(null); setLoading(true); setSpeakerOffset(value); }} />}
        {editing && <form className="inline-action" aria-label={t("common.rename")} onSubmit={(event) => void save(event)}>
          <h3>{label(editing)}</h3>
          <p className="field-hint">{t(editing.profile_public_id ? "meeting.profileNameHint" : "meeting.localNameHint")}</p>
          <p className="field-hint">{t("meeting.renameIdentityHint")}</p>
          <label htmlFor="meeting-speaker-name">{t("meeting.speakerName")}</label>
          <input ref={input} id="meeting-speaker-name" value={name} maxLength={120} required disabled={saving} onChange={(event) => setName(event.target.value)} />
          {saveError && <p role="alert" className="error-message">{t(saveError)}</p>}
          {saveError === "meeting.error.name_conflict" && <button type="button" className="button-secondary" disabled={saving} onClick={() => { closeEditor(); setLoading(true); setRefresh((value) => value + 1); }}>{t("common.refresh")}</button>}
          <div className="action-row"><button disabled={saving || !name.trim()} type="submit">{t("common.save")}</button><button className="button-secondary" disabled={saving} type="button" onClick={closeEditor}>{t("common.cancel")}</button></div>
        </form>}
      </section>
      <section className="panel meeting-transcript-panel" aria-labelledby="meeting-transcript-heading" aria-busy={loading}>
        <div className="section-heading"><h2 id="meeting-transcript-heading" tabIndex={-1}>{t("meeting.transcript")}</h2><Icon name="audio" size={20} /></div>
        <p className="field-hint">{t("meeting.transcriptHint")}</p>
        {correctionSaved && <p role="status" className="notice">{t("meeting.review.saved")}</p>}
        {transcriptPage?.provisional && <p className="notice">{t("meeting.provisional")}</p>}
        {transcriptPage?.items.length === 0 && <p className="empty-card">{t("meeting.transcriptEmpty")}</p>}
        <ol className="meeting-transcript">{transcriptPage?.items.map((turn) => {
          const speakerName = turn.speaker_name || (turn.speaker_ordinal != null ? t("meeting.speakerLabel", { number: new Intl.NumberFormat(locale).format(turn.speaker_ordinal + 1) }) : t("meeting.unknownSpeaker"));
          return <li key={turn.public_id} className="transcript-turn" data-transcript-id={turn.public_id}>
            <SpeakerAvatar name={speakerName} index={turn.speaker_ordinal ?? -1} />
            <div className="transcript-turn-body">
              <div className="transcript-turn-heading"><strong>{speakerName}</strong>
                <span className="muted meeting-timestamp">{recordingTime(turn.start_seconds)}–{recordingTime(turn.end_seconds)}</span></div>
              <CorrectedTranscriptText turn={turn} />
              {(turn.overlap || turn.uncertain) && <div className="action-row">{turn.overlap && <span className="status-badge status-queued">{t("meeting.overlap")}</span>}{turn.uncertain && <span className="status-badge status-queued">{t("meeting.uncertain")}</span>}</div>}
              <button type="button" className="button-quiet" aria-expanded={selection?.scope === selectionScope && selection.turn.public_id === turn.public_id} aria-label={t("meeting.audio.listenLabel", { name: speakerName, time: recordingTime(turn.start_seconds) })} onClick={(event) => {
                listenTrigger.current = event.currentTarget; setSelection({ scope: selectionScope, turn });
              }}>{t("meeting.audio.listen")}</button>
              {selection?.scope === selectionScope && selection.turn.public_id === turn.public_id && <MeetingAudioReview key={selectionScope} meeting={meeting} turn={turn} speakerName={speakerName} onClose={() => { setSelection(null); listenTrigger.current?.focus(); }} />}
              {canReview && <button type="button" className="button-quiet" aria-expanded={review?.scope === selectionScope && review.transcriptId === turn.public_id} aria-label={t("meeting.review.actionLabel", { name: speakerName, time: recordingTime(turn.start_seconds) })} onClick={(event) => {
                reviewTrigger.current = event.currentTarget; setCorrectionSaved(false); setReview({ scope: selectionScope, transcriptId: turn.public_id });
              }}>{t("meeting.review.action")}</button>}
              {canReview && review?.scope === selectionScope && review.transcriptId === turn.public_id && <MeetingTextReview key={selectionScope} meetingId={meeting.public_id} turn={turn} onClose={() => { setReview(null); reviewTrigger.current?.focus(); }} onSaved={(correction) => {
                setTranscriptPage((current) => current && ({ ...current, items: current.items.map((item) => item.public_id === turn.public_id ? { ...item, correction } : item) }));
                setReview(null); setCorrectionSaved(true); reviewTrigger.current?.focus();
              }} />}
            </div>
          </li>;
        })}</ol>
        {transcriptPage && <MeetingPagination label={t("meeting.transcript")} offset={textOffset} total={transcriptPage.total} limit={50} onChange={(value) => { setSelection(null); setReview(null); setLoading(true); setTextOffset(value); }} />}
      </section>
    </div>
  </>;
}
