import { useEffect, type ReactNode } from "react";
import { NavLink } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import { useIntl } from "@/contexts/IntlContext";
import { Icon } from "@/components/ui/Icon";
import { SpeakerAvatar } from "@/components/ui/SpeakerAvatar";

export function SpeakerLayout({ titleKey, children }: { titleKey: string; children: ReactNode }) {
  const { user, logout, hasPermission } = useAuth();
  const { locale, setLocale, t } = useIntl();
  const title = t(titleKey);
  useEffect(() => { document.title = `${title} · VoiceUp`; }, [title]);
  return (
    <div className="workspace">
      <a className="skip-link" href="#workspace-content">{t("workspace.skipContent")}</a>
      <aside className="workspace-sidebar">
        <NavLink className="brand" to="/" aria-label={t("workspace.brand")}><span className="brand-mark"><Icon name="audio" size={25} /></span><span>VoiceUp<span className="brand-caption">{t("workspace.brandCaption")}</span></span></NavLink>
        <div className="sidebar-label">{t("workspace.navigation")}</div>
        <nav className="workspace-nav" aria-label={t("nav.main")}>
          <NavLink to="/" end><Icon name="home" />{t("nav.home")}</NavLink>
          {hasPermission("meeting_analysis:read") && <NavLink to="/meetings"><Icon name="meetings" />{t("nav.meetings")}</NavLink>}
          {hasPermission("speaker_profiles:read") && <NavLink to="/speaker-profiles"><Icon name="users" />{t("nav.profiles")}</NavLink>}
          {hasPermission("speaker_analysis:read") && <NavLink to="/speaker-analysis"><Icon name="audio" />{t("nav.analysis")}</NavLink>}
        </nav>
        <div className="sidebar-note"><Icon name="sparkles" /><strong>{t("workspace.memoryTitle")}</strong><p>{t("workspace.memoryHint")}</p></div>
        <div className="sidebar-account"><SpeakerAvatar name={user?.username || t("workspace.account")} /><div className="account-copy"><strong>{user?.username || t("workspace.account")}</strong><span>{t("workspace.account")}</span></div></div>
        <button className="sidebar-logout" onClick={logout}><Icon name="logout" size={18} />{t("common.signOut")}</button>
      </aside>
      <div className="workspace-body">
        <header className="workspace-header">
          <div className="workspace-breadcrumb"><span>{t("workspace.label")}</span><Icon name="chevron-right" size={14} /><strong>{title}</strong></div>
          <button className="button-quiet" onClick={() => setLocale(locale === "tr" ? "en" : "tr")}><Icon name="globe" size={17} />{t("common.otherLanguage")}</button>
        </header>
        <main className="workspace-main" id="workspace-content" tabIndex={-1}>
          <div className="page-heading"><h1>{title}</h1></div>
          {children}
        </main>
      </div>
    </div>
  );
}
