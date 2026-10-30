import { lazy, type ReactNode } from "react";
import { PermissionRoute } from "@/components/auth/PermissionRoute";
import { workspacePageLoaders as loaders } from "@/components/workspacePageLoaders";

const ProfilesPage = lazy(loaders.profiles);
const AnalysisPage = lazy(loaders.analysis);
const JobPage = lazy(loaders.job);
const MeetingsPage = lazy(loaders.meetings);
const MeetingPage = lazy(loaders.meeting);
const SettingsPage = lazy(loaders.settings);

// Pages suspend into the single application boundary, so navigation keeps the current
// workspace on screen instead of replacing it with a loading view.
function DeferredPage({ permission, children }: { permission: string; children: ReactNode }) {
  return <PermissionRoute permission={permission}>{children}</PermissionRoute>;
}

export function SpeakerProfilesRoute() { return <DeferredPage permission="speaker_profiles:read"><ProfilesPage /></DeferredPage>; }
export function SpeakerAnalysisRoute() { return <DeferredPage permission="speaker_analysis:read"><AnalysisPage /></DeferredPage>; }
export function SpeakerJobRoute() { return <DeferredPage permission="speaker_analysis:read"><JobPage /></DeferredPage>; }
export function MeetingsRoute() { return <DeferredPage permission="meeting_analysis:read"><MeetingsPage /></DeferredPage>; }
export function SettingsRoute() { return <PermissionRoute superAdmin><SettingsPage /></PermissionRoute>; }
export function MeetingRoute() { return <DeferredPage permission="meeting_analysis:read"><MeetingPage /></DeferredPage>; }
