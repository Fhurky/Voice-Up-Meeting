# PRD — Kurum içi GPU platformunda çalışma

Status: Draft

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [018 — institutional-gpu-platform](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (29 Ekim 2026): Kullanıcı ürünün kurum ağı içinde çalışacağını, GPU'lara
kurumsal bir Kubernetes GPU zamanlayıcı platformu üzerinden erişildiğini ve dil
modellerinin bu platformda OpenAI uyumlu `/v1` uç noktalarıyla, ağırlıkları paylaşımlı
model deposunda tutularak sunulduğunu bildirdi. Bu taslağın platform ekibinin
cevaplarıyla (Open Question 1–6) tamamlanması ve açıkça kabul edilmesi gerekir.

## Amaç ve kapsam

VoiceUp'ın konuşma modelleri (ASR, konuşmacı ayırma, ses izi, konuşma tespiti) kurumun
GPU havuzunda ürünün kendi inference iş yükü olarak çalışır. Metin inceleme ve sonraki
dil modeli yetenekleri, kurumun mevcut OpenAI uyumlu dil modeli uç noktasını kullanabilir.
Çalışma anında internet erişimi ve model indirme yoktur. Model kimlikleri, eşikler,
veri şeması ve API sözleşmesi değişmez.

## Kararlar (taslak)

Decision 1: Konuşma modelleri kurumun dil modeli sunucusuna taşınmaz; bu sunucu metin
üretimi içindir. Mevcut inference servisi ayrı bir GPU iş yükü olarak çalışır; backend ve
worker ona yalnız küme içi HTTP ve Secret'tan gelen iç anahtarla erişir.

Decision 2: Tam GPU yerine platformun kesirli GPU tahsisi kullanılır. Ayrılacak bellek
ölçümle belirlenir: depodaki ölçümde Community-1 tepe ayrılmış belleği 1,963 GiB'dir;
Whisper ve ECAPA ile toplam tepe hedef GPU'da ayrıca ölçülür. Ölçüm olmadan değer uydurulmaz.

Decision 3: Model dosyaları sabit hash'li paketler olarak bir kez hazırlanır, kurumun
onaylı aktarım süreciyle salt okunur model deposuna konur ve inference podu tarafından
salt okunur bağlanır. Mevcut paket doğrulaması (`verify_meeting_bundle`, ECAPA paket
hash'leri) başlangıçta çalışır; eksik veya değişmiş paket hazır sayılmaz.

Decision 4: İmaj çalışma profili hedef donanıma göre seçilir. Kullanıcı hedef GPU'ları
H200 (compute capability 9.0) veya B300 (Blackwell Ultra, 10.3) olarak bildirdi.
x86_64 düğümlerde mevcut `x86_64-cu128` profili kullanılır: PyTorch 2.8.0 CUDA 12.8
derlemesi `7.0;7.5;8.0;8.6;9.0;10.0;12.0` mimarileri için kod içerir (v2.8.0
`.ci/manywheel/build_cuda.sh`); sm_100 kodu aynı ana sürümün 10.3'ünde çalışabilir.
Kabul edilen CTranslate2 4.8.1 kütüphanesi `compute_86` PTX'i taşır; sürücü bunu 9.0 ve
10.x'te ilk yüklemede derler, bu nedenle salt okunur kök dosya sisteminde
`CUDA_CACHE_PATH` boyutu sınırlı yazılabilir bir birime yönlendirilir. Bu çıkarımlar
hedef GPU'da canlı doğrulanmadan kabul edilmez. ARM tabanlı (Grace) düğümlerde toplantı
eki için ayrı bir aarch64 profili ve GPU destekli CTranslate2 derlemesi gerekir; bu,
ayrı bir PRD ve doğrulama işidir.

Decision 5: Metin inceleme sağlayıcısı ayar ile seçilir: mevcut yerel Ollama adaptörü
korunur, yanına OpenAI uyumlu `/v1/models` ve `/v1/chat/completions` adaptörü eklenir.
Model kimliği yapılandırmada sabitlenir ve her çağrıda uç noktanın sunduğu modelle
karşılaştırılır; kimlik bilgisi yalnız Secret'tan okunur. Toplantı içeriği yalnız bu
kurum içi uç noktaya gider.

Decision 6: Helm chart'ına platform zamanlayıcısı, proje/kuyruk etiketi, kesirli GPU
isteği ve var olan model deposunu bağlama değerleri overlay alanı olarak eklenir;
varsayılan render ve mevcut ağ, güvenlik ve probe kuralları değişmez.

## Gereksinimler

Requirement 1: Chart overlay alanları ve render/sözleşme testleri; platform değerleri
olmadan mevcut render çıktısı değişmez.

Requirement 2: OpenAI uyumlu metin inceleme adaptörü, tipli ayarlar, `.env.example`,
Compose ve chart Secret yüzeyi; yapılandırma senkron kontrolü ve adaptör testleri.

Requirement 3: Model yerleştirme rehberi: paket hazırlama, hash doğrulama, aktarım,
salt okunur bağlama ve `--verify` adımları.

Requirement 4: Hedef platformda `/meeting-ready`, bir örnek toplantı analizi ve metin
inceleme isteğiyle canlı doğrulama; GPU belleği ve süre ölçümü.

## Güvenlik ve veri

Toplantı sesi kişisel veridir; konuşmacı ses izi biyometrik veridir ve kurumun onaylı
ortamı dışına çıkmaz. Ses, metin, vektör ve kimlik bilgisi loglanmaz. Bütün iş yüklerinin
giriş/çıkış ağ politikaları tanımlıdır; inference ve dil modeli uç noktalarına yalnız
backend ve worker erişir. Şema/migration: N/A. Vektör sözleşmesi: N/A — model, boyut ve
eşikler değişmez. UI: N/A.

## Kabul ölçütleri

- [ ] Open Question 1–6 platform ekibinin yazılı cevaplarıyla kapatılmıştır.
- [ ] Chart overlay ve OpenAI uyumlu adaptör testleri, yapılandırma senkronu ve tam kalite kapısı geçer.
- [ ] Hedef platformda inference hazırlığı, örnek toplantı ve metin inceleme canlı gözlenir; GPU belleği ve süre kaydedilir.

Open Question 1: GPU'lar H200 veya B300; düğüm CPU mimarisi x86_64 (HGX) mı, ARM
(Grace; GH200/GB300) mı ve kurulu NVIDIA sürücü sürümü nedir?
Open Question 2: Kurumun iç registry'sinden gelen özel bir imaj, platformda kesirli GPU
ile inference iş yükü olarak çalıştırılabilir mi; zamanlayıcı ve proje ayarları nelerdir?
Open Question 3: Model dosyalarını paylaşımlı model deposuna koymanın onay, tarama ve
aktarım süreci nedir; pod bu depoyu hangi yolla salt okunur bağlar?
Open Question 4: Dil modeli uç noktasına kimlik doğrulama yöntemi ve ağ erişim kuralları nedir?
Open Question 5: Platformda kelime düzeyinde zaman damgası veren bir ses transkripsiyon
uç noktası var mı?
Open Question 6: Toplantı sesi ve biyometrik ses izinin bu kümede işlenmesi, saklama ve
loglama için kurumun veri sınıflandırması ve onay koşulları nelerdir?
