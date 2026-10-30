# Görevler — Toplantıları CPU'da çalıştırma

- [x] T01 Çıkarım servisi profili ve testleri (Requirement 1).
- [x] T02 Arka uç ve sözleşme (Requirement 2).
- [x] T03 Ön yüz uyarısı (Requirement 3).
- [x] T04 Açılış ve belgeler (Requirement 4).
- [x] T05 Tam kalite kapısı (30 Ekim 2026: arka uç 941/941, ön yüz /, tüm adımlar geçti).
- [x] T06 Gerçek CPU koşumu ve GPU ile karşılaştırma (Requirement 5).
- [ ] T07 GPU'suz makinede ilk kurulum (L3).

30 Ekim 2026 ölçüm kanıtı: GPU görünmeyen konteynerde (16 fiziksel, 32 mantıksal çekirdek) 14 dakikalık `IS1009a` toplantısı 618,6 saniyede işlendi
(gerçek zamanın 0,74'ü); çalışırken 11–15 çekirdek kullanıldı. Konuşmacı puanları GPU sonucuyla üç ondalığa kadar aynı. Metin birebir aynı değil: 1613 ve 1615
kelimede %94,18 benzerlik; hangisinin daha doğru olduğu ölçülmedi. Daha az çekirdekli makinelerde süre daha uzun olur, ölçülmedi.

Bulgu: Whisper'a mantıksal çekirdek sayısı verilince iş 2,3 çekirdekte kaldı ve 2 dakikalık klip 310 saniye sürdü; fiziksel çekirdek sayısıyla 30 saniye.
