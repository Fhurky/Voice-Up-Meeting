# Koşum raporu — 2026-09-09 · Mevcut referans, Spark aktarım ve özel çıkarım testlerinin kapsamlı tabanı

1. Sonuç: Mevcut referans ve çıkarım paketleri geçti; ayrı çalıştırılan Docker kontrolleri varsayılan atlamalarını kapattı — birim 641 başarılı / tarayıcı 0 başarılı / atlanan 2; karar bekleyen: yok.
2. Koşulan:

   | Kapsam ve ortam | Komut / kanıt | Gözlenen sonuç |
   | --- | --- | --- |
   | Referans paketinin tamamı; Windows, `.venv`, Python 3.12.10 / pytest 8.4.2 | `python -m pytest tests --ignore=tests/test_public_speaker_dataset.py --ignore=tests/test_public_speaker_evaluation.py -o addopts= -ra --junitxml=…/reference-tests.xml`; [çıktı](reference-tests.txt), [JUnit](reference-tests.xml) | 569 başarılı / 10 atlanan; 235,82 saniye |
   | İsteğe bağlı gerçek Docker aktarımı; aynı Windows ortamı | `RUN_DOCKER_TRANSPORT=1`, `python -m pytest tests/test_spark_transport_config.py -k 'ipv4_proxy_reaches or private_proxy_rejects or nginx_live_transport_contract' -o addopts= -ra`; [çıktı](reference-transport-tests.txt), [JUnit](reference-transport-tests.xml) | 8 başarılı / 0 atlanan / 5 kapsam dışı; 17,38 saniye. Referans koşumundaki 8 aktarım atlaması kapandı. |
   | İlk çıkarım paketi denemesi; Windows backend `.venv`, Python 3.13.14 | `python -m pytest app/inference/tests -o addopts= -ra`; [çıktı](inference-tests.txt), [JUnit](inference-tests.xml) | Çıkış 2; `scipy` yokluğu nedeniyle `test_service.py` toplanamadı; 1 koleksiyon hatası |
   | Windows'ta bağımsız çıkarım kontrolleri; aynı Python 3.13 ortamı | `python -m pytest app/inference/tests/test_bundle.py app/inference/tests/test_runtime_profiles.py app/inference/tests/test_wheelhouse.py -o addopts= -ra`; [çıktı](inference-available-tests.txt), [JUnit](inference-available-tests.xml) | 43 başarılı / 0 atlanan; 0,59 saniye. Son Linux sonucunda tekrar sayılmadı. |
   | Çıkarım paketinin tamamı; mevcut x86_64 imajı, Linux Python 3.13.14 / pytest 9.1.1 | Ağ/GPU kapalı, salt okunur kök ve kaynak bağları; `python -m pytest app/inference/tests -o addopts= -p no:cacheprovider -ra --junitxml=/evidence/inference-linux-tests.xml`; [çıktı](inference-linux-tests.txt), [JUnit](inference-linux-tests.xml), [araç sürümleri ve imaj kimlikleri](inference-test-tools.json) | 64 başarılı / 0 atlanan; 3,03 saniye. Paket 7, runtime profili 28, HTTP/ses 21, wheelhouse 8. |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Windows referans ortamı Python 3.12'dir ve FastAPI yoktur; Python 3.13 backend ortamında SciPy yoktur. Tam çıkarım kanıtı bunlardan türetilmedi; mevcut Linux çıkarım imajında üretildi.
   M2 Çıkarım imajında pytest/httpx yoktur; çalışan backend'deki saf Python test araçları mevcut `requirements-dev.txt` sürümleriyle birebir doğrulanıp salt okunur bağlandı. İlk araç toplaması pytest'in `py.py` dosyasını atladığı için başladıramadı; aynı dağıtımdan tamamlandı ([ilk çıktı](inference-linux-bootstrap.txt)).
   M3 Başarılı sayısı 569 + 8 + 64 = 641'dir. Önceki 43 çıkarım kontrolü ve PowerShell uyum raporundaki 76 kontrol ayrıca tekrar sayılmadı.

   **GÖZLEM**
   M4 İki PowerShell motorunun tünel/sahiplik testleri referans paketinde geçti. Docker aktarımı 50 POST'u dört nginx worker'ında ve HTTP yetki/yol sınırlarında kendi geçici proxy'leriyle doğruladı.
   M5 Çıkarım testleri gerçek HTTP uygulaması ve WAV/FLAC çözmeyi sabit model yanıtları veren test nesneleriyle çalıştırır; GPU çıkarımı, gerçek konuşmacı doğruluğu veya üretim kabulü iddiası değildir.

   **AÇIK**
   M6 Windows hesabı sembolik bağlantı oluşturamadığı için `test_symlinked_model_is_rejected_before_docker` ve wheelhouse sembolik bağlantı senaryosu bu referans koşumunda atlandı; başarılı sayılmadı.
   M7 Geliştirilmekte olan `test_public_speaker_dataset.py` ve `test_public_speaker_evaluation.py` ana görev tarafından ayrı çalıştırılır. Tam uygulama kalite kapısı, tarayıcı ve gerçek veri değerlendirmesi bu raporun kapsamına dahil değildir.

   **YAN-ETKİ**
   M8 Test verileri geçici dizinlerde üretildi; Docker testleri kendi geçici kapsayıcılarını kaldırdı. Mevcut model servisi, GPU, SSH tüneli, kalıcı uygulama verisi ve başka projeler değiştirilmedi.
   M9 Yeni indirme ve kurulum yapılmadan hazırlanan araç kopyası yalnız Git dışında tutulan `outputs/public-speaker-evaluation/inference-test-tools-s49quli0` içindedir; test sırasında salt okunurdur. Kaynak/paket kilidi değişmedi; ölçüm dosyaları bu kanıt klasörüne yazıldı.
