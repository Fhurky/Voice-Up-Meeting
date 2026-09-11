# Koşum raporu — 2026-09-11 · Yerel başlatmada değişen backend adresinin nginx tarafından yenilenmesi.

1. Sonuç: Yerel başlatmanın eski backend adresine HTTP 502 vermesi için düzeltme doğrulandı — birim 14 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Başlatıcı L1; gerçek geçici nginx/backend ağı L2.
2. Koşulan: Windows PowerShell 5.1 ve yerel Docker Desktop; `kt-vibecoding-python-web-v2`.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `pytest tests/test_spark_startup.py -k local_refreshes -q` | Düzeltmeden önce 2/2 başarısız: Local branch nginx reload çağırmıyordu. |
   | `RUN_DOCKER_TRANSPORT=1 pytest 'tests/test_spark_transport_config.py::test_nginx_reload_refreshes_replaced_backend_and_checks_active_private_config[local]' -q` | Düzeltmeden önce 1/1 başarısız: başlatıcıda Local reload komutu yoktu. |
   | `pytest tests/test_spark_startup.py -k 'local_refreshes or meeting or nginx or explicit_local or powershell_file' -q` | Düzeltme sonrası 12/12 başarılı; başarı/hata, doğru Compose proje kimliği, Local/Spark ayrımı, meeting overlay ve BOM korunması. |
   | `RUN_DOCKER_TRANSPORT=1 pytest tests/test_spark_transport_config.py::test_nginx_reload_refreshes_replaced_backend_and_checks_active_private_config -q` | Local ve Spark için gerçek Docker ağında 2/2 başarılı; değiştirilmiş backend IP'sinde önce gerçek 502/504, reload sonrası yeni backend yanıtı. |
   | `ruff check tests/test_spark_startup.py tests/test_spark_transport_config.py` | Başarılı; `start-local.ps1` UTF-8 BOM byte kontrolü başarılı. |

3. Maddeler:

   **KUSUR**
   M1 `start-local.ps1` yalnız Spark modunda nginx'i yeniden yüklüyordu; yerel backend yeniden oluşturulunca çalışan nginx eski IP'yi tutabiliyordu. Local moda `nginx -t` ardından bounded `nginx -s reload` eklendi.
   **TUZAK**
   M2 Local standart nginx config'i, Spark kendi tmpfs içindeki tek aktif config'i kullanır. Hatalı config veya reload durumunda seçili mod korunur, hazır URL yazılmaz; ham özel stderr kullanıcıya aktarılmaz.
   **GÖZLEM**
   M3 Gerçek taşıma testi iki ayrı backend IP'si ve geçici nginx ile kaynakta yazılı reload komutunu aynen yürütür; geçersiz config yenilemeyi reddederken önceki çalışan proxy korunur.
   **AÇIK**
   M4 Ana tam kalite kapısı bu kaynak değişikliğinden önce başlamıştı; bütünleşik teslim için tekrar koşulmalıdır. Bu alt koşum modelin metin/hafıza doğruluğunu veya PowerShell 7 uyumunu ölçmez.
   **YAN-ETKİ**
   M5 Başlatıcı ve iki ilgili test dosyası güncellendi; yalnız testin oluşturduğu geçici konteyner/ağlar temizlendi. Çalışan uygulamanın nginx kurtarma restart'ı ana ajan tarafından ayrı yapıldı.
   M6 RED/GREEN XML kayıtları Git dışı `outputs/2026-09-10-meeting-delivery/local-reload-*.xml` altında tutulur.
