import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { Link } from "react-router";
import { Icon } from "@/components/ui/Icon";
import { MeetingService } from "@/services/meetings";
import { SpeakerService } from "@/services/speakers";
import { meetingErrorKey } from "@/lib/meetingErrors";
import { errorMessageKey } from "@/lib/speakerErrors";

export default function HomePage() {
  const { user, hasPermission } = useAuth();
  const scope = JSON.stringify([user?.public_id, user?.tenant_id,
    hasPermission("meeting_analysis:read"), hasPermission("speaker_profiles:read")]);
  return <HomeOverview key={scope} />;
}

function HomeOverview() {
  const { user, hasPermission } = useAuth();
  const { t, locale } = useIntl();
  const canReadMeetings = hasPermission("meeting_analysis:read");
  const canReadProfiles = hasPermission("speaker_profiles:read");
  const canUpload = canReadMeetings && hasPermission("meeting_analysis:run");
  const [meetings, setMeetings] = useState<Awaited<ReturnType<typeof MeetingService.list>> | null>(null);
  const [profileCount, setProfileCount] = useState<number | null>(null);
  const [meetingError, setMeetingError] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    const pending: Promise<void>[] = [];
    if (canReadMeetings) pending.push(MeetingService.list(0, controller.signal).then((page) => {
      if (!controller.signal.aborted) { setMeetings(page); setMeetingError(null); }
    }).catch((error: unknown) => { if (!controller.signal.aborted) setMeetingError(meetingErrorKey(error)); }));
    if (canReadProfiles) pending.push(SpeakerService.profiles(0, controller.signal).then((page) => {
      if (!controller.signal.aborted) { setProfileCount(page.total); setProfileError(null); }
    }).catch((error: unknown) => { if (!controller.signal.aborted) setProfileError(errorMessageKey(error)); }));
    void Promise.all(pending).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [canReadMeetings, canReadProfiles, revision]);
  const number = new Intl.NumberFormat(locale);
  function retry() { setLoading(true); setRevision((current) => current + 1); }
  return (
    <SpeakerLayout titleKey="home.title">
      <p className="page-intro">{t("home.greeting", { name: user?.username ?? "" })}</p>
      {canUpload && <div className="action-cards">
        <Link className="action-card" to="/meetings?new=file"><span className="section-icon"><Icon name="upload" /></span>
          <span className="action-copy"><strong>{t("home.upload")}</strong><span>{t("home.uploadHint")}</span></span><Icon name="arrow-right" size={18} /></Link>
        <Link className="action-card" to="/meetings?new=microphone"><span className="section-icon icon-blue"><Icon name="microphone" /></span>
          <span className="action-copy"><strong>{t("home.record")}</strong><span>{t("home.recordHint")}</span></span><Icon name="arrow-right" size={18} /></Link>
      </div>}
      {(canReadMeetings || canReadProfiles) && <div className="overview-stats" aria-busy={loading}>
        {canReadMeetings && <Link to="/meetings" className="stat-card"><span className="stat-label">{t("home.meetingTotal")}</span><strong>{meetings ? number.format(meetings.total) : t("home.valuePending")}</strong></Link>}
        {canReadProfiles && <Link to="/speaker-profiles" className="stat-card"><span className="stat-label">{t("home.profileTotal")}</span><strong>{profileCount == null ? t("home.valuePending") : number.format(profileCount)}</strong></Link>}
      </div>}
      {(meetingError || profileError) && <div className="error-message" role="alert">{meetingError && <p>{t(meetingError)}</p>}{profileError && <p>{t(profileError)}</p>}<button className="button-secondary" disabled={loading} onClick={retry}>{t("common.retry")}</button></div>}
      {canReadMeetings && <section className="panel recent-meetings" aria-busy={loading}>
        <div className="section-heading"><h2>{t("meeting.history")}</h2>{meetings && meetings.total > 0 && <Link className="text-link" to="/meetings">{t("home.viewAll")}<Icon name="arrow-right" size={16} /></Link>}</div>
        {loading && !meetings && <p className="loading-state" role="status">{t("common.loading")}</p>}
        {!loading && !meetingError && meetings?.total === 0 && <div className="empty-card"><h3>{t("meeting.empty")}</h3><p>{t("meeting.emptyHint")}</p>
          <ol className="workflow-steps" aria-label={t("home.workflowTitle")}>{["upload", "review", "remember"].map((step, index) => <li key={step}><span className="step-number">{number.format(index + 1)}</span><div><h3>{t(`home.step.${step}`)}</h3><p>{t(`home.step.${step}Hint`)}</p></div></li>)}</ol></div>}
        <ul className="job-list home-history">{meetings?.items.slice(0, 5).map((meeting) => <li key={meeting.public_id}>
          <Link to={`/meetings/${meeting.public_id}`}><strong>{meeting.title}</strong><time dateTime={meeting.created_at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(meeting.created_at))}</time></Link><span className={`status-badge status-${meeting.status}`}>{t(`meeting.status.${meeting.status}`)}</span>
        </li>)}</ul>
      </section>}
      <p className="page-footnote"><Icon name="shield" size={15} />{t("brand.assurance")}</p>
    </SpeakerLayout>
  );
}
