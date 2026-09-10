# Koşum raporu — 2026-09-09 · Spark başlatıcısının hata, profil ve mod kontrolleri

1. Sonuç: Odaklı otomatik doğrulama geçti — birim 51 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Bu rapor başlatıcı değişikliğinin L1 kanıtını taşır; gerçek uygulama geçişini doğrulamaz.
2. Koşulan: Windows, Windows PowerShell 5.1, PowerShell 7, Git Bash ve gerçek Docker Compose yapılandırma ayrıştırıcısı; sabit teknoloji profili `kt-vibecoding-python-web-v2`.

   | Kontrol | Komut / dosya | Gözlenen sonuç |
   | --- | --- | --- |
   | Başlangıçtaki başarısız testler | `.venv/Scripts/python.exe -m pytest tests/test_spark_startup.py -q --tb=short` | 43 test: 16 başarılı, 27 başarısız; eski davranışın kusurları yeniden üretildi. |
   | İlk düzeltme | Aynı 43 test | 43 başarılı. |
   | Önceki odaklı paket | `.venv/Scripts/python.exe -m pytest tests/test_spark_startup.py tests/test_local_configuration.py -q --tb=short -o addopts= --durations=3` | 50 başarılı; 56,80 saniye. |
   | Son kabuk düzeltmesi | `.venv/Scripts/python.exe -m pytest tests/test_spark_startup.py -q -o addopts= -k stack --tb=short` | Yukarıdaki paketin 24 testi tekrar başarılı; 3,17 saniye. Toplama yeniden eklenmedi. |
   | Türkçe çıktı regresyonu | `.venv/Scripts/python.exe -m pytest tests/test_spark_startup.py -q -o addopts= -k turkish --tb=short` | Gerçek Windows PowerShell 5.1 `-File` çağrısı önce 1 başarısız; UTF-8 BOM düzeltmesinden sonra 1 başarılı. |
   | Son odaklı paket | `.venv/Scripts/python.exe -m pytest tests/test_spark_startup.py tests/test_local_configuration.py -q -o addopts= --tb=short` | Önceki 50 test ve yeni çıktı testi: toplam 51 başarılı; 56,41 saniye. |
   | Biçim / lint | `.venv/Scripts/python.exe -m ruff check tests/test_spark_startup.py tests/test_local_configuration.py` ve aynı dosyalarda `ruff format --check` | Başarılı. |
   | Kabuk sözdizimi / diff | `bash -n scripts/stack.sh`; `git diff --check -- scripts/start-local.ps1 scripts/stack.sh tests/test_spark_startup.py tests/test_local_configuration.py` | Başarılı. |

3. Maddeler:

   **KUSUR**

   M1 `.env` içindeki `COMPOSE_PROFILES`, yalnız süreç ortamını denetleyen kontrolü aşabiliyordu. Çözümlenen modelde etkin `inference` servisi mutasyondan önce reddedilir (DÜZELTİLDİ, `test_dotenv_profile_is_detected_from_real_compose_before_any_mutation`).

   M2 Kısmi uzak geçişten sonra eski yerel mod korunabiliyordu. Başarılı tünel/yapılandırma kontrolünden sonra, ilk Compose mutasyonundan önce seçilen mod kaydedilir; başarısız geçiş sonraki `Auto` çağrısını yerel modele döndürmez (DÜZELTİLDİ, `test_partial_activation_cannot_revert_to_local`).

   M3 Windows PowerShell 5.1, yönlendirilen yerel stderr nedeniyle hazır kontrolünü erken kesiyordu; komut hataları da özel çıktıyı gösterebiliyordu. Yerel süreç akışları doğrudan yakalanır ve hata kodları denetlenir (DÜZELTİLDİ, iki kabukta `test_spark_intent_precedes_mutation_and_native_stderr_is_retried`).

   M4 Docker alt süreçleri sınırsız bekleyebiliyordu. Sınırlar: yapılandırma 15 saniye, `up` 180 saniye, `stop` 30 saniye; hazır kontrolü toplam 30 saniye ve her çağrı en çok kalan süre/5 saniye (DÜZELTİLDİ, yerel süreç zaman aşımı ve terminal hazır kontrolü testleri).

   M5 Genel `start`/`restart`, yapılandırma hatası ve `COMPOSE_PROJECT_NAME` birleşiminde mevcut konteynerlerden oluşturulan projeye dönebiliyordu. Ortam/farklı model seçimi engellenir; yapılandırma hatasında konteyner komutu çalıştırılmaz (DÜZELTİLDİ, `test_stack_general_activation_fails_closed`).

   M6 Ana görevin 6,25 saniyede exit 0 ile tamamlanan canlı Spark başlatmasında Türkçe `için` metni bozuldu. Windows PowerShell 5.1'in kaynak kodlamasını tanıması için `start-local.ps1` UTF-8 BOM ile kaydedildi; UTF-8 konsol çıktısı gerçek `-File` çağrısında doğrulandı (DÜZELTİLDİ, `test_powershell_file_invocation_preserves_turkish_console_output`).

   **TUZAK**

   M7 Spark kabuk modu `timeout` aracını gerektirir; mevcut Git Bash içinde bulundu. Yapılandırma süreci TERM sinyalinden sonra kapanmazsa 3 saniye içinde KILL uygulanır. Açık `Local` seçimi korunur.

   **GÖZLEM**

   M8 `local-inference` ve `*` değerleri gerçek Compose ayrıştırıcısında geçici `.env` ile çözümlendi; üretilen model daha sonra etkisiz başlatıcı testine verildi. Bu odaklı test koşumunda gerçek `up`, `start`, `restart`, `stop` veya tünel komutu çalıştırılmadı.

   M9 İki PowerShell sürümünde gerçek fakat etkisiz yerel yürütülebilir dosya kullanıldı; stderr gizliliği, argüman bütünlüğü ve zaman aşımından sonra test sürecinin kapanması doğrulandı. Kalıcı hazır olamama testi önceki paket koşumunda 30,44 saniyede hata verdi; Spark seçimi korundu ve yerel model için `stop` çağrılmadı.

   **AÇIK**

   M10 Gerçek Spark uygulama işi ve bütün proje kalite kapısı bu odaklı koşumun kanıtı değildir; ana görev bunları ayrı raporlar. M6'daki canlı bulgu ana görevin bildirimidir; bu test paketi canlı uygulama koşumunun yerini almaz.

   **YAN-ETKİ**

   M11 `scripts/start-local.ps1`, `scripts/stack.sh`, `tests/test_spark_startup.py` ve `tests/test_local_configuration.py` içindeki yalnız başlatıcı testi güncellendi. Son çıktı düzeltmesi başlatıcının kaynak kodlamasını değiştirdi; davranışını değiştirmedi. Yerel süreç/Compose örnekleri test geçici dizinlerinde oluşturuldu; gerçek uygulama, model veya ağ durumu değiştirilmedi.
