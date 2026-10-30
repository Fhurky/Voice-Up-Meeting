# Plan — MP4 toplantı yükleme

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Ön yüz kütüphanesi | `app/frontend/src/lib/mediaAudio.ts`, `meetingErrors.ts` | Decision 1, 3; Requirement 1 |
| Form ve metinler | `MeetingUploadForm.tsx`, TR/EN kataloglar | Decision 2, 3; Requirement 2 |
| Tarayıcı | `e2e/speaker-identity/16-meeting-mp4-upload.mjs`, `e2e/shared/harness.mjs` | Requirement 3 |

Doğrulama: `mediaAudio.test.ts`, `MeetingUploadForm.test.tsx`, `scripts/quality-gate.sh all`, Edge ile canlı senaryo.
