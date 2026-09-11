# Koşum raporu — 2026-09-11 · Son model deneyinden sonra yerel uygulamanın geri açılması

1. Sonuç: Aynı yerel model servisi geri açıldı; özel model ve genel veritabanı hazır olma uçları gerçek HTTP 200 döndürdü — birim 0 başarılı / canlı HTTP 2 başarılı / servis komutu 2 başarılı / boş iş kuyruğu denetimi 1 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; mevcut Windows/Git Bash/Docker, RTX 4060 ve yerel FastAPI/PostgreSQL. 190 klibin çıkarımı, puanlaması ve son kaynak sabitleme denetimi tamamlandıktan sonra gerçek salt okunur veritabanı sorgusu aktif toplantı 0 ve aktif ses işi 0 döndürdü. `scripts/stack.sh --mode local stop inference` çıkış 0; ayrı bütün-kayıt deneyi bitince `scripts/start-local.ps1 -Mode Local` çıkış 0, 58,89 saniye. Son kontrol 11:11:18 UTC'de backend üzerinden özel `/meeting-ready` ve dışarıdan `http://127.0.0.1:8081/api/voiceup/v1/readiness` uçlarını çağırdı. Ham kayıtlar `outputs/2026-09-11-accuracy-audit/whole-recording-community-v1/runtime-coordination/` içindedir.
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Model hazır olma ucu yalnız kimlik ve cihaz bilgisini doğrular; bu iki GET isteği yeni konuşma doğruluğu ölçümü değildir. İmaj kaynak eşleşmesi, önceki gerçek deneyler ve tamamlanma sabitlemeleri ayrı kanıtlardır.
   **GÖZLEM**
   M2 Aynı konteyner `d17764af…` ve imaj `sha256:d14a4e65159af176eac50fe20334e49f64bdb199baa220d6ed36cb2edab0ef57` yeniden çalışıyor; başlangıç 11:08:02 UTC, Docker sağlığı `healthy`, cihaz `cuda:0`.
   M3 Hazır olma yanıtı aynı Community-1/Fa.15, Whisper large-v3 ve ECAPA192 model sürümlerini döndürdü; uygulama adresi `http://127.0.0.1:8081` ve veritabanı hazırdır.
   **AÇIK** — yok
   **YAN-ETKİ**
   M4 Yalnız model servisi geçici durdurulup mevcut wrapper ile geri açıldı; inceleme sırasında yeni kayıt/profil yazılmadı. Özel ham komut ve durum belgeleri ignore edilen dizine kaydedildi; bu kontroller ana 2.035 otomatik test toplamına eklenmedi.
