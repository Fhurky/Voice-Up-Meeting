# Koşum raporu — 2026-09-10 · İzole CPU ile gerçek kayıt ve tanıma

1. Sonuç: Gerçek CPU modeliyle kayıt ve aynı sesin tanınması geçti; profil belleği değişmedi — birim 1 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows Docker Desktop, Linux amd64 CPU modeli ve backend Python 3.13.

   | Koşum | Gözlenen sonuç |
   |---|---|
   | `tests/live/cpu_application.py`, ilk girişim | 1 hazırlık hatası; [XML](cpu-application-first-results.xml) |
   | Aynı dosya, düzeltilen kabuk argümanları | 1 başarılı, 0 başarısız, 0 atlanan; 7,42 saniye; [XML](cpu-application-results.xml), [çıktı](cpu-application-pytest.txt) |
   | Mevcut `db.sh apply` ve `db.sh validate`, yalnız özgün `*_test` veritabanı | Başarılı; [migration çıktısı](cpu-application-migrations.txt) |
   | Temizlik ve mevcut uygulama karşılaştırması | Geçici konteyner/veritabanı/dosyalar kaldırıldı; mevcut konteyner başlangıçları, `.env` ve mod dosyası değişmedi; [JSON](cpu-application.json) |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Birleşik oluşturma/koşum/temizlik komutu otomatik onay incelemesince işlem başlamadan reddedildi; ayrı hedef doğrulaması ve dar işlemler onaylandı.
   M2 Git Bash ilk `--basetemp=/tmp/...` argümanını Windows yoluna çevirdi; yol seçenekleri ayrı argüman yapılıp yalnız ilgili önekler dönüşümden çıkarılınca aynı kaynak geçti.

   **GÖZLEM**
   M3 `HttpEmbeddingAdapter` ve `SpeakerWorker` gerçek modele TCP üzerinden ulaştı: kayıt 2,148 saniye, tanıma 2,089 saniye; iki model isteği 200 ve `device=cpu` döndü.
   M4 Kayıt 26,886 saniye konuşma ve 5 pencere kullandı; tanıma aynı profili buldu, profil/örnek sayısı 1 kaldı ve saklanan vektör değişmedi; tamamlanmış kayıt tekrarı aynı işi döndürdü.
   M5 Aynı kamuya açık 30 saniyelik ses iki işlemde kullanıldı; bu sonuç bağımsız konuşmacı doğruluğu veya kalabalık kayıt başarısı değildir.

   **AÇIK**
   M6 Genel uygulama rotaları JWT/yetki/serileştirmeyle `ASGITransport` içinde çalıştı; genel API için TCP/nginx/tarayıcı ve gerçek MacBook kurulumu bu koşumda doğrulanmadı.

   **YAN-ETKİ**
   M7 Kalıcı açık çağrımlı test ve bu kanıt dosyaları eklendi; test dosyasının adı varsayılan `test_*.py` keşfine girmez.
   M8 `voiceup-cpu-live-260910e23a89`, `voiceup_cpu_live_260910e23a89_test` ve yalnız bu nonce'a ait geçici/yanlış çevrilen dosyalar sahiplik denetimi sonrası temizlendi; mevcut uygulama verisi ve sırları korunmuştur.
