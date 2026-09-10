# Koşum raporu — 2026-09-10 · CPU paket manifestleri, belirlenimci kilitler ve çevrimdışı paket bütünlüğü.

1. Sonuç: İki CPU paket sözleşmesi ve ilgili regresyon testleri geçti — birim 66 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam | Komut veya sınır | Gözlenen sonuç |
   | --- | --- | --- |
   | Windows, CPython 3.13.14 | `python -B -m pytest tests/test_cpu_wheelhouse.py -q -p no:cacheprovider -o addopts=` | Kırmızı: gerekli CPU dosyaları bulunmadığından 0 başarılı, 8 başarısız; [JUnit](cpu-artifacts-red.xml), [çıktı](cpu-artifacts-red.txt). |
   | Windows, CPython 3.13.14 | CPU sözleşmeleri, `tests/test_spark_wheelhouse.py`, `app/inference/tests/test_wheelhouse.py` | Yeşil: 64 başarılı, 1 atlanan; [JUnit](cpu-artifacts-green.xml), [çıktı](cpu-artifacts-green.txt). |
   | Linux x86_64, CPython 3.13.14, mevcut sabitlenmiş imaj; ağ kapalı, kaynak salt okunur | Aynı üç paket, `python -m pytest -p no:cacheprovider -o addopts=` | 65 başarılı, 0 atlanan; [JUnit](cpu-artifacts-native.xml), [çıktı](cpu-artifacts-native.txt). Bu koşum paket araçlarını denetler; CPU üzerinde model çalıştırmaz. |
   | Windows, CPython 3.13.14 | ARM OpenMP imaj sözleşmesi, ardından aynı üç paket | Kırmızı: 1 başarısız; yeşil: 65 başarılı, sembolik bağlantı nedeniyle 1 atlanan; [kırmızı](cpu-openmp-red.xml), [yeşil](cpu-openmp-green.xml). |
   | Linux x86_64, CPython 3.13.14; ağ kapalı, kaynak salt okunur | ARM OpenMP imaj sözleşmesi dahil son üç paket | 66 başarılı, 0 atlanan; [JUnit](cpu-artifacts-final.xml), [çıktı](cpu-artifacts-final.txt). |
   | Windows | `ruff check` ve `ruff format --check tests/test_cpu_wheelhouse.py` | İlk koşumda ve OpenMP regresyonu eklendikten sonra başarılı; [son çıktı](cpu-artifacts-final-lint.txt). |
   | Windows, mevcut manifest indiricisi | `prepare-spark-wheelhouse.py --manifest app/inference/cpu-{arch}-wheelhouse-manifest.json --write-lock app/inference/requirements.cpu-{arch}.txt` | İki belirlenimci özet kilidi ve bunları koruyan sekiz sözleşme testi. |
   | Windows, mevcut manifest indiricisi | Aynı araç, `--directory models/inference-cpu-{arch}-wheelhouse` seçeneğiyle | x86_64: 45 doğrulanmış dosya yeniden kullanıldı, 2 indirildi; aarch64: 34 yeniden kullanıldı, 13 indirildi. Her tam wheel dosyası boyut ve SHA256 denetimlerini geçti; [x86 çıktısı](cpu-x86_64-download.txt), [ARM çıktısı](cpu-aarch64-download.txt). |
   | Windows, hedef Linux CPython 3.13.14 üstveri değerlendirmesi | Tüm yerel wheel dosyalarının özetleri, kök dağıtım METADATA dosyası, Python sürüm koşulları ve etkin bağımlılıkların kapanımı | Her mimaride 47 wheel ve 65 etkin bağımlılık ilişkisi; kilitli paketlerin tamamına 12 doğrudan sürüm sabitlemesinden ulaşılıyor; [ayrıntılı doğrulama](cpu-wheelhouse-verification.json). |

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: CPU paket kaynakları eksikti; iki manifest, doğrudan sürüm kaynakları, üretilmiş kilitler ve CPU Dockerfile mevcut yayımlanmış sürümleri koruyor. `tests/test_cpu_wheelhouse.py` ile korunuyor.

   M2 DÜZELTİLDİ: İlk ARM64 içe aktarma denemesi `libgomp.so.1` dosyasını bulamadı; CPU imaj hazırlığı mevcut Torch wheel kitaplığını doğrulayıp root sahipliğinde, çalışma zamanında yazılamayan bir dizinde sembolik bağlantı oluşturuyor. [Hata](cpu-aarch64-probe-failure.txt), [geçici gerçek bağlantı denemesi](cpu-aarch64-alias-probe.txt), [koruyucu regresyon](cpu-openmp-red.xml).

   **TUZAK**

   M3 ARM64 TorchAudio, `+cpu` eki olmadan `2.8.0` sürümünü kullanıyor; CPU yayımlayıcı adresi ve SHA256 özeti aynı dosya adlı CUDA paketinden ayırıyor. Dosyanın bulunması veya yalnız sürüm metni kabul kanıtı için yeterli değil.

   M4 Windows, mevcut bir olumsuz testin kullandığı sembolik bağlantıyı oluşturamadı; aynı test Linux üzerinde geçti. Windows ve Linux tekrarları benzersiz test sayısına birlikte eklenmiyor.

   M5 İlk üstveri incelemesi setuptools içine gömülmüş bağımlılıkların METADATA dosyalarını seçerek durdu; tamamlanan kontrol, bağımlılıkları değerlendirmeden önce wheel dosyasının tek kök dağıtım METADATA dosyasını seçiyor.

   **GÖZLEM**

   M6 Mevcut CUDA sürüm kaynakları, kilitleri, wheel dizinleri ve model paketleri korundu. CPU kümeleri 45 ortak paket sürümünü koruyup kesin CPU Torch/TorchAudio dosyalarını ekliyor; NVIDIA kitaplıkları ve Triton bulunmuyor.

   **AÇIK**

   M7 Bağımsız kaynak kabulü ile çalışma zamanı ve derleme kanıtları bu dizinde ayrı kaydedildi; paket kontrolleri tek başına gerçek Mac uyumluluğunu veya konuşmacı doğruluğunu kanıtlamıyor.

   **YAN-ETKİ**

   M8 Yedi CPU kaynak/kilit/derleme dosyası ve dokuz sözleşme testi eklendi; Git tarafından izlenmeyen CPU wheel dizinleri doğrulanmış paket dosyalarını içeriyor. [Kaynak bağları](cpu-artifact-source-manifest.json), bu alt görevin sekiz kaynak dosyasını kaydediyor.

Seçili teknoloji profili `kt-vibecoding-python-web-v2`. Yapılandırılmış koşum raporu, birincil yerel ayar olan Türkçenin tam eşlemesini kullanıyor; teknik JSON üstverisi ve ham araç çıktıları özgün dilinde korunuyor.
