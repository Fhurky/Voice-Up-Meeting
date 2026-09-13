import { useEffect, useState } from "react";
import { Link } from "react-router";
import { AudioJobForm } from "@/components/AudioJobForm";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { errorMessageKey } from "@/lib/speakerErrors";
import { SpeakerService, type SpeakerJob } from "@/services/speakers";
import { Icon } from "@/components/ui/Icon";

export default function SpeakerAnalysisPage() {
  const { t, locale } = useIntl();
  const { hasPermission } = useAuth();
  const [jobs, setJobs] = useState<SpeakerJob[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    SpeakerService.jobs(offset, controller.signal).then((page) => {
      if (controller.signal.aborted) return;
      setJobs(page.items); setTotal(page.total); setLoading(false); setError(null);
    }).catch((caught: unknown) => { if (!controller.signal.aborted) { setError(errorMessageKey(caught)); setLoading(false); } });
    return () => controller.abort();
  }, [offset, revision]);

  return <SpeakerLayout titleKey="speaker.analysis.title">
    <p className="page-intro">{t("speaker.analysis.intro")}</p>
    <div className="pilot-grid analysis-workspace">
      <section className="panel" aria-labelledby="identify-heading"><div className="section-heading"><div className="section-title-group"><span className="section-icon"><Icon name="audio" size={20} /></span><h2 id="identify-heading">{t("speaker.analysis.new")}</h2></div></div>
        {hasPermission("speaker_analysis:run") ? <AudioJobForm purpose="identify" /> : <p>{t("speaker.analysis.readOnly")}</p>}
      </section>
      <section className="panel" aria-labelledby="jobs-heading">
        <div className="section-heading"><h2 id="jobs-heading">{t("speaker.jobs.history")}</h2><button className="button-quiet" disabled={loading} onClick={() => { setLoading(true); setRevision((value) => value + 1); }}><Icon name="refresh" size={16} />{t("common.refresh")}</button></div>
        <p className="muted">{t("speaker.jobs.retention")}</p>
        {error && <p role="alert" className="error-message">{t(error)}</p>}
        {loading ? <p role="status">{t("common.loading")}</p> : <>
          {jobs.length === 0 ? <div className="empty-card"><span className="empty-icon"><Icon name="audio" size={28} /></span><p>{t("speaker.jobs.empty")}</p></div> : <ul className="job-list">
            {jobs.map((job) => <li key={job.public_id}>
              <Link className="job-identity" to={`/speaker-jobs/${encodeURIComponent(job.public_id)}`}><span className="section-icon"><Icon name={job.purpose === "enroll" ? "users" : "audio"} size={18} /></span><span className="job-copy"><strong>{t(`speaker.purpose.${job.purpose}`)}</strong><time dateTime={job.created_at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(job.created_at))}</time></span><Icon name="chevron-right" size={16} /></Link>
              <span className={`status-badge status-${job.status}`}>{t(`speaker.status.${job.status}`)}</span>
            </li>)}
          </ul>}
          <div className="pagination" aria-label={t("common.pagination")}>
            <button className="button-secondary" disabled={offset === 0} onClick={() => { setLoading(true); setOffset(Math.max(0, offset - 20)); }}>{t("common.previous")}</button>
            <button className="button-secondary" disabled={offset + jobs.length >= total} onClick={() => { setLoading(true); setOffset(offset + 20); }}>{t("common.next")}</button>
          </div>
        </>}
      </section>
    </div>
  </SpeakerLayout>;
}
