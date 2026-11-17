# Plan — Tüm kayıtta tek geçişte konuşmacı ayırma

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Çıkarım: model | `app/inference/voiceup_inference/meeting_models.py` (tarif seçimi, tüm kayıt çağrısı) | Decision 1; Requirement 1 |
| Çıkarım: analiz | `meeting_runtime.py` (verilen aralıklarla parça analizi), `runtime.py`, `api.py` | Decision 4; Requirement 1, 2 |
| Arka uç: şema | `app/backend/app/domain/models/meeting.py` (`MeetingDiarization`), `schema/alembic/versions/` | Decision 3; Requirement 3 |
| Arka uç: sözleşme | `app/backend/app/services/meeting_ports.py` (tarif kimliği, tüm kayıt sonucu), `infrastructure/meeting_inference.py` | Decision 1, 4; Requirement 3 |
| Arka uç: ses | `app/backend/app/infrastructure/meeting_audio.py` (16 kHz tek kanal okuyucu) | Requirement 4 |
| Arka uç: akış | `services/meeting_worker.py` (tek geçiş adımı, geri dönüş), `services/meeting_chunks.py` (etiketle bağlama, birleştirmeyi atlama), `infrastructure/repositories/meeting_repository.py`, `services/meeting_cleanup.py` | Decision 2, 5, 6, 7; Requirement 3 |
| Gözlemlenebilirlik | `services/meeting_worker.py` | Requirement 5 |
| Ölçüm | `scripts/run-ami-evaluation.py` (yalnız `test` bölümü seçeneği), `results.md` | Requirement 6 |
| Dağıtım | `app/devops/charts/app-inference/values.yaml` (yalnız ölçüm gerektirirse) | Requirement 6(a) |

Doğrulama: `app/inference/tests`, `app/backend/tests` (birim ve `RUN_POSTGRES_INTEGRATION=1`), `scripts/quality-gate.sh all`,
ürün akışıyla AMI ve Türkçe ölçüm, `16-meeting-mp4-upload.mjs`.
