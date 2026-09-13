# Koşum raporu — 2026-09-13 · Model seçimi, görünür öneri ve kayıt arayüzü

1. Sonuç: İlk arayüz ve hizmet paketi geçti — birim 60 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Linux frontend konteynerinde `scripts/stack.sh exec -T frontend npm test -- src/services/meetings.test.ts src/components/MeetingTextReview.test.tsx src/components/MeetingResults.test.tsx src/locales/catalogues.test.ts`; 60 başarılı, çıkış 0.
3. Maddeler:

   **KUSUR**
   M1 Yeni model listeleme/seçim/kayıt sözleşmeleri uygulandı; [önceki kırmızı koşum](frontend-red-report.md) yeşil.

   **TUZAK**
   M2 012 UI testleri, kabul edilmiş 013 genişlemesine göre açık model seçimi ve tüm önerileri gösterme davranışını sınar; eski API testi korunur.

   **GÖZLEM**
   M3 StrictMode tek model liste isteği, açık kontrol, semantik önerilerin yeşil gösterimi, ham HTML metni, uyuşmayan kaynak/model/sürüm ve idempotent save retry gözlendi.

   **AÇIK**
   M4 Kaydedilen sonuç bileşeni ve read-only/reload testleri, üretilmiş tiplerle build ve gerçek tarayıcı bu ilk koşuma dahil değildir.

   **YAN-ETKİ**
   M5 Arayüz, hizmet, katalog ve test fixture'ları değişti; kalıcı kullanıcı verisi veya modeller kullanılmadı.
