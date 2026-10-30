# Plan — Okunabilir metin satırları

| Katman | Dosya | Karşıladığı |
|---|---|---|
| Alan | `app/backend/app/domain/meeting_timeline.py` (`align_words`) | Decision 1, 2; Requirement 1 |
| Test | `app/backend/tests/unit/test_meeting_timeline.py` | Requirement 1 |

Doğrulama: birim testleri, `scripts/quality-gate.sh all`, kayıtlı parça sonuçlarıyla iki Türkçe kaydın yeniden işlenmesi.
