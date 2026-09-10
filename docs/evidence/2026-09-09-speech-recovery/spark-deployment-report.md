# Koşum raporu — 2026-09-09 · Kısa konuşma kurtarma kaynağının Spark'a aktarılması

1. Sonuç: Yeni kaynak imajı Spark'ta healthy/ready; izole CUDA çıkarımı, imaj seçimi ve çalışan servis doğrulaması olmak üzere 3 canlı kontrol başarılı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kontrol | Ortam / işlem | Sonuç |
   | --- | --- | --- |
   | Ön koşullar | Yetkili SSH, Linux ARM64 Spark; mevcut imaj, wheelhouse, dosya izinleri ve eski kamu fikstürü | Hazır; [kanıt](spark-source-preflight.json) |
   | Kaynak paketi | Yalnız `Dockerfile.spark`, `requirements.spark.txt`, iki kaynak dizininin `.py` dosyaları; 112.640 bayt | 21 dosya SHA-256 ile doğrulandı; [manifest](spark-source-manifest.json), [aktarım](spark-release-transfer.json) |
   | Ağsız build | Sabit `Dockerfile.spark`; `docker build --platform linux/arm64 --network=none --pull=false --build-context wheelhouse=/home/lab_nvidia1/voiceup-runtime/artifacts/cp313-aarch64-cu129` | 7,17 saniye; paket kurulum katmanı önbellekten kullanıldı; [imaj bilgisi](spark-source-build.json), [çıktı](spark-build.txt) |
   | Ayrı CUDA kontrolü | Yeni imaj, ağsız/read-only geçici kapsayıcı, CDI GPU; önceden doğrulanmış kamu fikstürü | İmaj içindeki 20 dosya hash'i; CUDA ready; 192 boyut/L2 norm 1; `vad-windows-v1`; tepe ayrılan GPU belleği 189.954.560 bayt; [kanıt](spark-candidate-cuda.json) |
   | Geçiş | `.env.spark` içinde yalnız imaj kimliğinin atomik değişimi, ardından mevcut `ensure-spark-runtime.py` | Ready; aynı iç anahtar ve 0600 korundu; eski imaj mevcut; [kanıt](spark-source-deployment.json) |
   | Son durum | Çalışan kapsayıcının imajı ve 20 dosya hash'i; Spark loopback `/ready` | Healthy, restart sayısı 0, doğrulama kapsayıcısı kaldırıldı; [kanıt](spark-source-final.json) |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Aktif yerel ARM64 imaj kimliği `sha256:a743b6e101beee3d85788f082d1b32a957149fda409eec3860c681f249b7a8c5`; kaynak release `f6f12544ad85859220c7a27ca56633f741706072941fbab36bdf39124a4b0125`. Günlük başlatıcı bu hazır imajı kullanır.
   M2 PyTorch'un GB10 compute capability 12.1 için derlenen üst sınır 12.0 uyarısı sürüyor; gerçek çıkarım geçti. Bütün kernel ailelerine uyum iddia edilmez; [uyarılar](spark-candidate-warnings.txt).

   **GÖZLEM**
   M3 `Dockerfile.spark`, `requirements.spark.txt` ve model paketi doğrulayıcısının hashleri önceki release ile aynı. Kaynak paketi env, model dosyası, kullanıcı sesi, test veya geçici dosya içermiyor; son çalışma ağacı da 21 kaynak hash'iyle eşleşti.
   M4 Kamu fikstürü yalnız bağlantı/çıkarım kontrolüdür; bu veri üzerinde kişi doğruluğu veya kurtarma yolunun başarı oranı ölçülmedi. Gerçek kalibrasyon ve yeni holdout sonuçları ana görevde ayrıca raporlanır.

   **AÇIK**
   M5 Gerçek Windows uygulaması üzerinden yeni imajla uçtan uca doğrulama ve son tam kalite kapısı ana görevde sürüyor. Bu dağıtımın geri dönüş yolu çalıştırılmadı; önceki imaj ve kaynak release korunuyor.

   **YAN-ETKİ**
   M6 Spark'ta içerik adresli yeni release/imaj oluşturuldu ve yalnız aynı projenin inference servisi yeni imajla başlatıldı. Önceki `sha256:4b409e3a894b9e719e9785517bab922a8f52a1f74e69f387d6c815a0e39d8db3` imajı ve model/ses dosyaları korundu.
   M7 Windows servisleri veya veritabanı yeniden başlatılmadı; uygulama kaynaklarında bu dağıtım görevi değişiklik yapmadı. Yerel yürütme yardımcısı, arşiv ve ham hata çıktıları yalnız Git dışındaki `outputs/speech-recovery-deploy` altında tutuldu.
