import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { SpeakerResultCard } from "@/components/SpeakerResultCard";
import { useIntl } from "@/contexts/IntlContext";
import { ApiError } from "@/lib/apiClient";
import { errorMessageKey, jobErrorKey } from "@/lib/speakerErrors";
import { SpeakerService, type SpeakerJob } from "@/services/speakers";

function JobStatus({ publicId }: { publicId: string }) {
  const { t, locale } = useIntl();
  const [job, setJob] = useState<SpeakerJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let polls = 0;
    let failures = 0;
    async function poll() {
      try {
        const next = await SpeakerService.job(publicId, controller.signal);
        if (controller.signal.aborted) return;
        setJob(next); setError(null); failures = 0;
        if (next.status === "succeeded" || next.status === "failed") return;
      } catch (caught) {
        if (controller.signal.aborted) return;
        setError(errorMessageKey(caught)); failures += 1;
        if (caught instanceof ApiError && [401, 403, 404, 410].includes(caught.status)) return;
        if (failures >= 3) { setPaused(true); return; }
      }
      polls += 1;
      if (polls >= 180) { setPaused(true); return; }
      timer = setTimeout(() => { void poll(); }, Math.min(10_000, 2_000 + polls * 250 + failures * 2_000));
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [publicId, revision]);

  return <>
    <section className="panel job-status" aria-labelledby="job-heading">
      <h2 id="job-heading">{t(job ? `speaker.purpose.${job.purpose}` : "speaker.jobs.loading")}</h2>
      {error && <p role="alert" className="error-message">{t(error)}</p>}
      {!job && !error && <p role="status">{t("common.loading")}</p>}
      {job && <>
        <p role="status" aria-live="polite"><span className={`status-badge status-${job.status}`}>{t(`speaker.status.${job.status}`)}</span></p>
        {(job.status === "queued" || job.status === "running") && <p>{t(`speaker.jobs.${job.status}Hint`)}</p>}
        <p className="muted">{t("common.created")} <time dateTime={job.created_at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(job.created_at))}</time></p>
        {job.status === "failed" && <p className="error-message" role="alert">{t(jobErrorKey(job.error?.code ?? "unknown"))}</p>}
      </>}
      {paused && <p className="notice">{t("speaker.jobs.pollingPaused")}</p>}
      {(error || paused) && <button className="button-secondary" onClick={() => { setPaused(false); setError(null); setRevision((value) => value + 1); }}>{t("common.retry")}</button>}
      <p className="field-hint">{t("speaker.jobs.resumeHint")}</p>
    </section>
    {job?.status === "succeeded" && job.result && <SpeakerResultCard result={job.result} />}
    <p><Link className="text-link" to="/speaker-analysis">{t("speaker.jobs.back")}</Link></p>
  </>;
}

export default function SpeakerJobPage() {
  const { publicId = "" } = useParams();
  return <SpeakerLayout titleKey="speaker.jobs.title"><JobStatus key={publicId} publicId={publicId} /></SpeakerLayout>;
}
