# Plan — Toplantı katılımcı listesi

1. Requirement 1: `app/backend/app/domain/models/meeting.py` içinde `MeetingParticipant`;
   `scripts/db.sh generate meeting_participant_roster`, migration incelemesi, yerel
   `apply/validate/status`.
2. Requirement 2: `speaker_repository` liste kısıtlı/liste dışı sorgular;
   `meeting_memory` karar akışı (Decision 2–3); `meeting_service` oluşturma ve sayı
   ipucu (Decision 4). Önce kırmızı birim ve gerçek PostgreSQL testleri.
3. Requirement 3: `schemas/meeting.py`, `api/meetings/router.py`, hata eşlemesi;
   `scripts/export-openapi.sh`, `scripts/generate-types.sh`.
4. Requirement 4: `services/meetings.ts`, `MeetingUploadForm`, `MeetingMicrophoneRecorder`,
   `MeetingPage`; TR/EN katalogları; vitest ve `e2e/speaker-identity` senaryosu.
5. Requirement 5: 015 hattıyla AMI listeli/listesiz eşlenmiş koşum; `results.md`.
6. Tam kalite kapısı, canlı tarayıcı doğrulaması ve koşum raporu.
