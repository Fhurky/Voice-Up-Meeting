import { Navigate, Route, Routes } from "react-router";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { GeneratedRoutes } from "@/generated/routes";
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import NotFoundPage from "@/pages/NotFoundPage";
import { Suspense, useState } from "react";
import { useIntl } from "@/contexts/IntlContext";
import { Icon } from "@/components/ui/Icon";
import { MeetingUploadContext, type MeetingUploadSelection } from "@/contexts/meetingUploadSelection";

function RouteLoading() {
  const { t } = useIntl();
  return <main className="center route-loading" role="status"><span className="section-icon"><Icon name="audio" size={24} /></span>{t("common.loading")}</main>;
}

export default function App() {
  const [selection, setSelection] = useState<MeetingUploadSelection>(null);
  return (
    <MeetingUploadContext.Provider value={{ selection, setSelection }}>
    {/* One persistent boundary: a navigation that waits for page code keeps the current screen. */}
    <Suspense fallback={<RouteLoading />}>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthGuard />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<Navigate to="/" replace />} />
        {GeneratedRoutes}
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
    </Suspense>
    </MeetingUploadContext.Provider>
  );
}
