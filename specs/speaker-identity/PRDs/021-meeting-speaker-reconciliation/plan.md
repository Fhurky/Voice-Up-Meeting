# Plan — Toplantı sonunda konuşmacı birleştirme

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Alan | `app/backend/app/domain/meeting_reconciliation.py` | Decision 2, 5; Requirement 1 |
| Servis | `app/backend/app/services/meeting_chunks.py` (`reconcile`, `TrackRebuild`, `persist(rebuild=)`) | Decision 2, 4, 5 |
| Worker | `app/backend/app/services/meeting_worker.py` (`reconcile`) | Decision 1; Requirement 2 |
| Depo | `app/backend/app/infrastructure/repositories/meeting_repository.py` (`retire_transcript`) | Decision 4 |
| Ayar | `app/core/config.py`, `.env.example`, `docker-compose.local.yml` | Decision 3; Requirement 3 |
| API | `app/backend/app/services/meeting_service.py` (`rename`) | Decision 6; Requirement 6 |
| Ön yüz | `MeetingResults.tsx`, `meetingErrors.ts`, TR/EN kataloglar | Decision 6; Requirement 6 |
| Araç | `scripts/replay-meeting-reconciliation.py` | Decision 3; Requirement 4 |
| Ölçüm | `scripts/run-ami-evaluation.py` (değişmez), yeni `eval-ami3-*` tenant'ları | Requirement 5 |

Şema, OpenAPI şekli ve göç değişmez: yeni alan yok, hata kodu mevcut zarfla döner.

Doğrulama: `pytest tests/unit/test_meeting_reconciliation.py`,
`RUN_POSTGRES_INTEGRATION=1 pytest tests/integration/test_meeting_reconciliation.py`,
`tests/test_replay_meeting_reconciliation.py`, `scripts/check-config-sync.py`,
`scripts/quality-gate.sh all`, 015 protokolüyle gerçek ölçüm.
