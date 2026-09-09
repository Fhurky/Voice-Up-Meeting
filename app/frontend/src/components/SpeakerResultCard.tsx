import { Link } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import type { SpeakerResult } from "@/services/speakers";

const reasons = new Set(["enrolled", "matched", "no_profiles", "below_new_threshold", "below_match_threshold", "insufficient_margin"]);

export function SpeakerResultCard({ result }: { result: SpeakerResult }) {
  const { t, locale } = useIntl();
  const { hasPermission } = useAuth();
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 3 });
  const activeIdentity = !result.profile_deleted && (result.decision === "recognized" || result.decision === "enrolled");
  return <section className={`panel result-card decision-${result.decision}`} aria-labelledby="result-heading">
    <div className="eyebrow">{t("speaker.result.title")}</div>
    <h2 id="result-heading">{t(result.profile_deleted ? "speaker.result.deleted" : `speaker.decision.${result.decision}`)}</h2>
    {activeIdentity && <p className="result-name">{result.profile_name}</p>}
    <p>{t(result.profile_deleted ? "speaker.result.deletedHint" : `speaker.reason.${reasons.has(result.reason) ? result.reason : "other"}`)}</p>
    {activeIdentity && hasPermission("speaker_profiles:read") && <Link className="text-link" to="/speaker-profiles">{t("speaker.result.viewProfiles")}</Link>}
    <dl className="result-details">
      <div><dt>{t("speaker.result.similarity")}</dt><dd>{result.similarity == null ? t("common.unavailable") : number.format(result.similarity)}</dd></div>
      <div><dt>{t("speaker.result.runnerUp")}</dt><dd>{result.runner_up_similarity == null ? t("common.unavailable") : number.format(result.runner_up_similarity)}</dd></div>
      <div><dt>{t("speaker.result.speech")}</dt><dd>{number.format(result.speech_seconds)}</dd></div>
      <div><dt>{t("speaker.result.windows")}</dt><dd>{number.format(result.windows_count)}</dd></div>
    </dl>
    <p className="notice">{t("speaker.result.scoreHint")}</p>
    <details className="model-details"><summary>{t("speaker.result.technical")}</summary>
      <dl className="result-details">
        <div><dt>{t("speaker.result.model")}</dt><dd>{result.model_id}</dd></div>
        <div><dt>{t("speaker.result.revision")}</dt><dd><code>{result.model_revision}</code></dd></div>
        <div><dt>{t("speaker.result.device")}</dt><dd>{result.device}</dd></div>
        <div><dt>{t("speaker.result.matchThreshold")}</dt><dd>{number.format(result.policy.match_threshold)}</dd></div>
        <div><dt>{t("speaker.result.newThreshold")}</dt><dd>{number.format(result.policy.new_threshold)}</dd></div>
        <div><dt>{t("speaker.result.margin")}</dt><dd>{number.format(result.policy.margin)}</dd></div>
      </dl>
    </details>
  </section>;
}
