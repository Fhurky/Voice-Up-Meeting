# Koşum raporu — 2026-09-09 · Spark üzerinde ARM64 CUDA çıkarımı ve özel model servisi

1. Sonuç: Native çıkarım ve Spark loopback servisi L2 düzeyinde doğrulandı — birim 9 başarılı / gerçek HTTP 23 başarılı / CUDA tensor 1 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam | Komut veya sınır | Gözlenen sonuç |
   | --- | --- | --- |
   | Windows, Python 3.13 | `app/backend/.venv/Scripts/python.exe -m pytest tests/test_spark_service_config.py -q` | 9 başarılı; gerçek Compose çözümlemesi, yalnız kurgu ayarları |
   | Windows | `ruff check` ve `ruff format --check tests/test_spark_service_config.py` | Geçti; 1 dosya |
   | Spark, Linux ARM64 | `Dockerfile.spark`, `--network=none`, yerel wheelhouse, hash zorunlu çevrimdışı kurulum | 48 paket kuruldu; `pip check` geçti; [build çıktısı](native-build.txt) |
   | Spark, GB10 / CUDA 12.9 | Gerçek CUDA matrisi, paket importları, UID ve ağ kontrolü | 1 başarılı; [komut ve sonuç](cuda-import-probe.json) |
   | Spark, geçici CDI kapsayıcısı | Mevcut `app/inference/smoke_cuda.py`, tek kurgu WAV ve onun FLAC karşılığı | 9 HTTP kontrolü başarılı; [sonuç](cuda-smoke.json), [tam komut](smoke-execution.json) |
   | Spark, kalıcı loopback relay | Hazırlık, anahtar, yöntem/yol/boyut sınırları ve gerçek ses POST isteği | 11 HTTP kontrolü başarılı; [sonuç ve izolasyon](service-verification.json) |
   | Spark, geçici GPU aygıtsız kapsayıcı | Aynı imaj/model ile gerçek başarısızlık sınırı | 3 HTTP kontrolü başarılı; [komut ve sonuç](no-cdi-failure.json) |

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: Docker 29.2.1 iç ağa bağlı modelin port isteğini kaydetti fakat yayımlamadı; ayrı loopback nginx relay ile çözüldü. [İlk başarısızlık](service-internal-publish-failure.json), [koruyan test](../../../tests/test_spark_service_config.py), [son durum](service-verification.json).

   **TUZAK**

   M2 Torch derlenmiş mimari listesi `sm_120` ile bitiyor; GB10 `sm_121` için üst sınır uyarısı mevcut. Gerçek tensor ve ECAPA geçti; bütün CUDA işlemlerinin uyumu veya özel SM121 derlemesi iddia edilmez. [Uyarı](cuda-import-probe.stderr.txt).

   M3 Model başlatma 2,253 saniye; kurgu WAV/FLAC özel HTTP çağrıları 0,168–0,184 saniye. Bunlar Spark içindeki tek istek ölçümleridir; temiz sürücü/disk başlangıcı, Ethernet, Windows kuyruğu veya p95 değildir. [Ölçüm kapsamı](smoke-execution.json).

   M4 PyTorch tepe ayrılmış belleği 189.954.560 bayt, rezervi 211.812.352 bayt; yerleşik modelleri içeren süreç ölçümüdür. GB10 ortak sistem belleğinin toplam tüketimi olarak yorumlanmaz. [Telemetri](fixture-vector-metadata.json).

   **GÖZLEM**

   M5 Python 3.13.14 / aarch64, Torch 2.8.0+cu129, TorchAudio 2.8.0, SpeechBrain 1.1.1 ve gerçek GB10 CC12.1 doğrulandı. [Ortam](cuda-import-probe.json), [imaj](image.json), [tekil kaynak hashleri](source-manifest.json).

   M6 Model yalnız iç ağda, UID10001, salt okunur kök ve 512 MiB tmpfs ile çalışıyor; IPv4/IPv6 dış bağlantıları ENETUNREACH verdi. Relay yalnız `127.0.0.1:8090` yayımlar; Ethernet/Wi-Fi adreslerinde 8090 reddedildi. Relay ayrı edge ağına bağlıdır; dışa çıkış engeli iddiası model kapsayıcısına aittir. [Kanıt](service-verification.json).

   M7 GPU aygıtı yokken `/live` 200, `/ready` ve yetkili çıkarım POST isteği `503 cuda_unavailable` döndü; model yüklenmedi ve embedding üretilmedi. [Gerçek negatif test](no-cdi-failure.json).

   **AÇIK**

   M8 Windows tüneli/uygulama kuyruğu, kesinti-yeniden başlatma, cihazlar arası sayısal karşılaştırma ve genel kalite/güvenlik kapıları ana bütünleştirme görevinde raporlanır; bu rapor onları tamamlandı saymaz.

   M9 Kurgu örnek tekrarlanmış tek konuşmacı sesidir; doğal Türkçe toplantılarda veya onlarca kayıtlı kişide doğruluk kanıtı değildir. Temsili veriyle sahip kabulü L3 bu koşumda yapılmadı.

   **YAN-ETKİ**

   M10 İki Compose servisi ve yalnız bu projeye ait iki ağ oluşturuldu; doğrulanmış model/kaynaklar korundu. Sadece iç servis anahtarı şifreli SSH girdisiyle hedefin `0600` özel dosyasına aktarıldı. [Başlatma ve dosya hashleri](service-start.json).

   M11 Native imaj ve içerik adresli kaynak sürümü üretildi; tek açık kaynak kurgu WAV aktarıldı. Vektör yalnız Git dışındaki özel çıktıya yazıldı; bu dizindeki kanıtlarda vektör veya sır yoktur. [Aktarım](release-transfer.json), [vektör metaverisi](fixture-vector-metadata.json).

   M12 Compose, boş ayar şablonu, relay yapılandırması ve 9 test eklendi. İlk kırmızı koşum eksik dosyaları; relay kırmızı koşumu eksik erişim katmanını yakaladı. Son Python 3.13 koşumu ve biçim/lint kontrolleri geçti.

Doğrulanan teknoloji profili: `kt-vibecoding-python-web-v2`. Model kimliği
`speechbrain/spkrec-ecapa-voxceleb`, revision
`0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`, boyut 192 olarak korundu.
Tekrarlama ve işletim komutları [commands.md](commands.md) içindedir.
