# Koşum raporu — 2026-09-09 · yerel konuşmacı pilotunun bütünleştirilmesi

1. Sonuç: Yerel pilot, gerçek CUDA çıkarımı ve teknik gecikme hedefi doğrulandı; gerçek kişi doğruluğu ve dış dağıtım kapıları eksik — uygulama birim 65 başarılı / PostgreSQL entegrasyon 15 başarılı / tarayıcı 3 başarılı / çalışan otomatik testlerde atlanan 0; karar bekleyen: yok. Güvenlik ve kalıcı Playwright kapıları ortam nedeniyle çalıştırılamadı; tam ürün kabulü ilan edilmedi.
2. Koşulan: Sabit teknoloji profili `kt-vibecoding-python-web-v2`; Windows host, Docker Linux CPython 3.13, PostgreSQL 17.11/pgvector 0.8.6, Node 22.23.2.

   | Kanıt | Gözlenen sonuç |
   | --- | --- |
   | [Son uygulama kalite kapısı](contract-regression-run-report.md) | 59 backend testi (44 birim, 15 gerçek PostgreSQL), 21 frontend testi; statik, şema, OpenAPI/tip, config, bağımlılık/yönetişim ve chart başarılı. Önceki 53 test koşumu [ayrı kayıttadır](backend-run-report.md). |
   | [Sözleşme ve benchmark aracı](contract-benchmark-run-report.md) | Tenant header export düzeltmesi 10 test; benchmark aracının 6 testi başarılı; araç testi GPU ölçümü değildir. |
   | [Canlı tarayıcı](../../../app/frontend/VERIFICATION.md) | 3 canlı CUA akışı: salt okunur rol, negatif yükleme/yenileme ve kapsamlı gerçek GPU profil/tanıma/silme akışı. Son senaryodaki 9 işin 2 hatası beklenen retlerdir. |
   | [Yerel hazırlık ve araştırma regresyonları](setup-review-run-report.md) | 219 test başarılı, 0 atlanan; .env koruması, VoiceUp proje sabitleme ve indirmesiz başlangıç doğrulandı. |
   | [Model servisi](../../../app/inference/VERIFICATION.md) | 36 birim testi ve [gerçek GPU/network-none HTTP kontrolü](../../../app/inference/evidence/cuda-smoke.json) içinde 12 başarılı kontrol; 6 WAV/FLAC çıkarımı, 192 boyut, birim norm, CUDA 12.8. |
   | Gerçek model süre/bellek | Teknik 30 saniyelik örneklerde özel HTTP 0,610–0,710 saniye; PyTorch tepe allocated 190,21 MiB, reserved 260 MiB. Bunlar uygulamanın 20 iş p95 ölçümü veya toplam cihaz kullanımı değildir. |
   | [Servis başlangıcı](../../../app/inference/evidence/compose-startup.json) | Yeni süreçten application ready 4,909 saniye, ilk /ready 200 kaydı 5,380 saniye. Image üretimi/container oluşturma hariç; dosya cache'i önceki testten sıcak. |
   | [20 iş GPU ölçümü](4060-benchmark.json) | Bir dışlanan ısınma + 20 ardışık tek denemeli CUDA işi; 20/20 recognized. İşlem p50 0,786 sn, p95 0,869 sn, max 0,885 sn; 30 sn hedefi geçti. |
   | Kuyruk ve gözlenen süre | Kuyruk p95 1,951 sn; sunucu toplamı p95 2,721 sn; istemcinin polling ile gözlediği toplam p95 3,146 sn. Tek dosyanın yüklenmesi 0,024 sn; ölçüm işlerine dahil değil. |
   | [Benchmark ortamı](4060-environment.json) | Başlangıçta tek teknik profil, boş kuyruk; en yüksek örneklenen toplam GPU kullanımı 1519/8188 MiB. Diğer host süreçlerini içerir, allocator tepe değeri değildir. |
   | Linux shell taşınabilirliği | Son düzenlemede kalite kapısının satır sonları LF olarak doğrulandı; gerçek Linux container'ında `sh -n` ve veritabanı kurulum hatası regresyonu (1 test) başarılı. |
   | Yerel başlangıç | `scripts/start-local.ps1` gerçek Docker üzerinde exit 0; mevcut 12 VoiceUp servisi korundu, adres 8081, yeni image indirmesi yok. |
   | Docker GPU erişimi | Sabit Python container'ında `nvidia-smi`: RTX 4060 Laptop, 8188 MiB, sürücü 610.62. Model çıkarımı kanıtı değildir. |
   | PostgreSQL runtime rolü | `voiceup_runtime`: superuser/createdb/createrole/public CREATE tümü false; migration owner ayrı süreçte. |
   | Helm | 46 kaynak × 2 fixture ve renderer self-test başarılı; gerçek Kubernetes dağıtımı yapılmadı. |
   | [Güvenlik kapısı](security-gate.txt) | Exit 2: gerekli gitleaks aracı bulunamadı; taramalar başarılı sayılmadı. |

3. Maddeler:

   **KUSUR**

   M1 Kalite kapısı başarısız test veritabanı kurulumunu geçerli sanabiliyordu; açık hata dönüşü ve benzersiz `_test` adı eklendi, `tests/test_quality_gate_failure.py` ile korundu.

   M2 Windows bind mount dosya modları Ruff kontrolünü bozdu; kapı kaynak içeriğinin geçici kopyasında modları normalleştiriyor. Kaynak kuralları gevşetilmedi.

   M3 Alpine image'ında ses native kütüphanesi eksikti; sabit hashli/signed APK paketi ve libsndfile yükleme yolu doğrulandı. Web image'ına Torch eklenmedi.

   M4 Geçerli sürelerin kayan nokta yuvarlaması iki tüketicide yanlış reddediliyordu; üreticiyle aynı tolerans ve CUDA-only yanıt kontrolü eklendi. Beş yeni sınır regresyonu geçti.

   M5 CUDA lock içindeki pip index direktifi ek CUDA index'ini kaldırıyordu; runtime sürümleri ve hashleri korunarak lock üretimi düzeltildi, kalıcı doğrulanmış wheelhouse ile ağsız kurulum eklendi.

   **TUZAK**

   M6 Host Node 26 ürün ortamı değildir; build/test Node 22 container'ında çalıştı. Kök Python 3.12 CPU prototipi ile ürün Python 3.13 GPU ortamı ayrı tutuldu.

   M7 Tekrar edilmiş resmi açık örnekler teknik bağlantı ve süre ölçümü içindir; başka oturum doğruluğu veya onlarca kişi başarısı değildir.

   **GÖZLEM**

   M8 8080/5432 üzerindeki mevcut diğer uygulama çalışmayı sürdürdü; VoiceUp ters vekili yalnız loopback 8081'e açıldı. Veri ve model servisleri iç ağdadır.

   M9 Bağımlılık kaydı 107 benzersiz koordinatı ve resmi release/digest kanıtlarını içerir; yerel kaynak/uyum incelemesi kurum yayın kabulü sayılmaz.

   **AÇIK**

   M10 Gerçek kişi tanıma başarısı ve onlarca kişilik galeri henüz ölçülmedi. 20 iş ölçümü tek kayıtlı teknik profile ve aynı tekrarlı örneğe aittir; ayrı oturum ya da kapasite kanıtı değildir.

   M11 Beş kişiden ayrı oturum kayıtları ile bilinmeyen kişi sorguları yok; 14/15 doğru kabul ve 0/10 yanlış kabul hedefi ölçülemedi.

   M12 Kabul edilmiş güvenlik araç/bundle ortamı ve Playwright paketi yok; bu kapılar açık. Canlı CUA kullanımı kalıcı Playwright senaryosunun çalıştığı iddiası değildir.

   **YAN-ETKİ**

   M13 Kullanıcının kabul ettiği pilot için backend/frontend/inference, dört domain tablosu, eklemeli migration, yerel worker ve GPU/chart yüzeyleri oluşturuldu; özgün boilerplate kaynak kopyası korundu.

   M14 Tek teknik profil ve 31 terminal deneme/benchmark işi bırakıldı; yerel deneme hesapları, ses fixture'ları, image/model cache'i ve Git dışı ayarlar oluşturuldu; eksik JWT sırrı rastgele üretildi, backend/worker yenilendi, mevcut hesapla giriş tekrar HTTP 200 verdi. Sırlar yazdırılmadı.

   M15 Güncel kullanım [yerel pilot rehberinde](../../LOCAL_PILOT.md), tamamlanan/açık işler [görevlerde](../../../specs/speaker-identity/PRDs/001-local-speaker-pilot/tasks.md) izlenir.
