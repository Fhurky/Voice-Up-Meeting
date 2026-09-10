# Koşum raporu — 2026-09-10 · Native Linux ARM64 CPU üzerinde gerçek model ve özel HTTP doğrulaması.

1. Sonuç: Gerçek CPU HTTP akışı geçti — birim 0 başarılı / tarayıcı 0 başarılı / gerçek HTTP 9 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; önceden yetkilendirilmiş fiziksel Spark üzerinde native Linux aarch64, Python 3.13.14, `torch=2.8.0+cpu`, `cuda_build=null`, `device=cpu`, `runtime_profile=aarch64-cpu`. Sonuç L2 özel HTTP kanıtıdır; uygulama veritabanı veya kalıcı profil işlemi çalıştırılmadı.

   | Kontrol | Gözlenen sonuç | Kanıt |
   | --- | --- | --- |
   | Canlılık, hazır olma | 2 başarılı; HTTP 200 | [Gerçek HTTP çıktısı](cpu-aarch64-native-http-smoke.json) |
   | Bozuk ses, desteklenmeyen ses, yanlış iç anahtar, sessizlik | 4 başarılı; HTTP 400/415/401/422 | [Gerçek HTTP çıktısı](cpu-aarch64-native-http-smoke.json) |
   | Tekrarlı 30 saniyelik genel WAV: kayıt, tanıma; FLAC: tanıma | 3 başarılı; HTTP 200, normalize 192 boyut, GPU ölçüsü yok | [Gerçek HTTP çıktısı](cpu-aarch64-native-http-smoke.json) |
   | Aktarım ve değişmez imaj zinciri | 4 dosya hash değeri, OCI indeks/ARM manifest/yapılandırma ve 11 katman doğrulandı | [Çalıştırma ve koruma kaydı](cpu-aarch64-native-verification.json) |
   | İmaj içindeki config/models/API kaynakları | 3 dosyanın byte hash değeri mevcut kaynakla aynı | [Kaynak bağları](cpu-aarch64-native-verification.json) |
   | Mevcut Spark hizmetleri ve model | 2 konteynerin kimlik/imaj/başlama zamanı/yeniden başlama sayısı; 6 model dosyası ve manifest değişmedi | [Önce/sonra kanıtı](cpu-aarch64-native-verification.json) |

   Yerel `docker image save --output outputs/local-cpu-native-arm64-20260910-review/image.tar sha256:b1fb44a1ced25fb328552f991572f1b88a4f0a54ac40d5c4e9d64a745a2cad43` çıktısı, `Get-SparkConnection` ve `Invoke-StartupNative` kullanan mevcut sarmalayıcı üzerinden sabit sunucu anahtarıyla SSH/SFTP aktarımından geçti. Sunucuda yalnız yeni `/tmp/voiceup-cpu-native-arm64-20260910-review` dizini kullanıldı; mevcut Spark başlatıcısı çağrılmadı. Etiketsiz arşiv `docker image load --input` ile yüklendi; deneme konteyneri önce oluşturulup incelendi, sonra tam kimliğiyle başlatıldı.

   Çalışan komut: `python /smoke/smoke_cpu.py --runtime-profile aarch64-cpu /smoke/repeated-public-sample-30s.wav`. Docker kısıtları: `--runtime runc --network none --read-only --user 10001:10001 --cpus 2 --memory 4g --memory-swap 4g --pids-limit 128 --cap-drop ALL --security-opt no-new-privileges:true`; `/tmp` 512 MiB tmpfs, model ve smoke dosyaları salt okunur, GPU aygıtı/isteği yok. OpenMP, MKL ve OpenBLAS iş parçacığı sayısı 2; model indirme çevrimdışı ayarlarla kapalı.

   Konteyner 5,573 saniyede çıkış 0 ile tamamlandı; bellek aşımı yok. İç HTTP açılışı/model yükleme/ısınma 0,522 saniye; WAV kayıt 1,181, WAV tanıma 1,085, FLAC tanıma 1,086 saniye. Açılış ölçüsü konteyner oluşturmayı ve ilk Python importlarını kapsamaz.

3. Maddeler:

   **KUSUR** — yok
   **TUZAK**
   M1 İlk salt okunur arşiv kontrolü OCI indeks kimliğini yapılandırma kimliğiyle eşitleyip yüklemeden durdu; hash zinciri doğrulanarak kontrol düzeltildi, ürün kaynağı değişmedi.
   M2 İki mevcut TorchAudio kullanımdan kaldırma uyarısı görüldü; gerçek HTTP kontrollerini engellemedi. İmajın yerel indeks kimliği `b1fb44…`, native Docker yapılandırma kimliği `32cacd04…`; tam bağlar JSON kaydındadır.
   **GÖZLEM**
   M3 Mevcut Spark CUDA hizmetleri, model ağırlıkları, sır dosyaları, veritabanları ve kullanıcı profilleri korunmuştur; önce/sonra çalışan konteyner kümesi aynıdır.
   M4 QEMU üzerindeki önceki HTTP zaman aşımı/signal 11 sonucu [ayrı raporda](cpu-aarch64-run-report.md) korunur; native geçiş o koşumun sonucunu değiştirmez.
   **AÇIK**
   M5 Fiziksel MacBook ortamı yoktur; bu Spark CPU ölçümü Mac gecikmesini, Mac kurulumunu, kullanıcı kabulünü veya yeni konuşmacı doğruluğunu kanıtlamaz.
   **YAN-ETKİ**
   M6 Yalnız başarılı ve durmuş deneme konteyneri tam kimliğiyle kaldırıldı; yeni etiketsiz CPU imajı, sunucudaki ayrı geçici dizin ve yerel ignored çıktı arşivi inceleme için tutuldu. Üç yeni kanıt dosyası yazıldı.
