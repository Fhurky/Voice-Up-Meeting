// Route is intentionally pre-registered for generated routes.
import { Route } from "react-router";
// PermissionRoute is intentionally pre-registered for generated protected routes.
import { PermissionRoute } from "@/components/auth/PermissionRoute";
import { SpeakerProfilesRoute, SpeakerAnalysisRoute, SpeakerJobRoute, MeetingsRoute, MeetingRoute } from "@/components/SpeakerPages";
// kt-scaffold:imports

void PermissionRoute;

export const GeneratedRoutes = <>
  <Route path="/meetings" element={<MeetingsRoute />} />
  <Route path="/meetings/:publicId" element={<MeetingRoute />} />
  <Route path="/speaker-profiles" element={<SpeakerProfilesRoute />} />
  <Route path="/speaker-analysis" element={<SpeakerAnalysisRoute />} />
  <Route path="/speaker-jobs/:publicId" element={<SpeakerJobRoute />} />
  {/* kt-scaffold:routes */}
</>;
