# Plan — Konuşmacı ve sürdürülen yüklemelerde MP4

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Ses çıkarma | `app/frontend/src/lib/mediaAudio.ts` | Decision 1, 2; Requirement 1 |
| Konuşmacı formu | `components/AudioJobForm.tsx`, `lib/speakerErrors.ts` | Decision 2, 4; Requirement 2 |
| Sürdürme paneli | `components/MeetingSourceUpload.tsx` | Decision 3, 4; Requirement 3 |
| Metinler | `locales/tr.json`, `locales/en.json`, `README.md` | Decision 5 |
| Tarayıcı | `e2e/speaker-identity/18-speaker-mp4-upload.mjs`, `04-meeting-upload.mjs` metni | Requirement 4 |

Doğrulama: `mediaAudio.test.ts`, `AudioJobForm.test.tsx`, `MeetingSourceUpload.test.tsx`, `scripts/quality-gate.sh all`, canlı senaryo.
