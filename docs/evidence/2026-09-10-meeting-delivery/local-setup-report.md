# Koşum raporu — 2026-09-11 · Yerel RTX toplantı seçimi, çevrimdışı hazırlık ve özel proxy rotaları.

1. Sonuç: Hedeflenen kurulum ve taşıma kontrolleri geçti; geniş başlangıç paketinde ortam eksiği var — birim 31 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Önceki geniş pakette 56 başarılı / 9 başarısız; dokuz hata `pwsh` yürütülebiliri bulunamamasıdır.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows PowerShell 5.1, yerel Python 3.12 test ortamı, Docker Desktop Linux x86_64 ve mevcut digest sabitlenmiş nginx imajı. Bu host test ortamı ürünün Python 3.13 sınırını değiştirmez.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `pytest tests/test_meeting_setup.py tests/test_spark_startup.py -k meeting -q` | İlk uygulama öncesi 5 başarısız / 3 import hatası / 2 başarılı; son genişletilmiş hedef 17/17 başarılı. |
   | Model bağlama dizini koruması | Önce eksik `create_host_path: false` kontrolünde 1 başarısız / 12 başarılı; uzun bind tanımıyla düzeltildi. |
   | `pytest tests/test_meeting_setup.py tests/test_spark_startup.py tests/test_spark_service_config.py -q` | O aşamada 65 test: 56 başarılı / 9 başarısız; dokuzunda eski helper `shutil.which('pwsh') = None` nedeniyle alt süreci başlatamadı. Test atlanmadı veya zayıflatılmadı. |
   | `RUN_DOCKER_TRANSPORT=1 pytest tests/test_spark_transport_config.py -q` | Son koşum 14/14 başarılı: gerçek HTTP, query/body/header aktarımı, hatalı rota/yöntem reddi, IPv4 sınırı, 50 POST/4 nginx worker ve backend yenilenmesi. |
   | `python scripts/check-config-sync.py` | Başarılı: 36 Compose anahtarı, 37 örnek ortam alanı, 39 typed alan, 72 kaynak dosyası. |
   | `python scripts/check-dependency-admission.py` | Başarılı: 211 koordinat; `403862bbd150130d09566193560c011863d2ece858028ca2ab5a487c39b14ef6`. |
   | `ruff format` / `ruff check` | Yeni hazırlık scripti ve testleri biçimlendi, lint geçti. `python -m black --check` denemesi host ortamında modül bulunmadığından çalışmadı; Black başarısı iddia edilmez. |

3. Maddeler:

   **KUSUR**
   M1 Yeni iki meeting rotası eklendiğinde özel proxy başlangıcının sabit host-alias değiştirme koruması hâlâ 2 bekliyordu; gerçek konteyner açılışı başarısız oldu. `start-spark-proxy.sh` koruması 4 oldu; gerçek taşıma paketi yeşil.
   M2 Kısa bind gösterimi eksik model yolunu boş dizin olarak oluşturabilirdi; iki yeni model mount'u `read_only: true` ve `create_host_path: false` ile güvenli başarısız olur.
   **TUZAK**
   M3 `setup-local-meeting.py` yalnız yerel Linux x86_64 Docker hedefini kabul eder; uzak Docker ve ARM hedefi seçimi değiştirmeden reddedilir. Normal başlatma indirme/derleme yapmaz; CPU/Spark modları yerel meeting marker'ını kullanmaz.
   M4 Mevcut PowerShell 7 test yolu bu makinede yoktur; Windows PowerShell 5.1 ile yeni Local/Spark seçim sınırları ve UTF-8 BOM doğrulandı. Bu kontrol eksik dokuz PowerShell 7 testinin yerine geçmez.
   **GÖZLEM**
   M5 Gerçek dosya sistemi testleri iki wheelhouse'un hash kilitlerini, eksik/fazla/değişmiş dosya reddini sınar; Compose çözümlemesi temel ses modeli, CUDA seçimi, salt okunur kök ve GPU rezervasyonunun korunduğunu doğrular.
   M6 Taşıma testi bir in-memory HTTP fixture ve yalnız testin oluşturduğu nginx konteynerlerini kullanır; model sonucu, Spark cihazı veya ARM uyumu kanıtı değildir. Çalışan nginx ve mevcut worker ağ ayarları değiştirilmedi.
   **AÇIK**
   M7 Bu alt görevde gerçek `setup-local-meeting.py` indirme/build/marker geçişi çalıştırılmadı; model çalışma zamanı ve gerçek kayıttan metin/hafıza bütünleşmesi ayrı doğrulama bekler.
   M8 Worker'ın 256 MiB limiti ile uç 70 saniyelik yüksek örneklemeli parça belleği, 10 GiB ortak diskte toplam tenant/profil kapasitesi, tam kalite kapısı ve güvenlik taramaları bu koşumda ölçülmedi. Kapasite sınırları `MEETING_WORKFLOW.md` içinde açıklandı.
   **YAN-ETKİ**
   M9 Yerel meeting overlay, hazırlık scripti, iki launcher'da kalıcı Local seçimi, iki proxy allowlist'i, testler ve işletim belgesi eklendi/güncellendi. Ürün Dockerfile/bağımlılık pinleri bu alt görevde değiştirilmedi.
   M10 Teste ait geçici nginx konteynerleri ve ağlar test sonunda temizlendi. XML kanıtları Git dışı `outputs/2026-09-10-meeting-delivery/meeting-{startup-targeted,transport-suite}.xml` altında tutulur; gerçek model seçimi marker'ı bu koşumda yazılmadı.
