# Koşum raporu — 2026-09-09 · Tek komut başlatıcısında nginx adres yenileme ve UTF-8 aktarım regresyonları

1. Sonuç: Sabit `kt-vibecoding-python-web-v2` profilinde gözlenen iki başlatma kusuru düzeltildi; bu kapsamda 100 benzersiz otomatik vaka geçti — birim 100 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kontrol | Ortam / komut | Sonuç |
   | --- | --- | --- |
   | nginx değişiklik öncesi | Windows Python 3.13.14, PowerShell 5.1 ve 7.6.5; `pytest tests/test_spark_startup.py -k 'refreshes_nginx or nginx_reload_failure' -q -o addopts=` | 4 beklenen hata; [çıktı](nginx-reload-red.txt), [JUnit](nginx-reload-red.xml) |
   | Başlatma ve yerel konfigürasyon | Aynı Python; `pytest tests/test_spark_startup.py tests/test_connect_spark.py tests/test_local_configuration.py -q -o addopts=` | Başlatma 51 ve yerel konfigürasyon 4 başarılı; koordinatör 39 başarılı / 1 stdin hatası. Sonraki satır koordinatör sonucunu tamamlar; [çıktı](nginx-reload-startup.txt), [JUnit](nginx-reload-startup.xml) |
   | stdin değişiklik öncesi | İki PowerShell sürümü; `pytest tests/test_connect_spark.py -k native_stdin_is_utf8 -q -o addopts=` | 3 beklenen hata / 1 başarılı; [çıktı](native-stdin-red.txt), [JUnit](native-stdin-red.xml) |
   | Son koordinatör paketi | Windows Python 3.13.14; `pytest tests/test_connect_spark.py -q -o addopts=` | 44 başarılı / 0 atlanan; [çıktı](native-stdin-connect.txt), [JUnit](native-stdin-connect.xml) |
   | Gerçek nginx adres değişimi | Mevcut sabit nginx imajı, ayrı iç Docker ağı; `RUN_DOCKER_TRANSPORT=1 pytest tests/test_spark_transport_config.py -k nginx_reload_refreshes -q -o addopts=` | 1 başarılı / 13 seçilmeyen; [çıktı](nginx-reload-docker.txt), [JUnit](nginx-reload-docker.xml) |
   | Kaynak biçimi | Mevcut backend Ruff; üç değişen kök test dosyasında `ruff check` ve `ruff format --check`; kapsamlı `git diff --check` | Başarılı; iki PowerShell dosyası UTF-8 BOM'unu koruyor. |

3. Maddeler:

   **KUSUR**
   M1 Compose backend'i değiştirince nginx eski IP'ye istek gönderiyordu. `start-local.ps1` yalnız aynı projenin nginx servisinde etkin Spark konfigürasyonunu sınayıp yeniden yükler; yeni backend ve private dinleyici gerçek izole nginx ile doğrulandı. DÜZELTİLDİ.
   M2 Yerel konsol kod sayfası native stdin'i değiştiriyor; PowerShell 5.1 UTF-8 BOM ekleyebiliyordu. `connect-spark.ps1` BOM'suz UTF-8 seçer; Türkçe baytlar ve süreç açılışı başarı/hatası sonrası konsol koruması iki PowerShell sürümünde test edildi. DÜZELTİLDİ.

   **TUZAK**
   M3 Eski IP bağlantıyı reddederse 502, cevap vermezse 504 oluşabilir. İlk Docker denemesinin yalnız 502 beklentisi düzeltildi; [ilk çıktı](nginx-reload-docker-initial.txt) korunur.
   M4 Spark etkin konfigürasyonu `/tmp/voiceup-spark.*/nginx.conf` içindedir; varsayılan nginx dosyasını sınamak private include hatasını kaçırır. Bozuk include, eksik veya birden çok etkin dosya yeniden yüklemeyi reddeder.

   **GÖZLEM**
   M5 Başarılı benzersiz toplam 51 başlatma + 4 konfigürasyon + 44 koordinatör + 1 gerçek nginx = 100. Önceki 569 referansına eklenen vaka sayısı nginx 5 + stdin 4 = 9; tekrarlar toplam yeni test sayısını artırmaz.

   **AÇIK**
   M6 Bu alt rapor otomatik regresyon düzeyindedir. Sonraki ana koşumda iki PowerShell motorunda gerçek tek komut açılışı ve 90-testlik tam kapı geçti; [canlı sonuç](final-live-environment.json) ve [son kapı](quality-gate-post-startup.txt) ayrı kanıttır. Güvenlik paketi eksikliği sürer.

   **YAN-ETKİ**
   M7 İki başlatıcı, üç kök test dosyası ve 004 PRD/plan/tasks notları değişti. Ayrı Docker ağında oluşturulan test kapsayıcıları ve ağ temizlendi; gerçek uygulama, Spark, SSH tüneli, kullanıcı verisi ve diğer projeler yeniden başlatılmadı.
