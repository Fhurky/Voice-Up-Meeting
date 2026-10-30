# Görevler — Toplantı ön girdileri

- [x] T01 Şema otoritesi ve göç: `meeting.subject`, `meeting_question` (Requirement 1).
- [x] T02 Şema sözleşmesi, servis, depo ve entegrasyon testleri (Requirement 2).
- [x] T03 Worker: tahmini sayı modele gitmez, en çok sayı üst sınırdır (Requirement 3).
- [x] T04 OpenAPI ve ön yüz tipleri (Requirement 2).
- [x] T05 Form, sonuç ekranı, TR/EN metinler ve birim testleri (Requirement 4).
- [x] T06 Kalıcı tarayıcı senaryosu ve canlı geçiş (Requirement 4).
- [x] T07 Tam kalite kapısı (30 Ekim 2026: arka uç 930/930, ön yüz 264/264, tüm adımlar geçti).
- [x] T08 Kullanıcı kabulü (L3): 30 Ekim 2026, kullanıcı ekranları inceledi, "şimdilik yeterli".

30 Ekim 2026 kanıtı: `tests/integration/test_meeting_context_inputs.py` 15/15, ön yüz birim 264/264;
`15-meeting-context-inputs.mjs` canlı yığında sıradan rolle TR 1440 px ve EN 390 px geçti, ekran görüntüsü
incelendi. Göç `fb45c4da9ca3` yalnız ekleme yapar; çalışma rolünün yeni tablodaki yetkisi doğrulandı.
