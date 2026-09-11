# PRD — Ethernet üzerinden Spark çıkarımı

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [004 — spark-remote-inference](../../roadmap.md)
Kabul kaydı: 9 Eylül 2026. Kullanıcı Spark'ı bu bilgisayara Ethernet ile bağladığını
ve bütün model hesaplamalarını orada çalıştırmak istediğini açıkça belirtti.
Bu kayıt dağıtım kapsamını kabul eder; cihaz erişimi, bağımlılık kabulü veya çalışma
kanıtını tamamlanmış saymaz. [Önceki cihaz planı](../../../../docs/DGX_SPARK_PLAN.md).

## Sonuç, aktörler ve sınır

Yetkili geliştirici mevcut Windows web uygulamasını kullanır; ses çözme, yeniden
örnekleme, VAD ve konuşmacı embedding çıkarımı Spark'taki ayrı model servisinde yapılır.
Model süreçleri yerel 4060'ta çalışmaz. PostgreSQL, profiller, iş kuyruğu, küçük vektör
karşılaştırmaları ve web/API Windows'ta kalır; bunlar yeni bir model eğitimi değildir.
Bu yetenek model algoritmasını değiştirmez; uzun toplantı ve canlı analiz 002/003'te kalır.

## Kararlar

Decision 1: `kt-vibecoding-python-web-v2` ve 001'in özel HTTP sözleşmesi korunur.
Model servisi veritabanına bağlanmaz; GitHub tokeni Spark çalışma ortamına taşınmaz.

Decision 2: Spark'ta model servisi yalnız loopback'te dinler. Windows–Spark arasında
kimliği doğrulanmış SSH tüneli kullanılır. SSH anahtarı, host anahtarı kaydı ve iç API
anahtarı yerel/gizli dosyalardadır; kaynak kodda veya logda bulunmaz. Host anahtarı
uyuşmazlığı reddedilir. Web tarayıcısı Spark servisine doğrudan bağlanmaz.

Decision 3: Ethernet arayüzünün fiziksel bağlantısı ile kullanılan IP rotası ayrı
kontrol edilir. Wi-Fi adresine SSH erişimi Ethernet üzerinden çalışma kanıtı değildir.
Var olan Wi-Fi/uzak erişim ve diğer cihaz bağlantıları korunur; yeni adres önceden
kontrol edilir. Doğrulanan rota Windows Ethernet 192.168.137.1 üzerinden Spark
enP7s7/192.168.137.2 adresine gider; Wi-Fi varsayılan rotası korunur.

Decision 4: ARM64 için ayrı runtime artifact seti hazırlanır. İlk araştırma adayı
Python 3.13, PyTorch/TorchAudio 2.8 ve CUDA 12.9'dur. Mevcut x86_64/CUDA 12.8 kilidi
korunur; yeni paketler resmî kaynak, yayın yaşı, hash, envanter ve uyumluluk kanıtı
ile ayrıca kabul edilmeden etkinleştirilmez. CUDA guard'ı kaldırılmaz; yalnız
kanıtlanmış açık runtime profilleri kabul edilir. CPU veya yerel GPU'ya sessiz dönüş yoktur.

Decision 5: Yerel model servisi yalnız Spark'ta gerçek kimlik çıkarımı ve uygulama
ulaşımı doğrulandıktan sonra durdurulur. Yerel mod ayrı, açık kullanıcı seçeneği olarak
korunabilir; uzak modda başlatıcı yerel model paketi veya yerel GPU gerektirmez.

Decision 6: 9 Eylül 2026 ek kabulü — kullanıcı Ethernet bağlantısından sonra bütün
hazırlığın otomatik veya tek betikle yapılmasını istedi. Bu bilgisayarda tek tıklama/
tek komut seçeneği uygulanır. İlk anahtar, adres, imaj ve gizli ayar hazırlığı korunur;
günlük açılışta yeni indirme, kurulum, yönetici parolası veya zamanlanmış görev gerekmez.

## Gereksinimler

Requirement 1: Salt okunur cihaz kontrolü mimari/OS, Python, GPU/sürücü/compute
capability, Docker runtime, kullanılabilir ortak bellek/disk ve ağ arayüzlerini raporlar.
Eksik araç veya giriş yetkisi başarı sayılmaz. Parola/env/sır/toplu dosya listesi okunmaz.

Requirement 2: Sabit ECAPA/Silero paketinin hashleri hedefte doğrulanır; runtime
internetten model veya bağımlılık indirmez. Yalnız gereken kaynak ve model dosyaları
aktarılır; var olan Spark projeleri, veri ve sanal ortamlar üzerine yazılmaz.

Requirement 3: Uzak başlatma/tünel konfigürasyonu açık hedef, kullanıcı, anahtar ve
host anahtarı bilgisi kullanır. Tünel açılma hatası ve kopma görünürdür; sonsuz/belirsiz
bekleme olmaz. HTTP anahtarı ve ses içeriği ağda SSH içinde taşınır.

Requirement 4: Docker Desktop'taki iç worker ağının tünele ulaşımı gerçek paketle
ölçülür. Windows'ta mevcut nginx üzerinde yayınlanmayan 9080 portu, açık Docker host
eşlemesinden doğrulanan tek IPv4 adresiyle loopback tüneline ulaşır. Erişilemeyen
IPv6 adresinin rastgele seçilmesine izin verilmez; adres çözümlenemezse başlatma
reddedilir. Spark'ta Docker'ın yalnız iç ağa bağlı servis
portunu yayınlamaması nedeniyle aynı kabul edilmiş nginx imajıyla ayrı bir aktarıcı
kullanılır; yalnız 127.0.0.1:8090 yayınlanır. İki aktarıcı da yalnız mevcut model
uçlarını iletir. Model, veri ve uygulama servisleri iç ağlarında kalır.

Requirement 5: Gerçek CUDA tensor işlemi, VAD, embedding, yetkisiz çağrı reddi ve
model/cihaz hataları doğrulanır. Aynı model revision'ı ve 192 boyut korunur; sayısal fark
mevcut referansla ölçülür. Değişiklik doğrudan Türkçe kimlik doğruluğu iddiası üretmez.

Requirement 6: Uygulama üzerinden gerçek iş Spark'a ulaşır; iş/model/sürüm/cihaz,
aktarım ve yürütme süreleri ayrı kanıtlanır. Tünel veya Spark kesildiğinde mevcut
deneme başına 300 saniye sınırı, en fazla iki deneme ve terminal hata davranışı korunur.

Requirement 7: Tek Windows başlatıcısı aynı anda bir kez çalışır; fiziksel Ethernet
rotasını sınırlı sürede doğrular, yerel Docker Desktop kapalıysa açıp Linux motorunu
bekler, yetkili SSH üzerinden hazırlanmış Spark Compose servislerini başlatır, beklenen
GPU modelini doğrular ve sahipli tüneli kurar veya yeniden kullanır. Yalnız doğrulanmış
fakat kullanılamayan kendi tünelini yenileyebilir. Sonra mevcut Spark uygulama
başlatıcısını çağırıp web/API hazırlığını kontrol eder ve sonucu gösterir.
Compose backend veya ön yüz kapsayıcısını yeniden oluşturduğunda eski IP'yi tutan
VoiceUp nginx, etkin Spark konfigürasyonu sınandıktan sonra yeniden yüklenir.
Konfigürasyon veya yeniden yükleme hatası başarı sayılmaz; dış web/API hazır olma
kontrolü korunur. Bu işlem yalnız aynı projenin nginx sürecini hedefler.
SSH üzerinden yürütülen hazırlık kaynağı, Windows konsol kod sayfasından bağımsız
olarak BOM içermeyen UTF-8 baytlarıyla aktarılır; yerel konsol ayarı kalıcı değiştirilmez.
002'nin kabul edilmiş özel toplantı uçları proxy şablonuna eklendiğinde hazırlanmış
runtime yardımcısının sabit SHA-256 denetimi aynı incelenmiş kaynakla birlikte
güncellenir. Çalışma anında yeni hash hesaplayıp kabul etmez; değişmiş veya eski
hazırlık dosyası Docker işlemi başlamadan reddedilir. Eski hazırlanmış cihazın
şablonunu güncellemek ayrı yetkili hazırlama işlemidir; başlatıcı uzaktaki dosyayı
kendiliğinden düzeltmez ve yeni toplantı modelinin hazır olduğunu varsaymaz.

Requirement 8: Masaüstü motoru, kablo, SSH, hedef ayarları veya model hazır olmazsa
adımı belirten güvenli hata ve başarısız çıkış kodu döner. Wi-Fi/CPU/yerel GPU'ya
otomatik dönüş, Docker motoru sıfırlama/değiştirme, genel ağ taraması, yeni imaj
indirme veya başka projeleri durdurma yapılmaz. İlk kurulumu eksik başka bir
bilgisayarda özel bağlantı bilgileri uydurulmaz; eksik önkoşul açıkça bildirilir.

## Katmanlar, güvenlik ve dağıtım

API/şema/migrasyon N/A — 001'in iş ve model sözleşmesi değişmez. Ön yüz işlev değişimi
N/A — mevcut iş durumu ekranı kullanılır; yeni GPU modeli etiketi uydurulmaz. Ses/
profil saklama ve tenant/RBAC 001'deki gibidir. SSH erişimi yalnız verilen kullanıcı
hesabındadır; sudo veya ağ değişikliği ihtiyaçları cihazda incelenir.

Mevcut backend/inference ayar sınırları korunur; yeni runtime ayarı gerekiyorsa bütün
örnek/Compose/Secret yüzeyleri birlikte güncellenir. Yerel masaüstü tüneli ayrı dağıtım
profilidir. Kubernetes'te mevcut ClusterIP/internal-registry, non-root/read-only,
GPU kaynak ve NetworkPolicy kuralları korunur; gerçek Spark kümesi kurulumu bu
kullanıcı isteğinde yoktur. Artifact mimarisi ve runtime değerleri dağıtım kanıtında
belirtilir. Kaynak/pinler değiştiğinde kalite, bağımlılık ve güvenlik kapıları denenir.

## Kanıt ve kabul ölçütleri

- [x] Spark oturumu yetkili anahtarla açılır; mimari/GPU/Docker/ağ envanteri vardır. Kanıt: `docs/evidence/2026-09-09-spark-runtime/ethernet-and-docker.json`.
- [x] Kullanılan uygulama rotası fiziksel Ethernet'e gider; Wi-Fi bağlantısı korunur. Kanıt: `ethernet-and-docker.json` ve gerçek iş korelasyonu.
- [x] ARM64 runtime ve model paketi doğrulanır; gerçek CUDA/VAD/embedding çıkarımı geçer. Kanıt: aynı klasörde `cuda-import-probe.json` ve `cuda-smoke.json` (9 kontrol).
- [x] LAN'da açık HTTP modeli yoktur; SSH/host anahtarı/iç API yetkisi çalışır. Kanıt: `service-verification.json`, `host-key-rejection.json`.
- [x] Windows worker → özel proxy/tünel → Spark zinciri gerçek işte çalışır. Kanıt: `application-remote-correlation.json`; 25 başarılı iş Spark kaydıyla eşleşir.
- [x] Uzak modda yerel GPU servisi kapalıdır; kopmada yerel/CPU fallback oluşmaz. Kanıt: `application-live.json`, `windows-active-mode.json`, `no-cdi-failure.json`.
- [x] Oturum/kesinti/yeniden başlatma ve uygun otomatik testler raporlanır. Kanıt: `service-restart.json`, `focused-tests.xml`, `quality-gate.txt`. Güvenlik aracı eksikliği ayrı açık madde olarak kalır.
- [x] Hız, ortak bellek ve aynı-revision sayısal karşılaştırma ölçülür; kişi doğruluğu ayrı tutulur. Kanıt: `application-performance-comparison.json`, `benchmark-memory.json`, `numerical-comparison.json`.
- [x] Tek komut/çift tıklama ile Ethernet → Docker Desktop → Spark servisleri → tünel → uygulama hazırlanır; ikinci çalıştırma mevcut sağlıklı servisleri kullanır. Kanıt: `docs/evidence/2026-09-09-spark-one-click/README.md`; durmuş proje servislerinden canlı geri dönüş ve aynı tünel PID'siyle tekrar geçti. Docker Desktop'ın soğuk başlangıç dalı otomatik sınır testi düzeyindedir.
- [x] Kablo/SSH/Docker/hedef ayarı hatası ve eşzamanlı başlatma açık hata ile durur; durdurulmuş proje servisleri aynı başlatıcıyla geri gelir, başka projeler korunur. Kanıt: 81 odaklı test ve canlı başlangıç sonrası profil/diğer proje karşılaştırması; fiziksel kablo çıkarma ve tüm cihaz reboot'u çalıştırılmadı.

Open Question 1: Çözüldü — gerçek ARM64 CUDA, VAD ve ECAPA geçti. Torch'un SM121 üst sınır uyarısı raporda korunur; bütün kernel ailelerine uyum genellenmez.
Open Question 2: Çözüldü — iç nginx → doğrulanan IPv4 → SSH → Spark loopback aktarımı gerçek işlerle doğrulandı.

Kanıtlar [çalışma raporunda](../../../../docs/evidence/2026-09-09-spark-runtime/README.md)
birlikte değerlendirilir. Çevrimdışı güvenlik araçları ve gerçek kişi verisiyle L3
sahip kabulü bulunmadığından üretim/güvenlik kabulü iddia edilmez.
