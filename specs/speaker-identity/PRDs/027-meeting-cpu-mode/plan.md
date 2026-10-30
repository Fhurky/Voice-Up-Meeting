# Plan — Toplantıları CPU'da çalıştırma

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Çıkarım | `app/inference/voiceup_inference/config.py`, `models.py`, `meeting_models.py` | Decision 2; Requirement 1 |
| Arka uç | `meeting_ports.py`, `meeting_inference.py`, `core/config.py`, `api/meetings/router.py`, `schemas/meeting.py` | Decision 3, 4; Requirement 2 |
| Sözleşme | `specs/openapi`, `app/frontend/src/types/api.d.ts` | Requirement 2 |
| Ön yüz | `services/meetings.ts`, `MeetingUploadForm.tsx`, TR/EN kataloglar | Decision 4; Requirement 3 |
| Açılış | `app/infra/docker-compose.meeting-cpu.yml`, `scripts/start-local.ps1`, `scripts/stack.sh` | Decision 1, 3; Requirement 4 |
| Değerlendirme | `scripts/experiment_ledger.py`, `scripts/evaluate-expanded-turkish-asr.py` | Decision 5; Requirement 5 |

Doğrulama: `app/inference/tests`, arka uç ve ön yüz testleri, `scripts/quality-gate.sh all`, GPU gizlenerek AMI toplantısı.
