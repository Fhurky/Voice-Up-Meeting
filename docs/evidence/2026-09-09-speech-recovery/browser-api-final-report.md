# Koşum raporu — 2026-09-09 · Tamamlanan tarayıcı işlerinin son API ve profil korunum kontrolü

1. Sonuç: Beş sonlanmış işin beklenen durumları ve negatif denemeler sonrası tam profil yanıtı doğrulandı — birim 0 başarılı / tarayıcı 0 başarılı / canlı kontrol 20 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel FastAPI uygulamasına mevcut `benchmark-local-pilot.py#Api` ile 1 giriş ve 2 GET; [anonim son API kaydı](browser-api-final.json). Asıl tarayıcı akışları ana ajanın ayrı tarayıcı raporundadır.
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Sonlanan 2 başarısız iş beklenen negatif sonuçlardır: yanlış kişiye ekleme `target_mismatch`, yetersiz konuşmalı tanıma `insufficient_speech`; bu iki sonuç başarı kaydı gibi değerlendirilmedi.

   **GÖZLEM**

   M2 Kayıt, bilinen tanıma ve bilinmeyen tanıma işleri başarılıydı; işlem sürümleri sırasıyla `vad-windows-v1`, `vad-packed-fallback-v1`, `vad-packed-fallback-v1`. Beş işin her biri tek denemede sonlandı.

   M3 Kayıt ve tanınan sorgu beklenen profile bağlıydı; bilinmeyen sorgu profile bağlanmadı. Başarısız işlerin başarı sonucu alanları boştu.

   M4 Negatif denemelerden sonra 1 profil ve 1 örnek kaldı; genel profil yanıtının tüm alanları başlangıç görüntüsüyle aynıydı. İki kanonik yanıt hashı da `62155803f73fad96238737358aea094919cc5d98c2f3e2fa1a4a362d28033ffa`.

   **AÇIK**

   M5 Bu sonuç tarayıcı test hesabını kapsar; özgün kullanıcı ve diğer konteynerlerin son açılış sonrası genel korunum kontrolü ayrı talimatı beklemektedir.

   M6 API yanıtı eşitliği özel vektörlerin veya bütün veritabanı baytlarının eşitliği değildir; bu ajan tarayıcı işlemlerini gerçekleştirdiğini iddia etmez.

   **YAN-ETKİ**

   M7 Yalnız giriş ve GET yapıldı; yeni iş, ses yükleme, hesap veya profil değişikliği yapılmadı. Ham gözlemler özel çıktı dizininde kaldı; kimlik, ses, vektör veya tekil kalite sayıları yayımlanmadı.
