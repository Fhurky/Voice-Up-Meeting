# Koşum raporu — 2026-09-09 · özel Spark nginx aktarım katmanı

1. Sonuç: Uzak Compose modeli ve geçici proxy üzerinden gerçek HTTP denetimleri başarılı — birim 6 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows Python ve Docker Desktop; son canlı koşum 12,13 saniye.

   | Denetim | Komut veya kapsam | Gözlenen sonuç |
   | --- | --- | --- |
   | Gerçek Compose modeli | `tests/test_spark_transport_config.py`: yerel, uzak ve bütün profiller açık çözümlemeler | 5 test başarılı; yalnız test ortam değerleri kullanıldı |
   | Canlı taşıma | `RUN_DOCKER_TRANSPORT=1 python -m pytest tests/test_spark_transport_config.py -s` | 1 canlı test başarılı; toplam paket 6 başarılı |
   | Nginx sözdizimi | Mevcut public conf ile yeni özel conf birlikte bağlanan geçici konteyner içinde `nginx -t` | Çıkış 0; 21 HTTP denetimi bu birleşik yapılandırmayla tekrar geçti |
   | Host eşlemesi | `voiceup-spark-host:host-gateway`, geçici konteynerin `/etc/hosts` kaydı | Bir IPv4 ve bir IPv6 kaydı; adres aileleri ayrı ayrıştırıldı |
   | Tekrarlı hazır kontrolü | Mevcut worker → geçici özel nginx → Windows `127.0.0.1:18090` | 12 GET isteğinde HTTP 200 ve doğru nonce |
   | POST aktarımı | `/v1/embeddings?purpose=identify`, yalnız teknik metin gövdesi | Sorgu, gövde, `X-Inference-Key`, `X-Job-Id`, `X-Tenant-Id` aynen korundu |
   | Yöntem ve yol sınırı | HEAD/POST `/ready`; GET/PUT `/v1/embeddings`; iki ilgisiz yol | İlk dört istek 405, son iki istek 404; üst hedefe ulaşmadı |
   | Boyut sınırı | 51 MiB sınırından büyük `Content-Length` | 413; üst hedefe ulaşmadı |
   | Kopma | Yalnız test HTTP dinleyicisi kapatıldıktan sonra GET | 6 saniyeden kısa sürede 502; başka hedefe dönüş yok |
   | Log sınırı | Geçici nginx logları | Test anahtarı ve metin gövdesi görünmedi |
   | Statik | `python -m ruff format/check tests/test_spark_transport_config.py` | Biçim ve lint başarılı |
   | Ayar yüzeyleri | `python scripts/check-config-sync.py` | `ok: true`; 29 typed ayar, 26 Compose ortam anahtarı |
   | Bağımlılık kabulü | `python scripts/check-dependency-admission.py` | Güncel 119 koordinat; `abf1a5d81b9344531dd52f334a62404b4a49955831ad3b4504760fe320102ba9` |

3. Maddeler:

   **KUSUR**

   M1 İlk kırmızı koşumda uzak Compose dosyası eksikti: 5 kurulum hatası. Katman eklendikten sonra 5 model testi geçti.

   M2 İlk iki canlı koşumda test düzeneği başlatma ve netcat yanıt okuma sorunları yaşadı; geçici nginx UID/GID 101 ile, istemci mevcut worker içindeki standart HTTP istemcisiyle çalıştırıldı. Son canlı koşum geçti.

   **TUZAK**

   M3 Compose profili otomatik başlatmayı engeller; açıkça `inference` servisinin hedeflenmesi veya profil etkinleştirilmesi ayrı başlatıcı kontrolü gerektirir. Mevcut çalışan yerel inference bu katman yazılırken durdurulmadı.

   M4 `host-gateway` iki adres ailesi üretir. Önceki tek satır varsayımı bu testte kullanılmadı; sayısal Docker host adresi kaynak dosyaya sabitlenmedi.

   **GÖZLEM**

   M5 `docker-compose.spark.yml`, backend/worker/migrate için mevcut `VOICEUP_INFERENCE_URL` değerini `http://nginx:9080` yapar; yeni uygulama ayarı, bağımlılık veya image pini eklemez.

   M6 Backend, worker ve veri servisleri yalnız `internal: true` ağında kalır. Nginx mevcut default+edge bağlantısını kullanır; 9080 portu yayımlanmaz ve 8080 üzerindeki mevcut public yapılandırma korunur.

   M7 Yeni listener yalnız GET `/ready` ve POST `/v1/embeddings` aktarır; access log kapalı, bağlantı süresi 3 saniye, okuma/yazma 300 saniye, request buffering kapalı ve upstream retry kapalıdır.

   M8 Canlı deneme 21 HTTP denetimi içerir. Kullanılan gövdenin SHA-256 değeri `b85d83e92a5796ecfb32e599d89ae077c0ed4f1275ed20e99cd3d963561c12c8`; gövde ses veya model sonucu değildir.

   **AÇIK**

   M9 Bu koşum SSH tüneli, Spark HTTP servisi, gerçek model çıkarımı veya uygulama işinin Spark üzerinde tamamlanmasını doğrulamaz. Uzak katman çalışan uygulamada henüz etkinleştirilmedi.

   M10 Tam uygulama kalite ve güvenlik kapıları bu alt görevde yeniden çalıştırılmadı; bunlar 004 yeteneğinin bütün katmanları birleştirildiğinde ayrıca raporlanmalıdır.

   **YAN-ETKİ**

   M11 Yalnız uzak Compose katmanı, nginx conf, odaklı test ve bu rapor eklendi. `start-local.ps1`, `stack.sh`, yerel Compose ve mevcut public nginx conf değiştirilmedi.

   M12 Teste ait proxy, mevcut ağlara geçici üye olarak bağlandı; test sonunda kaldırıldı ve loopback dinleyicisi kapatıldı. Mevcut konteynerler yeniden başlatılmadı; hiçbir model veya kullanıcı sesi işlenmedi.
