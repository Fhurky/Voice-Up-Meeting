import { lazy, Suspense, type ReactNode } from "react";
import { PermissionRoute } from "@/components/auth/PermissionRoute";
import { useIntl } from "@/contexts/IntlContext";

const ProfilesPage = lazy(() => import("@/pages/SpeakerProfilesPage"));
const AnalysisPage = lazy(() => import("@/pages/SpeakerAnalysisPage"));
const JobPage = lazy(() => import("@/pages/SpeakerJobPage"));

function DeferredPage({ permission, children }: { permission: string; children: ReactNode }) {
  const { t } = useIntl();
  return <PermissionRoute permission={permission}><Suspense fallback={<main className="center" role="status">{t("common.loading")}</main>}>{children}</Suspense></PermissionRoute>;
}

export function SpeakerProfilesRoute() { return <DeferredPage permission="speaker_profiles:read"><ProfilesPage /></DeferredPage>; }
export function SpeakerAnalysisRoute() { return <DeferredPage permission="speaker_analysis:read"><AnalysisPage /></DeferredPage>; }
export function SpeakerJobRoute() { return <DeferredPage permission="speaker_analysis:read"><JobPage /></DeferredPage>; }
