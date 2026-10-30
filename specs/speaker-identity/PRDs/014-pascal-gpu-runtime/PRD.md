# PRD — Pascal NVIDIA GPU üzerinde yerel çalışma

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [014 — pascal-gpu-runtime](../../roadmap.md)
Kabul kaydı (28 Ekim 2026): Kullanıcının “Projeyi bu bilgisayarda hatasız çalışacak
hale getir, gerekli kurulumları da yap” talimatı, ikinci geliştirme bilgisayarındaki
GTX 1080 Ti (compute capability 6.1, 11 GB) için yerel CUDA ortamını yetkilendirir.
Kabul, bu GPU'da konuşmacı veya metin doğruluğu kanıtı değildir.

## Amaç ve aktörler

Yerel geliştirici, projeyi Pascal mimarili NVIDIA GPU'su olan Windows bilgisayarda
mevcut Docker/WSL2 akışıyla kurar; tek konuşmacılı pilot ve 002 toplantı akışı aynı
yerel veritabanı, model paketleri ve arayüzle çalışır. RTX 4060 bilgisayarı ayarsız
olarak mevcut `x86_64-cu128` profilinde kalır.

## Kararlar

Decision 1: Sabit `kt-vibecoding-python-web-v2` profili korunur. PyTorch 2.8.0
CUDA 12.8 derlemeleri sm_50–sm_61 çekirdeklerini içermediği için ayrı açık
`x86_64-cu126` çıkarım profili eklenir. Aynı PyTorch 2.8.0/torchaudio 2.8.0
sürümünün CUDA 12.6 yayın baytları kullanılır; diğer bütün base pinler
`requirements.txt` ile aynıdır. Toplantı eki kilidi değişmez.

Decision 2: Model kimlikleri, revizyonları, boyutlar (192/256), eşikler ve kalite
kuralları değişmez. CTranslate2 compute capability 7.0 altında `int8_float16`
çalıştırmadığı için Whisper bu profilde `int8` (int8 ağırlık, float32 aktivasyon)
ile yüklenir. Bu hesaplama türü farkı doğruluk eşdeğerliği iddiası değildir.

Decision 3: Profil seçimi makineye özgüdür ve Git'e girmez. `prepare-local-config.py`
ilk NVIDIA GPU'nun compute capability değeri 7.0 altındaysa `app/infra/.env` içine
profil, kilit ve wheelhouse anahtarlarını yalnız yoksa yazar. Tutarsız seçim açık
hata verir; mevcut değerler değişmez. Kubernetes chart hedefi değişmez.

## Gereksinimler

Requirement 1: Çıkarım servisi `x86_64-cu126` profilinde x86_64 mimarisi, PyTorch
2.8.0 ve CUDA 12.6 derlemesini doğrular, gerçek CUDA çekirdeği çalıştırır; uyumsuz
ortam başlamaz. Toplantı modelleri yalnız iki açık x86_64 CUDA profilinde yüklenir.

Requirement 2: CUDA 12.6 kilidi hash'li, deterministik ve mevcut kilitle eşlenmiş
olarak üretilir; wheelhouse hazırlayıcı yalnız kilitteki resmi PyTorch baytlarını
kabul eder. Bağımlılık kabul kaydı yeni kaynak dosyayı ve yayın tarihlerini içerir.

Requirement 3: Compose aynı Dockerfile'larla seçili kilidi ağsız derler ve seçili
profili servise iletir; varsayılan değerler mevcut cu128 davranışını korur.
`setup-local-meeting.py` seçili base wheelhouse'u doğrular.

Requirement 4: Windows kurulum rehberi WSL2, Docker Desktop, model/paket hazırlığı,
ilk yönetici ve başlatma adımlarını Pascal ayrımıyla açıklar.

## Katmanlar ve doğrulama

API/şema/migration/UI: N/A — ürün ve veri sözleşmeleri değişmez. Worker/önbellek:
N/A. Kubernetes: N/A — yerel Compose geliştirme ortamıdır; chart profili cu128 kalır.
Gözlemlenebilirlik: mevcut hazırlık/cihaz alanları korunur; sır/ses/vektör loglanmaz.

Testler profil kabul/ret durumlarını, Whisper hesaplama türü seçimini, kilit-wheel
eşleşmesini, yapılandırma algılama/tutarlılığını, Compose çözümlemesini ve wheelhouse
doğrulamasını kapsar. Gerçek GTX 1080 Ti üzerinde CUDA, model hazırlığı ve tarayıcı
akışı ayrıca gözlenir; gözlenmeyen adım başarılı sayılmaz.

## Kabul ölçütleri

- [x] Profil, kilit, yapılandırma ve Compose testleri geçer; cu128 regresyonu korunur.
- [x] CUDA 12.6 wheelhouse ve çıkarım imajı ağsız derlenir; GTX 1080 Ti CUDA hazırlığı gözlenir.
- [x] Toplantı imajı üç sabit modeli GTX 1080 Ti üzerinde hazır raporlar.
- [x] Yerel uygulama 8081'de açılır; yönetici girişi ve bir gerçek analiz akışı gözlenir.
