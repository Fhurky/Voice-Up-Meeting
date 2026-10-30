import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { MeetingUploadForm } from "@/components/MeetingUploadForm";
import { MeetingPagination } from "@/components/MeetingPagination";
import { MeetingService } from "@/services/meetings";
import { meetingErrorKey } from "@/lib/meetingErrors";
import { Icon } from "@/components/ui/Icon";

export default function MeetingsPage() {
  const { t, locale } = useIntl();
  const { user, hasPermission } = useAuth();
  const [params, setParams] = useSearchParams();
  const requested = params.get("new");
  const initialSource = requested === "microphone" ? "microphone" : "file";
  const canRun = hasPermission("meeting_analysis:run");
  const composing = canRun && (requested === "file" || requested === "microphone");
  const captureScope = JSON.stringify([user?.public_id, user?.tenant_id, hasPermission("speaker_profiles:write"), initialSource]);
  const [page, setPage] = useState<Awaited<ReturnType<typeof MeetingService.list>> | null>(null);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void MeetingService.list(offset, controller.signal).then((result) => { if (!controller.signal.aborted) { setPage(result); setError(null); } })
      .catch((failure: unknown) => { if (!controller.signal.aborted) setError(meetingErrorKey(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [offset, revision]);
  return <SpeakerLayout titleKey="meeting.listTitle" actions={canRun && !composing ? <button onClick={() => setParams({ new: "file" })}><Icon name="plus" size={18} />{t("meeting.new")}</button> : undefined}>
    <p className="page-intro">{t("meeting.intro")}</p>
    {!canRun && <p className="field-hint">{t("meeting.readOnly")}</p>}
    {composing && <MeetingUploadForm key={captureScope} initialSource={initialSource} onClose={() => setParams({})} />}
    <section className="panel meeting-history-panel" aria-busy={loading}>
      <div className="section-heading"><h2>{t("meeting.history")}</h2><button className="button-quiet" disabled={loading} onClick={() => { setLoading(true); setRevision((value) => value + 1); }}><Icon name="refresh" size={16} />{t("common.refresh")}</button></div>
      {loading && <p role="status">{t("common.loading")}</p>}
      {error && <p className="error-message" role="alert">{t(error)}</p>}
      {!loading && !error && page?.items.length === 0 && <div className="empty-card"><h3>{t("meeting.empty")}</h3><p>{t("meeting.emptyHint")}</p></div>}
      <ul className="history-list">{page?.items.map((meeting) => <li key={meeting.public_id}>
        <Link className="history-link" to={`/meetings/${meeting.public_id}`}>
          <span className="history-copy"><strong>{meeting.title}</strong><time dateTime={meeting.created_at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(meeting.created_at))}</time></span>
          <span className={`status-badge status-${meeting.status}`}>{t(`meeting.status.${meeting.status}`)}</span>
          <span className="history-arrow"><Icon name="chevron-right" size={16} /></span>
        </Link>
      </li>)}</ul>
      {page && <MeetingPagination label={t("meeting.history")} offset={offset} total={page.total} limit={20} onChange={(value) => { setLoading(true); setOffset(value); }} />}
    </section>
    <p className="page-footnote"><Icon name="shield" size={15} />{t("meeting.retention")}</p>
  </SpeakerLayout>;
}
