import { useEffect, type ReactNode } from "react";
import { NavLink } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";

export function SpeakerLayout({ titleKey, children }: { titleKey: string; children: ReactNode }) {
  const { logout, hasPermission } = useAuth();
  const { locale, setLocale, t } = useIntl();
  const title = t(titleKey);
  useEffect(() => { document.title = `${title} · VoiceUp`; }, [title]);
  return (
    <main className="workspace">
      <header className="workspace-header">
        <NavLink className="brand" to="/" aria-label={t("nav.home")}>VoiceUp<span>{t("speaker.pilot")}</span></NavLink>
        <div className="header-actions">
          <button className="button-quiet" onClick={() => setLocale(locale === "tr" ? "en" : "tr")}>{t("common.otherLanguage")}</button>
          <button className="button-quiet" onClick={logout}>{t("common.signOut")}</button>
        </div>
      </header>
      <nav className="workspace-nav" aria-label={t("nav.main")}>
        {hasPermission("speaker_profiles:read") && <NavLink to="/speaker-profiles">{t("nav.profiles")}</NavLink>}
        {hasPermission("speaker_analysis:read") && <NavLink to="/speaker-analysis">{t("nav.analysis")}</NavLink>}
      </nav>
      <div className="page-heading"><div className="eyebrow">{t("speaker.pilot")}</div><h1>{title}</h1></div>
      {children}
    </main>
  );
}
