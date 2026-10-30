export const workspacePageLoaders = {
  profiles: () => import("@/pages/SpeakerProfilesPage"),
  analysis: () => import("@/pages/SpeakerAnalysisPage"),
  job: () => import("@/pages/SpeakerJobPage"),
  meetings: () => import("@/pages/MeetingsPage"),
  meeting: () => import("@/pages/MeetingPage"),
};

let preloaded: Promise<unknown> | null = null;
/** Fetches every workspace page chunk once so later navigation does not wait for code. */
export function preloadWorkspacePages() {
  preloaded ??= Promise.all(Object.values(workspacePageLoaders).map((load) => load())).catch(() => { preloaded = null; });
  return preloaded;
}
