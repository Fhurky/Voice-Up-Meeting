import { Navigate, Route, Routes } from "react-router";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { GeneratedRoutes } from "@/generated/routes";
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import NotFoundPage from "@/pages/NotFoundPage";
import { useState } from "react";
import { MeetingUploadContext, type MeetingUploadSelection } from "@/contexts/meetingUploadSelection";

export default function App() {
  const [selection, setSelection] = useState<MeetingUploadSelection>(null);
  return (
    <MeetingUploadContext.Provider value={{ selection, setSelection }}>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthGuard />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<Navigate to="/" replace />} />
        {GeneratedRoutes}
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
    </MeetingUploadContext.Provider>
  );
}
