# Plan — Ayarlar menüsü ve işlemci seçimi

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Çıkarım | `app/inference/voiceup_inference/runtime.py`, `api.py` | Decision 2, 3, 4; Requirement 1 |
| Arka uç | `meeting_inference.py`, `api/meetings/router.py`, `schemas/meeting.py`, `core/config.py` | Decision 1, 7; Requirement 2 |
| Kompozisyon ve başlatma | `docker-compose.local.yml`, `docker-compose.meeting-cpu.yml`, `scripts/start-local.ps1` | Decision 5, 6 |
| Sözleşme | `specs/openapi`, `app/frontend/src/types/api.d.ts` | Requirement 2 |
| Ön yüz | `pages/SettingsPage.tsx`, `SpeakerLayout.tsx`, `SpeakerPages.tsx`, `generated/routes.tsx`, TR/EN kataloglar | Decision 1, 3, 4, 5; Requirement 3 |
| Tarayıcı | `e2e/speaker-identity/17-settings-processor.mjs` | Requirement 4 |

Doğrulama: `test_processor_switch.py`, `test_meeting_processor.py`, `SettingsPage.test.tsx`, `scripts/quality-gate.sh all`, canlı senaryo.
