# Koşum raporu — 2026-09-13 · Geliştirme modunda yinelenen metin inceleme isteği

1. Sonuç: Canlı akışta gözlenen yinelenen istek testte yeniden üretildi — birim 20 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows üzerinden mevcut Linux frontend konteynerinde `scripts/stack.sh exec -T frontend npm test -- src/components/MeetingTextReview.test.tsx`; 21 test, 1 başarısız, çıkış 1.
3. Maddeler:

   **KUSUR**
   M1 Gerçek `StrictMode` altında tek seçim iki `correctionPreview` çağrısı üretiyor; ilk sinyal iptal olsa da pahalı sunucu çağrısı başlatılmış oluyor.

   **TUZAK**
   M2 Geliştirme modunun effect setup/cleanup/setup denetimi korunmalı; StrictMode kapatılmamalı veya inceleme sonucu önbelleğe alınmamalı.

   **GÖZLEM**
   M3 Önceden var olan kaynak/hash/yerelleştirme/iptal/retry kontrollerinin 20'si geçti.

   **AÇIK**
   M4 Bu dar test gerçek model veya tarayıcı HTTP koşumu değildir; düzeltme sonrası canlı çağrı sayısı ayrıca gözlenmeli.

   **YAN-ETKİ**
   M5 `MeetingTextReview.test.tsx` dosyasına gerçek React StrictMode regresyonu eklendi; model ve iş verisi değiştirilmedi.
