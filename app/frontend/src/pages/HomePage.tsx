import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { SpeakerLayout } from "@/components/SpeakerLayout";
import { Link } from "react-router";

export default function HomePage() {
  const { hasPermission } = useAuth();
  const { t } = useIntl();
  return (
    <SpeakerLayout titleKey="home.title">
      <section className="hero">
        <p>{t("home.intro")}</p>
        <div className="action-row">
          {hasPermission("meeting_analysis:read") && <Link className="button-link" to="/meetings">{t("nav.meetings")}</Link>}
          {hasPermission("speaker_profiles:read") && <Link className="button-link" to="/speaker-profiles">{t("nav.profiles")}</Link>}
          {hasPermission("speaker_analysis:read") && <Link className="button-link button-secondary" to="/speaker-analysis">{t("nav.analysis")}</Link>}
        </div>
      </section>
      <section className="panel">
        <h2>{t("home.scopeTitle")}</h2>
        <p>{t("home.scope")}</p>
      </section>
    </SpeakerLayout>
  );
}
