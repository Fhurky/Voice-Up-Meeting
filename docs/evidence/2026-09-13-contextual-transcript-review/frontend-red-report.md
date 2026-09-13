# Koşum raporu — 2026-09-13 · Bağlamsal metin incelemesi arayüzünün kırmızı testi

1. Sonuç: Yeni davranışın iki eksiği gözlendi — birim 16 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows ana makineden mevcut `scripts/stack.sh` ile Linux frontend konteynerinde `npm test -- src/services/meetings.test.ts src/components/MeetingResults.test.tsx`; 18 test, 2 başarısız, çıkış 1. Profil `kt-vibecoding-python-web-v2`.
3. Maddeler:

   **KUSUR**
   M1 `MeetingService.correctionPreview` henüz yok; kimliklerle gövdesiz istek sözleşmesi testi başarısız.
   M2 `MeetingResults` inceleme eylemini henüz sunmuyor; erişilebilir düğme testi başarısız.

   **TUZAK** — yok

   **GÖZLEM**
   M3 Önceden var olan 16 hizmet ve sonuç testi başarılı.

   **AÇIK**
   M4 Gerçek tarayıcı ve model bu dar koşumda çalıştırılmadı.

   **YAN-ETKİ**
   M5 İki mevcut test dosyasına Accepted 012 davranışını tarif eden regresyonlar eklendi; iş verisi değişmedi.
