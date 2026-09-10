# Koşum raporu — 2026-09-09 · Spark bağlantısı ve çıkarım hazırlığı

1. Sonuç: SSH ve hazırlık doğrulandı; 004 kapsamının gerçek GPU ve uygulama geçişi tamamlanmadı — birim 224 başarılı / tarayıcı 0 başarılı / atlanan 1; gerçek PostgreSQL 15 başarılı; karar bekleyen: yok.
2. Koşulan:

   | Kapsam | Ortam, komut ve gözlenen sonuç |
   | --- | --- |
   | Spark oturumu | Yetkili anahtar ve strict host checking ile gerçek SSH giriş başarılı. Ubuntu 24.04.4, aarch64, NVIDIA GB10, compute capability 12.1, sürücü 580.159.03, host Python 3.12.3 doğrulandı. Ayrıntılı cihaz envanteri Git dışındaki çıktıda. |
   | Ethernet/Docker | Fiziksel enP7s7 bağlı fakat IPv4 yok. Mevcut SSH Wi-Fi üzerinden. Kullanıcı Docker grubunda değil; Docker socket erişimi reddediliyor, sudo parola istiyor. İncelenmiş yerel yönetici aracı cihaza kopyalandı; çalıştırılması bekleniyor. |
   | Odaklı otomatik testler | Windows CPython 3.13.14; 9 inceleme + 38 host ayarı + 48 wheelhouse + 64 çıkarım testi: 159 başarılı, 1 atlanan. [JUnit](spark-preparation-tests.xml). Son biçim düzeltmesinden sonra 47 inceleme/host testi tekrar geçti; tekrarlar toplamda ikinci kez sayılmadı. |
   | Linux dosya sınırı | Spark host Python 3.12; gerçek dizin/dangling symlink reddi ve idempotent kilit üretimi: 3 kontrol geçti. [Çıktı](linux-filesystem-checks.txt). Windows'taki platform atlaması başarıya çevrilmedi. |
   | ARM64 paketleri | 48 dosya / 3.643.549.689 bayt Spark'a indirildi ve tam boyut/SHA-256 ile iki kez doğrulandı. Son yardımcı mevcut 48 dosyanın hepsini tekrar kullandı. [Dosya kanıtı](arm64-wheelhouse-verification.json). Paket kurulmadı ve GPU çalıştırılmadı. |
   | Kaynak incelemesi | 48 artifact/67 aktif bağımlılık bağlantısı kapalı; 46 aynı artifact ve 9 genç mevcut pin korunuyor. 119 doğrudan envanter koordinatı ve kilit/manifest özetleri kayıtlı. [Bağımsız inceleme](arm64-source-review.json), [Python ARM64 index](python-base-platforms.json). |
   | Model paketi | Sabit ECAPA/Silero paketi yeni hedefe aktarıldı: 7/7 dosya, 91.256.819 bayt. Aynı derlenmiş hash listesi hedefte doğrulandı; aktarım/doğrulama 14,32 saniye. [Aktarım kaydı](model-bundle-transfer.json). Model dosyası doğrulamak CUDA çıkarımı değildir. |
   | Docker Desktop | İki bozuk geçici socket yolu başlangıcı engelliyordu. Yalnız bu çalışma alanları kardeş yedek adlarda korundu; motor 29.6.1/Linux x86_64 olarak açıldı. Image, volume veya uygulama verisi sıfırlanmadı. |
   | Özel taşıma deneyi | Windows loopback test sunucusuna nginx üzerinden gerçek nonce erişimi geçti; internal worker sayısal hedefte ağ erişimi hatası verdi. Özel nginx ara katmanı gerekiyor. [Ayrıntılar](loopback-transport-probe.json). Spark model HTTP servisi henüz denenmedi. |
   | Tam uygulama kapısı | `kt-vibecoding-python-web-v2`; `scripts/quality-gate.sh all` exit0. 44 arka uç birim + 15 gerçek PostgreSQL + 21 ön yüz testi geçti; format/lint/tip, migrasyon/drift, OpenAPI/tip sözleşmeleri, governance ve chart render geçti. Geçici test DB oluşturuldu ve düşürüldü; uygulama DB'sine migrasyon uygulanmadı. [Ham çıktı](quality-gate.txt). |
   | Güvenlik kapısı | `scripts/security-gate.sh` exit2: `required offline security tool is unavailable: gitleaks`. [Ham çıktı](security-gate.txt). |

3. Maddeler:

   **KUSUR**

   M1 Eksik cihaz/host/paket yardımcıları ve açık runtime profilleri testlerle eklendi; son kök Ruff/biçim kusurları düzeltildi.

   M2 Docker Desktop'ın bozuk geçici bağlantı dosyaları motoru açtırmıyordu; dosyalar korunarak çalışma yolları yeniden oluşturuldu ve tam uygulama kapısı geçti.

   **TUZAK**

   M3 SSH'nin Wi-Fi adresinde çalışması Ethernet kanıtı değildir; enP7s7 adresi ve Windows rotası yönetici adımı sonrası tekrar doğrulanmalı.

   M4 ARM64 TorchAudio aynı ad/sürümde farklı publisher içerikleri taşır; yalnız manifestteki kaynak ve hash kullanılmalı. Paket hashleri gerçek GB10/CUDA uyumluluğunu kanıtlamaz.

   M5 Worker ağı tünele doğrudan ulaşmıyor; nginx'in özel, yayımlanmayan portu ve açık host eşlemesi gerçek servisle doğrulanmadan uzak mod seçilmemeli.

   **GÖZLEM**

   M6 Mevcut x86_64/CUDA 12.8 kilidi ve 4060 servisi korunuyor. Spark ayrı ARM64/CUDA 12.9 profilidir; iki profil de gerçek GPU işlemi ister ve CPU'ya sessiz dönüş yapmaz.

   M7 Açılan SSH, indirilen dosyalar ve Linux dosya kontrolleri canlı hazırlık kanıtıdır. Yazılan kod/ayarların otomatik kanıtı L1'dir; 004'ün GPU/uygulama kabulü tamamlanmış sayılmaz.

   **AÇIK**

   M8 Spark'ta kullanıcıya gönderilen tek sudo komutu bekleniyor: özel Ethernet profili ve Docker grup üyeliği. Yeni oturumdaki Docker erişimi ve kablolu rota henüz doğrulanmadı.

   M9 Native ARM64 offline image kurulumu, pip/import, gerçek CUDA/VAD/ECAPA, aynı-revision sayısal karşılaştırma, SSH model tüneli, özel proxy, uygulama işi, kesinti ve uzak mod başlatıcısı açık.

   M10 Gitleaks/offline güvenlik paketi ve kalıcı tarayıcı koşumu çalıştırılmadı. Gerçek ayrı oturumlu insan sesleriyle doğruluk ve onlarca kişilik galeri deneyi henüz yapılmadı.

   **YAN-ETKİ**

   M11 004 PRD/plan/görevleri, yardımcılar/testler, ayrı Spark kaynak manifesti/kilidi/Dockerfile ve kaynak kabul kaydı eklendi. Spark'ın yeni `~/voiceup-runtime` hazırlık alanına dosyalar aktarıldı; GitHub tokeni veya kullanıcı sesleri taşınmadı. Git commit/push yapılmadı.

   M12 Docker socket yedekleri silinmedi: `C:/Users/furko/AppData/Local/Docker/run.voiceup-backup-20260909`, `run.voiceup-backup-20260909-attempt2` ve `C:/Users/furko/AppData/Local/docker-secrets-engine.voiceup-backup-20260909`. Yalnız bu hazırlıkta başlatılmış, başlangıç hatası veren Docker süreçleri kapatılıp tekrar açıldı.
