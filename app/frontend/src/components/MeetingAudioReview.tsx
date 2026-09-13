import { useEffect, useRef, useState } from "react";
import { useIntl } from "@/contexts/IntlContext";
import { ApiError } from "@/lib/apiClient";
import { recordingTime } from "@/lib/meetingErrors";
import { MeetingService, type Meeting, type MeetingTranscript } from "@/services/meetings";

type Props = { meeting: Meeting; turn: MeetingTranscript; speakerName: string; onClose: () => void };
type SourceState = { url: string; error: string | null; loading: boolean };

function errorKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 410 || error.status === 404) return "meeting.audio.unavailable";
    if (error.status === 401 || error.status === 403) return "meeting.audio.forbidden";
    if (error.code === "invalid_response") return "meeting.audio.invalid";
    if (error.code === "invalid_audio_range") return "meeting.audio.empty";
    if (error.status === 409) return "meeting.audio.notReady";
  }
  return "meeting.audio.failed";
}

export function MeetingAudioReview(props: Props) {
  // Selection changes reset the local window and release the old source before loading.
  const key = `${props.meeting.public_id}:${props.turn.public_id}:${props.turn.start_seconds}:${props.turn.end_seconds}`;
  return <AudioSelection key={key} {...props} />;
}

function AudioSelection({ meeting, turn, speakerName, onClose }: Props) {
  const { t } = useIntl();
  const [windowIndex, setWindowIndex] = useState(0);
  const [retry, setRetry] = useState(0);
  const start = Math.max(0, turn.start_seconds);
  const end = Math.min(turn.end_seconds, meeting.duration_seconds ?? 0);
  const valid = Number.isFinite(start) && Number.isFinite(end) && end > start;
  const windowStart = start + windowIndex * 30;
  const windowEnd = Math.min(windowStart + 30, end);
  const identity = `${windowStart}:${windowEnd}:${retry}:${meeting.source_available}`;
  return <section className="audio-review inline-action" aria-label={t("meeting.audio.title")} data-audio-review="true">
    <div className="section-heading"><h3>{t("meeting.audio.title")}</h3><button type="button" className="button-quiet" onClick={onClose}>{t("meeting.audio.close")}</button></div>
    <p><strong>{speakerName}</strong> · <span>{recordingTime(windowStart)}–{recordingTime(windowEnd)}</span></p>
    <p className="field-hint">{t("meeting.audio.hint")}</p>
    {!valid ? <p role="status">{t("meeting.audio.empty")}</p> : !meeting.source_available ? <p role="status">{t("meeting.audio.unavailable")}</p> :
      <AudioWindow key={identity} meetingId={meeting.public_id} start={windowStart} end={windowEnd} onRetry={() => setRetry((value) => value + 1)} />}
    {valid && end - start > 30 && <div className="action-row" aria-label={t("meeting.audio.parts")} role="group">
      <button type="button" className="button-secondary" disabled={windowIndex === 0} onClick={() => setWindowIndex((value) => value - 1)}>{t("meeting.audio.previous")}</button>
      <button type="button" className="button-secondary" disabled={windowEnd >= end} onClick={() => setWindowIndex((value) => value + 1)}>{t("meeting.audio.next")}</button>
    </div>}
  </section>;
}

function AudioWindow({ meetingId, start, end, onRetry }: { meetingId: string; start: number; end: number; onRetry: () => void }) {
  const { t } = useIntl();
  const [source, setSource] = useState<SourceState>({ url: "", error: null, loading: true });
  const audio = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    let url = "";
    const element = audio.current;
    void MeetingService.audioPreview(meetingId, { start_seconds: start, end_seconds: end }, controller.signal).then((blob) => {
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(blob);
      setSource({ url, error: null, loading: false });
    }).catch((error: unknown) => { if (!controller.signal.aborted) setSource({ url: "", error: errorKey(error), loading: false }); });
    return () => {
      controller.abort();
      element?.pause();
      element?.removeAttribute("src");
      if (url) URL.revokeObjectURL(url);
    };
  }, [meetingId, start, end]);
  return <>
    {source.loading && <p role="status">{t("meeting.audio.loading")}</p>}
    {source.error && <div role="alert" className="error-message"><p>{t(source.error)}</p><button type="button" onClick={onRetry}>{t("common.retry")}</button></div>}
    <audio ref={audio} controls preload="metadata" hidden={!source.url || Boolean(source.error)} src={source.url || undefined} aria-label={t("meeting.audio.title")} onError={() => setSource((value) => ({ ...value, error: "meeting.audio.invalid" }))} />
  </>;
}
