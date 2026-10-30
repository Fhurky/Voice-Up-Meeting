# Plan — Toplantı ön girdileri

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Şema | `app/backend/app/domain/models/meeting.py`, `app/db/base.py`, Alembic göçü | Decision 3; Requirement 1 |
| Şema sözleşmesi | `app/backend/app/schemas/meeting.py` | Decision 1, 3, 4; Requirement 2 |
| Depo ve servis | `meeting_repository.py` (`questions`), `meeting_service.py` | Decision 3, 4; Requirement 2 |
| Worker | `meeting_worker.py` (`claim`) | Decision 2, 5; Requirement 3 |
| Sözleşme | `specs/openapi`, `app/frontend/src/types/api.d.ts` | Requirement 2 |
| Ön yüz | `MeetingUploadForm.tsx`, `MeetingPage.tsx`, TR/EN kataloglar, `globals.css` | Decision 1, 2, 4; Requirement 4 |
| Tarayıcı | `e2e/speaker-identity/15-meeting-context-inputs.mjs`, `04`, `05` | Requirement 4 |

Doğrulama: `tests/integration/test_meeting_context_inputs.py`, `test_meeting_worker.py`,
`MeetingUploadForm.test.tsx`, `MeetingPage.test.tsx`, `scripts/db.sh validate`,
`scripts/quality-gate.sh all`, canlı tarayıcı senaryosu TR/EN 390 ve 1440 px.
