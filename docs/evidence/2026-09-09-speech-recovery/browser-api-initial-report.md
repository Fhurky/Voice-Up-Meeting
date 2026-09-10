# Koşum raporu — 2026-09-09 · Tarayıcı akışının ilk genel API doğrulaması

1. Sonuç: Tarayıcı hesabının kayıt ve tanıma sonuçları salt okunur API görüntüsüyle doğrulandı — birim 0 başarılı / tarayıcı 0 başarılı / canlı kontrol 5 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Mevcut `benchmark-local-pilot.py#Api` ile yerel FastAPI uygulamasına 1 giriş, 2 GET; [anonim sonuç](browser-api-initial-corroboration.json). Tarayıcıyı başka ajan işletti; bu rapor arayüz kullanımını üstlenmez.
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Genel iş API'sinde işlem sürümü `result.preprocessing_version` alanındadır; iç çıkarım yanıtının `quality.preprocessing_version` yolu burada kullanılmaz.

   **GÖZLEM**

   M2 1 profil ve 1 örnek görüldü; ilk kayıt başarılı ve `vad-windows-v1`, tanınan sorgu doğru profile bağlı ve `vad-packed-fallback-v1` idi. Bilinmeyen sorgu hiçbir profile bağlanmadı.

   M3 Yanlış kişiye ekleme denemesi öncesindeki tam profil API yanıtı özel anlık görüntü olarak saklandı; başlangıç dosyası SHA256 `7ab2502ee417448f759f9eaf4786ae48514ab254399773f5955146af64142053`.

   **AÇIK**

   M4 Bu görüntü yanlış kişiye ekleme ve kalan negatif denemeler sonrasındaki profil korunumunu göstermez; tamamlanma sonrası karşılaştırma henüz yapılmadı.

   **YAN-ETKİ**

   M5 Yalnız giriş ve GET yapıldı. Ham iş/profil yanıtları özel çıktı dizininde kaldı; kimlik, ses, vektör veya tekil kalite sayıları yayımlanmadı.
