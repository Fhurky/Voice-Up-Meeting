# PRD — MacBook üzerinde tamamen yerel çalışma

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [005 — local-cpu-runtime](../../roadmap.md)
Kabul kaydı (10 Eylül 2026): Kullanıcının “her şeyi macbookunda halledicek, o yüzden
yapıyı ona da müsait hale getirsek” talimatı bu ortamı yetkilendirir. Kabul, gerçek
Mac uyumluluğu veya konuşmacı doğruluğu kanıtı değildir.

## Amaç ve aktörler

Yerel kullanıcı, projeyi kendi MacBook'unda Spark/NVIDIA cihazına ihtiyaç duymadan
kurar; 001 profil oluşturma ve ses tanıma akışını kendi yerel veritabanıyla kullanır.
Yerel yönetici kendi ilk hesabını oluşturur.

## Kararlar

Decision 1: Sabit `kt-vibecoding-python-web-v2` korunur. React/Vite, Python 3.13/
FastAPI, PostgreSQL 17/pgvector, SQLAlchemy/Alembic ve mevcut iç HTTP adaptörü kullanılır.
Docker Linux ortamında açık CPU çıkarımı eklenir: Apple Silicon için aarch64, Intel
için x86_64. CUDA/Spark modları açık cihaz denetimlerini korur; GPU hatası CPU'ya düşmez.
Bu karar 001 Decision 4'ün CPU'yu yalnız karşılaştırma ile sınırlandırmasını genişletir.

Decision 2: Aynı sabit ECAPA/Silero ağırlıkları, 192 boyutlu normalize vektörler,
cosine exact arama, 0.55/0.45/0.10 eşikleri ve 001 kalite kuralları korunur. Model
eğitimi/profil dönüşümü yapılmaz. CPU gecikmesi ölçülür; GPU hızı veya 50 kişide
yeni doğruluk iddiası verilmez. Mevcut 300 saniyelik iş zaman aşımı görünür kalır.

Decision 3: İlk kurulum internetten yalnız kayıtlı sürüm/hash ile model, paket ve
imaj hazırlar. Çalışma anında model indirme/internet erişimi yoktur. Native Apple
Metal bu CPU ortamının gereksinimi değildir. 002 toplantı transkripti ayrı kabul
kapsamında kalır; bu çalışma mevcut pilotun taşınabilirliğini sağlar.

## Gereksinimler

Requirement 1: CPU profili cihaz, mimari, PyTorch sürümü ve CPU derlemesini doğrular;
uyumsuz ortam başlamaz. Readiness gerçek model yükleme/ısınmasını bekler; sonuç
`device=cpu` döndürür, GPU bellek ölçüsü uydurmaz. Backend bu sonucu tipli sınırda kabul eder.

Requirement 2: Her iki mimari için mevcut sürümlerden türeyen incelenebilir artifact
manifesti/hash kilidi bulunur. Kilit kaynaktan deterministik üretilir; resmi metadata
ve bağımlılık kapanışı denetlenir. Mevcut GPU paketleri yeniden yazılmaz.

Requirement 3: İlk kurulum Docker/Linux/mimari önkoşullarını denetler, eksik yerel
sırları üretir, model/paketleri doğrular, imajları hazırlar, yerel veritabanı rolü ve
migration'ı uygular, servis hazırlığını kontrol eder ve ilk yönetici oluşturma
adımını açıklar. Tekrar mevcut sırları/veriyi korur. Günlük başlangıç indirme yapmaz;
eksik hazırlıkta adını belirten hata verir. Başka Docker projelerini durdurmaz.

Requirement 4: CPU Compose GPU rezervasyonu içermez; model yalnız özel ağda, web
yalnız loopback'te sunulur. Model non-root/read-only, tek iş kilitli kalır. Mevcut
yükleme/süre/tenant/yetki/idempotency sınırları korunur. Mod değişimi açıktır.

Requirement 5: Mac rehberi kendi GitHub hesabıyla erişim, önkoşullar, kurulum,
başlatma/durdurma/güncelleme ve hataları açıklar. Sırlar, kullanıcılar, sesler,
profiller/model paketleri Git ile taşınmaz. Gerçek Mac testi yoksa görünür kalır.

## Katmanlar ve doğrulama

API/şema/yeni migration/UI: N/A — mevcut ürün/veri sözleşmeleri korunur; yerel
kurulum mevcut migration'ları uygular. Yeni işçi/önbellek: N/A — 001 kullanılır.
Kubernetes CPU dağıtımı: N/A — bu yetenek yerel Compose ortamıdır; GPU chart hedefi
korunur. Gözlemlenebilirlik: hazırlık/cihaz alanı korunur, sır/ses/vektör loglanmaz.
Saklama, veri sınıflandırması ve yetki politikası 001'dir.

Testler profil hatalarını, CPU gerçek çıkarımını, çevrimdışı paket doğrulamayı,
Compose GPU ayrımını ve kurulum tekrar/eksik önkoşul davranışını kapsar. Linux CPU
kanıtı Mac kanıtı değildir. Tam profil kalite/güvenlik kapıları ve eksik ortamlar raporlanır.

## Kabul ölçütleri

- [x] Her iki CPU profili ve CUDA regresyon testleri geçer; 119 runtime testi.
- [x] İki mimarinin artifact/hash/bağımlılık kapanışı incelendi; gerçek CPU kanıtı raporlandı.
- [x] Kurulum/başlangıç koruma sözleşmeleri 30 testte, GPU'suz Compose iki mimaride doğrulandı; fiziksel Mac kabulü aşağıda ayrı açık.
- [x] CPU modeline gerçek TCP, uygulama API'sine ASGI ve gerçek PostgreSQL ile profil kayıt/tanıma doğrulandı; gerçek Mac tarayıcı kabulü aşağıda açık.
- [x] Mac rehberi, 143 testli tam kalite kapısı ve eksik ortam kanıtları birlikte kaydedildi.
- [ ] Gerçek MacBook üzerinde yerel kurulum/kayıt/tanıma doğrulanır.
