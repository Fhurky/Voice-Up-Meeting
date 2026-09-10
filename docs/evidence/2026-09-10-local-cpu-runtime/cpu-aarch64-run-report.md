# Koşum raporu — 2026-09-10 · ARM64 CPU çevrimdışı imaj derlemesi ve emülasyon üzerinde çalışma zamanı doğrulaması.

1. Sonuç: Son ARM64 CPU imajı içe aktarma ve sayısal çekirdek kontrollerini geçti; gerçek modelle HTTP denemesi emülasyonda başarısız oldu — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; çalışma zamanı kontrolleri 11 başarılı / HTTP denemeleri 0 başarılı, 1 başarısız; karar bekleyen: yok.
2. Koşulan:

   | Ortam | Komut veya sınır | Gözlenen sonuç |
   | --- | --- | --- |
   | Windows Docker Desktop, Linux ARM64 emülasyonu | `docker build --platform linux/arm64 --network none --build-arg CPU_ARCH=aarch64 --build-context wheelhouse=models/inference-cpu-aarch64-wheelhouse -f app/inference/Dockerfile.cpu -t voiceup-inference:cpu-aarch64 .` | Mevcut sabitlenmiş Python imajının ARM64 platformu hazırlandı; özetleri kilitli 47 wheel dosyası derleme sırasında ağ erişimi olmadan kuruldu ve `pip check` geçti. [İlk derleme](cpu-aarch64-build.txt). |
   | Aynı emüle ARM64 imajı | Gerçek Torch/TorchAudio içe aktarımı | Paket bağımlılık denetimi geçmesine rağmen `libgomp.so.1` bulunamadığından başarısız oldu. [Hata](cpu-aarch64-probe-failure.txt). |
   | Aynı imaj; yalnız geçici `/tmp` yazılabilir | Mevcut özetli Torch OpenMP kitaplığına sembolik bağlantı oluşturma, ardından Torch/TorchAudio içe aktarımı ve matris çarpımı | Başka kitaplık kurmadan veya paket sürümlerini değiştirmeden başarılı oldu. [Deneme](cpu-aarch64-alias-probe.txt). |
   | Son CPU imaj derlemesi | Root sahipliğindeki OpenMP bağlantısı eklendikten sonra aynı ağ erişimi kapalı derleme | Başarılı; [son derleme](cpu-aarch64-fixed-build.txt). |
   | Son ARM64 CPU imajı; UID10001, salt okunur kök dosya sistemi, ağ kapalı, Linux yetenekleri kaldırılmış | İçe aktarım, mimari/sürüm/cihaz denetimleri, değiştirilemeyen bağlantı, matris/evrişim/normalleştirme, TorchAudio/SciPy yeniden örnekleme ve NumPy sayısal kontrolleri | 11 başarılı. Kaydedilen dört çalışma zamanı kaynak özeti çalışma alanıyla eşleşiyor. [Kesin komut ve sonuç](cpu-aarch64-probe.json), [standart hata çıktısı](cpu-aarch64-fixed-probe-stderr.txt). |
   | Aynı son ARM64 imajı; mevcut ECAPA/Silero model paketi ve açık kaynaktan oluşturulmuş WAV salt okunur bağlanmış | `python -B /checks/smoke_cpu.py --runtime-profile aarch64-cpu /fixtures/repeated-public-sample-30s.wav` | Oluşturulmuş WAV kaydı/tanıma isteğinde 180 saniyelik HTTP zaman aşımı, ardından QEMU sinyal 11 nedeniyle başarısız oldu. Araç, tamamlanmış dokuz vakalık JSON raporu üretmedi. [Kesin komut](cpu-aarch64-http-execution.json), [hata](cpu-aarch64-http-failure.txt), [standart hata çıktısı](cpu-aarch64-http-stderr.txt). |

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: ARM64 TorchAudio `libgomp.so.1` isterken eşlik eden Torch wheel dosyası kitaplığı denetlenmiş, özet içeren bir adla saklıyor. CPU Dockerfile kitaplığın SHA256 özetini doğrulayıp sabit, root sahipliğinde bir bağlantı oluşturuyor; 47 paket sürümü değişmedi.

   M2 AÇIK: Emülasyondaki gerçek model HTTP koşumu oluşturulmuş WAV isteğinde zaman aşımına uğradı, ardından QEMU sinyal 11 bildirdi. Tam vaka sonuçları bulunmadığından dokuz HTTP vakasının geçtiği veya ARM model çalıştırmasının tamamlandığı iddia edilmiyor.

   **TUZAK**

   M3 Bu koşum Windows üzerindeki Docker Desktop emülasyonuyla Linux ARM64 çalıştırıyor. Derleme süreleri, HTTP zaman aşımı ve QEMU hatası fiziksel MacBook uyumluluğunu veya performansını belirlemiyor.

   **GÖZLEM**

   M4 Mevcut GPU paket kaynakları ve model paketleri korundu. Bağımsız paket ve paylaşımlı kitaplık incelemesi [kaynak incelemesinde](cpu-artifact-source-review.json) kayıtlı; paket içe aktarımı ve oluşturulmuş tek konuşmacılı ses örneği model kalitesi kanıtı değil.

   **AÇIK**

   M5 Gerçek MacBook kurulumu, yerel ARM üzerinde başarılı gerçek model HTTP çalıştırması ve sahip kabulü bu koşumda doğrulanmadı. Başarısız emülasyon koşumu, yerel ARM uygulamasında bir kusur bulunduğu teşhisini koymuyor.

   **YAN-ETKİ**

   M6 CPU ARM64 imajı ve derleme önbelleği oluşturuldu. Gözlenen HTTP zaman aşımı ve QEMU hatasından sonra yalnız kimliği doğrulanmış geçici deneme konteyneri kaldırıldı; [temizlik kaydı](cpu-aarch64-http-cleanup.json) çıkış kodu 137'yi açıklıyor. Mevcut uygulama konteynerleri korundu.

Son imaj `voiceup-inference:cpu-aarch64`, kimliği `sha256:b1fb44a1ced25fb328552f991572f1b88a4f0a54ac40d5c4e9d64a745a2cad43`; seçili teknoloji profili `kt-vibecoding-python-web-v2`.
