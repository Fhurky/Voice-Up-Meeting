# Koşum raporu — 2026-09-10 · MacBook için yerel CPU çalışma ortamı

1. Sonuç: Tam uygulama kalite kapısı geçti — birim/entegrasyon 143 başarılı /
   tarayıcı 0 başarılı / atlanan 0; ayrı CPU ve ortam kontrolleri aşağıdadır;
   karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows üzerinden Docker Linux,
   uygulamada Python 3.13/PostgreSQL 17 ve React/Vite. Mac cihazı kullanılmadı.

   | Kontrol | Gözlenen sonuç ve kanıt |
   | --- | --- |
   | `scripts/quality-gate.sh all` | Çıkış 0; [104 backend](quality-gate-backend.xml), [39 frontend](quality-gate-frontend.json); format/lint/tip, config, migration, OpenAPI/tip drift, governance ve chart başarılı. [Ham çıktı](quality-gate-all.txt). |
   | Inference runtime | [119/119 başarılı](runtime-green.xml); [kırmızı/yeşil raporu](runtime-report.md). CPU cihaz/mimari/sürüm hataları ve CUDA regresyonları kapsandı. |
   | CPU kurulum/model/artifact testleri | [105 başarılı, 1 Windows platform atlaması](setup-model-artifact-final.xml); 30 başlangıç, 18 model hazırlama ve mevcut artifact sınırları dahil. |
   | Linux artifact regresyonu | [66/66 başarılı](cpu-artifacts-final.xml); Windows'taki symlink vakası burada da geçti. Aynı testler yeniden toplama eklenmez. |
   | Bağımsız artifact incelemesi | [60 benzersiz resmî artifact](cpu-artifact-source-review.json); mimari başına 47 paket/65 aktif bağımlılık, tam dosya hashleri [doğrulandı](cpu-wheelhouse-verification.json). |
   | Model ilk hazırlığı/tekrar | [3 kontrol geçti](model-preparation-live.json): altı model dosyası yeni dizine indirildi, paket doğrulandı ve ikinci çağrı indirmeden mevcut paketi kullandı. |
   | x86_64 gerçek CPU | Ağsız/read-only imajda ECAPA/Silero ve [9 gerçek HTTP kontrolü](cpu-x86_64-final-http.json) geçti; WAV/FLAC, sessizlik ve yetkisiz istek dahil. [Son imaj build](cpu-x86_64-final-build.txt). |
   | CPU uygulama entegrasyonu | [1/1 başarılı](cpu-application-results.xml): gerçek PostgreSQL ve TCP model adaptörüyle kayıt/tanıma; genel API uygulama içinde ASGI üzerinden çağrıldı. [Rapor](cpu-application-report.md); Mac/tarayıcı kanıtı değildir. |
   | ARM64 CPU | [11 import/kernel/ortam kontrolü](cpu-aarch64-probe.json) geçti; Docker Desktop emülasyonudur, Mac hız ölçümü değildir. [Düzeltilmiş build](cpu-aarch64-fixed-build.txt). |
   | ARM64 emülasyonda gerçek ses | [HTTP koşumu başarısız](cpu-aarch64-run-report.md): 180 saniyelik zaman aşımı ve QEMU signal 11; tamamlanmış dokuz vaka raporu yoktur. |
   | Gerçek ARM64 donanımında CPU | Spark'ta GPU erişimi olmayan, ağsız/read-only, 2 CPU/4 GiB sınırındaki aynı imajla [9/9 HTTP kontrolü](cpu-aarch64-native-http-smoke.json) geçti. [Rapor](cpu-aarch64-native-run-report.md); Mac donanım/hız kabulü değildir. |
   | Eski Windows başlangıç regresyonları | [65 başarılı/10 ortam hatası](windows-startup-regressions.xml); `pwsh` PATH üzerinde olmadığı için on testin alt süreci başlamadı. |
   | `scripts/security-gate.sh` | Çıkış 2: `required offline security tool is unavailable: gitleaks`; [çıktı](security-gate.txt). Güvenlik taraması geçti sayılmaz. |
   | Son kaynak/rapor kontrolü | [3/3 başarılı](final-metadata-verification.json): 39 kaynak hash değeri, 81 yerel belge bağlantısı ve dar kanıt metni sır taraması; güvenlik kapısının yerine geçmez. `scripts/check-dependency-admission.py` 143 koordinatla, `git diff --check` çıkış 0 ile geçti. |

3. Maddeler:

   **KUSUR**

   M1 CPU config/model yükleyici ve backend yanıt sınırı eklendi; CUDA'ya sessiz
   geri dönüş yok. [Runtime raporu](runtime-report.md) ve backend kapısı koruyor.

   M2 ARM64 TorchAudio, mevcut wheel'deki OpenMP dosyasını standart adıyla bulamadı;
   hash kontrollü build alias'ıyla düzeltildi, yeni paket/sürüm eklenmedi.

   M3 Resmî Hugging Face CDN yönlendirmesi ve JIT dosyasının atomik yayını hazırlık
   testlerinde düzeltildi; [18 model testi](model-preparation-tests.xml) koruyor.

   **TUZAK**

   M4 Apple Silicon profili Linux ARM64 **CPU** kullanır; Metal/GPU hızlandırması
   değildir. ARM emülasyonundan Mac gecikmesi veya kişi doğruluğu çıkarılamaz.

   M5 Günlük başlangıç indirme/build yapmaz; kod güncellenince kurulum tekrar gerekir.
   `CPU_ARCH` hedef Docker'dan üretilir; başka bilgisayarın `.env` dosyası kopyalanmaz.

   **GÖZLEM**

   M6 Kalite kapısı kendine özel `_test` veritabanına migration uygulayıp onu düşürdü;
   mevcut Spark modu, kullanıcı sırları ve uygulama veritabanı değiştirilmedi.

   M7 Aynı ECAPA/Silero ağırlıkları, vektör uzayı ve eşikler korundu. Kullanılan
   tekrarlı ses, teknik bağlantı kanıtıdır; yaklaşık 50 kişide yeni doğruluk deneyi değildir.

   **AÇIK**

   M8 Fiziksel MacBook'ta temiz ilk kurulum, tarayıcı ve temsilî sesle kabul yapılmadı;
   005 T06 açık. Mac çalışma ortamına erişim yoktur.

   M9 Gitleaks ve PowerShell 7 (`pwsh`) bulunmadığı için güvenlik taraması
   ve on eski `pwsh` regresyonu doğrulanmadı; testler değiştirilmedi veya atlatılmadı.

   **YAN-ETKİ**

   M10 CPU Dockerfile/Compose/başlatıcı, model hazırlayıcı, testler, Mac rehberi ve
   005 kabul/plan/görev kayıtları eklendi; bağımlılık kaynakları incelemeyle kaydedildi.

   M11 Doğrulama model/wheelhouse ve imajları yerelde hazırladı. Bunlar Git dışında
   kaldı; mevcut sesler/profiller taşınmadı. Commit veya push yapılmadı.

   M12 CPU uygulama testinin ayrı veritabanı/konteyner/dosya hedefleri doğrulanarak
   temizlendi; mevcut konteyner kimlikleri, sırlar ve mod dosyası değişmedi.

   M13 Native ARM test konteyneri kaldırıldı; Spark GPU servisleri ve model hashleri
   değişmedi. Yeni CPU imajı ve geçici aktarım arşivi test önbelleği olarak tutuldu.
