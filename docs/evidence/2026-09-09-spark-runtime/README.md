# Koşum raporu — 2026-09-09 · Uygulamanın model işlemlerini Ethernet üzerinden Spark'a taşıma

1. Sonuç: Uygulama Spark'ta gerçek model çıkarımı yapıyor; yerel inference kapalı — birim 328 başarılı / tarayıcı 0 başarılı / atlanan 1; gerçek PostgreSQL 15 başarılı; karar bekleyen: yok. Toplam 343 otomatik test geçti. İşlevsel L2 gözlendi; güvenlik/üretim kabulü ve gerçek kişi verisiyle L3 sağlanmadı.
2. Koşulan: Sabit teknoloji profili `kt-vibecoding-python-web-v2`; Windows PowerShell 5.1/7, Git Bash, Docker Desktop ve Spark Ubuntu 24.04.4 / ARM64 / NVIDIA GB10.

   | Sınır / komut | Gözlenen sonuç ve kanıt |
   | --- | --- |
   | Son odaklı `pytest`, CPython 3.13.14; `RUN_DOCKER_TRANSPORT=1` | 263 başarılı, 1 Windows symlink testi atlandı; 128,25 sn. Cihaz 9, host ayarı 38, wheelhouse 48, çıkarım 64, tünel 31, başlatıcı/yerel yapılandırma 51, Spark Compose 9, Windows aktarımı 13. [JUnit](focused-tests.xml), [ham çıktı](focused-tests.txt). |
   | `scripts/quality-gate.sh all` | Exit 0; 44 arka uç birim + 15 gerçek PostgreSQL + 21 ön yüz testi. Format/lint/tip, migrasyon/drift, OpenAPI/tip sözleşmeleri, yapılandırma/bağımlılık kabulü, governance ve 46 kaynak × 2 chart overlay geçti. Tek kullanımlık test veritabanı oluşturuldu ve düşürüldü; uygulama veritabanına migrasyon yapılmadı. [Kapı çıktısı](quality-gate.txt). |
   | Kök Ruff ve diff kontrolleri | 14 Python dosyası lint/format kontrolünden geçti; `git diff --check` exit 0. [Ayrıntı](final-static-checks.txt). |
   | Native çevrimdışı imaj ve gerçek GPU | 48 hash doğrulanmış paketle ağsız kurulum ve `pip check`; gerçek CUDA tensor kontrolü, 23 özel HTTP kontrolü. GPU verilmediğinde yetkili çıkarım `503 cuda_unavailable` döndü. [Native rapor](native-run-report.md). |
   | Ethernet ve özel erişim | Windows 192.168.137.1 → Spark 192.168.137.2 gerçek SSH rotası; Wi-Fi korundu. Yanlış host anahtarı reddedildi. Spark 8090 yalnız loopback'te; modelin dış TCP bağlantıları reddedildi. [Rota](ethernet-and-docker.json), [host anahtarı](host-key-rejection.json), [model izolasyonu](service-verification.json). |
   | Windows aktarımı | Dört gerçek nginx sürecinde 50/50 POST ve tam 50 upstream isteği; ayrıca 21 HTTP sınır kontrolü ve altı geçersiz adres reddi. [IPv4 regresyon raporu](ipv4-proxy-run-report.md). |
   | Gerçek uygulama, kesinti ve yeniden başlatma | Dört olumlu iş ve iki beklenen kesinti hatası; kesintiler iki denemede terminal `inference_unavailable`, yerel model kapalı. Spark servisleri yeniden başlatıldıktan 4,03 sn sonra hazır; yeni iş geçti. [İşler](application-live.json), [yeniden başlatma](service-restart.json). |
   | Son 20 işlik hız ölçümü | Bir hariç tutulan ısınma + 20/20 tek denemeli CUDA işi. Isınma dahil 21 iş ve yukarıdaki dört olumlu işin tümü Spark logundaki tekil job UUID ile eşleşti. [Benchmark](application-benchmark.json), [25 işin korelasyonu](application-remote-correlation.json). |
   | Windows başlangıcı | Açık Spark seçimi exit 0; sonraki Auto çağrısı exit 0, aynı sahipli tünel kullanıldı ve Türkçe çıktı doğru. Yerel inference kapalı, backend/worker özel proxy'yi kullanıyor. [Başlatıcı](windows-startup-verification.json), [etkin mod](windows-active-mode.json), [51 testlik rapor](startup-run-report.md), [tünel raporu](tunnel-run-report.md). |
   | `scripts/security-gate.sh` | Exit 1: gerekli çevrimdışı `gitleaks` yok. Semgrep/Trivy adımlarına ulaşılamadı; güvenlik taraması geçti sayılmadı. [Gerçek çıktı](security-gate.txt). |

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: İç Docker ağı Spark model portunu yayınlamadı; mevcut kabul edilmiş nginx imajıyla yalnız loopback'te ayrı aktarıcı eklendi. Model iç ağda kaldı. [İlk hata](service-internal-publish-failure.json), [koruyan testler](../../../tests/test_spark_service_config.py).

   M2 DÜZELTİLDİ: Windows Docker host eşlemesindeki IPv6 rastgele seçiliyordu. İlk benchmarkın ilk ölçülen işi yeniden denendi; ayrı dört süreçli deneyde 4/50 istek 502 verdi. Başlangıçta tek IPv4 doğrulaması sonrası 50/50 geçti; başarısız ölçüm korunuyor. [İlk deneme](application-benchmark-first-attempt.json), [hata](windows-ipv6-failure.txt), [regresyon](ipv4-proxy-run-report.md).

   M3 DÜZELTİLDİ: Başlatıcıda dotenv profiliyle yerel modelin açılması, kısmi geçişte yerel moda dönme, PowerShell 5.1 stderr/zaman aşımı ve Türkçe kodlama sorunları giderildi. [Regresyon kanıtı](startup-run-report.md).

   M4 DÜZELTİLDİ: SSH başlangıç denetimi hata verdiğinde yeni süreç temizliği ve Türkçe yerel ayarda host anahtarı kontrolü düzeltildi; kök statik kontroldeki test importu/açık subprocess seçeneği eksikleri de giderildi. [Tünel](tunnel-run-report.md), [son statik kontrol](final-static-checks.txt).

   **TUZAK**

   M5 Torch'un derlenmiş mimari listesi SM120 ile bitiyor; GB10 SM121 için uyarı veriyor. Gerçek CUDA/VAD/ECAPA geçti; bütün CUDA kernel ailelerine uyum genellenmez. [Uyarı](cuda-import-probe.stderr.txt).

   M6 Tünel Windows oturumu kapandığında sona erer; yeniden açılışta başlatıcı çalıştırılır. Spark servisleri `unless-stopped` kullanır. İş sınırı deneme başına 300 sn, en fazla iki denemedir; toplam 300 sn garantisi değildir. [İşletim rehberi](../../SPARK_RUNTIME.md).

   **GÖZLEM**

   M7 30 saniyelik tekrarlı teknik örnekte Spark işleme p95 **0,198 sn**, kuyruk dahil sunucu p95 **2,111 sn**; önceki 4060 koşumunda sırasıyla 0,869 ve 2,721 sn. Aynı protokol/ses, farklı zamanlardaki iki koşumdur; genel donanım hız oranı veya toplantı performansı iddia edilmez. [Karşılaştırma](application-performance-comparison.json).

   M8 Aynı revision için cihazlar arası vektör kosinüsü **0,9999999525**, en büyük bileşen farkı 0,00006754. Önceden tanımlanmış kabul toleransı veya kişi doğruluğu sonucu değildir. [Sayısal ölçüm](numerical-comparison.json).

   M9 90 saniyede 91 ortak-host bellek örneği: kullanılabilir RAM en az **20,39 GiB**, swap kullanımı sabit 573.440 bayt. PyTorch tepe tahsisi ayrıca 189.954.560 bayt; bu iki farklı kapsam toplanmaz. [Host belleği](benchmark-memory.json), [model tahsisi](fixture-vector-metadata.json).

   **AÇIK**

   M10 T06 güvenlik kanıtı eksik: kurumca kabul edilmiş çevrimdışı tarayıcı paketi yok. Tam uygulama kalite kapısının geçmesi bu eksikliği kapatmaz. [Görev durumu](../../../specs/speaker-identity/PRDs/004-spark-remote-inference/tasks.md).

   M11 Windows symlink yetkisi nedeniyle bir pytest atlandı; önceki üç gerçek Linux dosya sınırı kontrolü ayrı kanıttır. İki test bağımlılığı kullanım dışı bırakma uyarısı verdi; testler geçti, sürüm değiştirilmedi. [Odaklı çıktı](focused-tests.txt), [Linux kontrolü](../2026-09-09-spark-preflight/linux-filesystem-checks.txt).

   M12 Bu değişiklikte tarayıcı koşumu yapılmadı; yeni arayüz davranışı yok. Kalıcı Playwright için kabul edilmiş çevrimdışı paket, doğal Türkçe çok kişi verisi ve L3 sahip kabulü yok. Uzun kayıt/canlı 002/003 taslakları uygulanmadı; pilot 120 sn/50 MiB sınırını korur.

   **YAN-ETKİ**

   M13 Spark'a yalnız gereken kaynak, doğrulanmış model/artifact dosyaları ve özel iç API anahtarı aktarıldı; iki proje servisi ve ağları oluşturuldu. Kullanıcının diğer projeleri/bağlantıları korundu. SSH özel anahtarı ve gerçek env dosyaları Git dışındadır.

   M14 Windows'ta backend/worker yönü ve nginx özel aktarımı değişti, yerel inference durduruldu; Spark modu ve sahipli tünel kaydı Git dışındaki outputs altında tutulur. Uygulama profili değiştirilmedi; teknik ses yüklemeleri ve test işleri mevcut saklama politikasına tabidir.

Kullanım: proje kökünde `.\scripts\start-local.ps1`; ayrıntılar
[Spark geliştirme rehberinde](../../SPARK_RUNTIME.md). Bu rapordaki L2, gözlenen
işlevsel çalışma sınırıdır; güvenlik/üretim kabulü veya onlarca kişide tanıma doğruluğu değildir.
