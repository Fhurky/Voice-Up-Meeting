# NVIDIA DGX Spark geliştirme ve model değerlendirme planı

Güncelleme: **9 Eylül 2026**. Kullanıcının bildirdiği Spark cihazı esas alınarak hedef
platform **NVIDIA DGX Spark / GB10, Linux ARM64, 128 GB ortak bellek** olarak belirlenmiştir.
Bu belge model değerlendirme yol haritasıdır. Spark kurulumu ve gerçek ECAPA çıkarımı
doğrulandı; kişi doğruluğu ve aşağıdaki aday model deneyleri henüz tamamlanmadı.

## 9 Eylül cihaz bağlantısı isteği

Kullanıcı Spark'ı bu bilgisayara kabloyla bağladı ve model hesaplamalarının oraya
aktarılmasını istedi. Güncel uygulama işi [004 Accepted PRD](../specs/speaker-identity/PRDs/004-spark-remote-inference/PRD.md)
ve bağlı plan/görevlerde yürütülür. Web/API/PostgreSQL burada, VAD ve embedding Spark'ta
kalır. Yetkili SSH erişimi açıldı ve cihaz gerçekten incelendi: Ubuntu 24.04.4,
ARM64, NVIDIA GB10, compute capability 12.1 ve sürücü 580.159.03. Ethernet arayüzü
enP7s7 artık 192.168.137.2 adresinde; Windows 192.168.137.1 üzerinden Ethernet SSH
bağlantısı doğrulandı. Wi-Fi varsayılan rotası korundu. Docker erişimi ve yerel CDI
GPU eşlemesi çalışıyor. Python 3.13.14 / Torch 2.8.0+cu129 ile gerçek CUDA, VAD ve
192 boyutlu ECAPA çıkarımı geçti. [Çalışma kanıtı](evidence/2026-09-09-spark-runtime/README.md)
ölçülen sonuçları ve uyumluluk sınırlarını ayrı kaydeder.

Mevcut 4060 paketleri CPython 3.13/x86_64/CUDA 12.8 içindir. İlk daha dar ARM64 adayı
aynı kararlı Torch/TorchAudio 2.8 API'siyle CUDA 12.9'dur; resmi wheel bulunması runtime
kabulü veya GB10 başarı kanıtı değildir. [İncelenen resmî artifact metadata'sı](evidence/2026-09-09-spark-preflight/arm64-candidate-metadata.json)
kaynak URL/hash/boyutları içerir. 48 dosyanın kapalı bağımlılık grafiği bağımsız
incelendi; ayrı kaynak manifesti ve hash kilidi oluşturuldu. Mevcut 46 artifact
korunuyor. 48 paketin tamamı Spark'ın hazırlık alanına indirildi ve hashleri iki
kez doğrulandı; sabit ses modelinin 7 dosyası da aktarılıp doğrulandı. Native paket
kurulumu ağ kapalıyken tamamlandı ve gerçek GPU çıkarımı geçti. Aşağıdaki NGC adayı
seçilmedi; çalışan ayrı Python 3.13 imajı kullanılır. Alternatif NGC değerlendirmesi
yapılırsa Python 3.12 farkı ve yayın yaşı ayrıca ele alınacaktır.

## Donanımın plana etkisi

DGX Spark, Blackwell GPU ve 20 çekirdekli Arm CPU kullanır. 128 GB LPDDR5x bellek CPU
ve GPU tarafından paylaşılır; işletim sistemi, ses tamponları, uygulamalar ve model
hesaplamaları aynı kapasiteden yararlanır. NVIDIA'nın belirttiği bellek bant genişliği
273 GB/s'dir. Dolayısıyla kaynak hesabını 128 GB ayrık VRAM + ayrıca sistem RAM'i olarak
yapmayacağız. [NVIDIA donanım özellikleri](https://docs.nvidia.com/dgx/dgx-spark/hardware.html)

Bu kapasiteyi daha güçlü embedding adaylarını aynı veriyle karşılaştırmak, daha büyük
ses partileri işlemek ve gerekli olursa ikinci modelle kontrol etmek için kullanacağız.
Onlarca profilin vektörlerini karşılaştırmak küçük bir iştir; gerçek güçlük kısa ve
örtüşen konuşma, kanal değişimi, benzer sesler ve bilinmeyen kişiyi yanlış kabul etmedir.
Büyük bellek bu hataları kendiliğinden çözmez. İlk hedef, önceden eğitilmiş modeller ve
kalıcı örnek deposuyla en iyi sonucu ölçmektir. Türkçe fine-tuning ancak hata analizi
ve yeterli ayrı eğitim verisi gerekçelendirirse eklenecek.

## Hedef çalışma ortamı

| Katman | Karar | Cihaz üzerinde kabul kontrolü |
| --- | --- | --- |
| Ana sistem | Spark'ın desteklenen DGX OS kurulumu ve NVIDIA sürücüsü | OS, `uname -m`, sürücü, GPU adı ve boş disk kayıt altına alınır. |
| GPU ortamı | ARM64/SBSA ve GB10 desteği doğrulanan NVIDIA NGC PyTorch container'ı | ARM64 manifest, ana sistem sürücüsüyle CUDA uyumu ve gerçek GPU tensor işlemi geçer. |
| Tekrarlanabilirlik | Testten sonra container digest'i ve Python bağımlılık sürümleri sabitlenir | Image etiketi yanında digest, CUDA/PyTorch sürümü ve model revision'ı sonuçlara yazılır. |
| Ses bağımlılıkları | Torch ile uyumlu torchaudio, torchcodec, FFmpeg ve libsndfile | WAV yükleme; gerekiyorsa sıkıştırılmış ses çözme; yeniden örnekleme; gerçek model çıkarımı geçer. |
| Uygulama | Boilerplate uygulaması ve ayrı Python ses işçisi | Web/API süreci istek başına model yüklemez; kalıcı işçi ve iş kuyruğu kullanılır. |
| Veri | Model önbelleği, ses dosyaları, profil deposu ve deney çıktıları kalıcı disk alanında | Container yeniden oluşturulduğunda modeller ve profiller korunur. |

Sağlanan boilerplate'in web backend'i Python 3.13/Alpine tabanlıdır. CUDA/PyTorch
bu image'a eklenmeyecek; NVIDIA/Ubuntu çıkarım ortamıyla HTTP sözleşmesi kurulacak.
Ürün ses profilleri PostgreSQL'de, tanımlanmış vektör gereksinimi varsa aynı veritabanında
pgvector ile tutulacak. Mevcut SQLite yalnız araştırma referansıdır. Çalışma anında
internet veya model indirme yerine önceden hazırlanmış, revision/hash bilgili model
paketleri kullanılacak. İşçi ve kalıcı kuyruk 001 kapsamında Windows/4060 ortamında
uygulandı; Spark üzerindeki çıkarım bağlantısı henüz doğrulanmadı.

Spark için ARM64 yazılım ve uygun container seçimi gerekir. NVIDIA'nın Spark NGC
koleksiyonu araştırma tarihinde `pytorch:26.08-py3` sürümünü listeliyor; bu **ilk
incelenecek adaydır**, doğrulanmış VoiceUp kurulum reçetesi değildir. Kurulum gününde
mevcut DGX OS/sürücü ile uyumlu sürüm seçilip digest'e sabitlenecek.
[NVIDIA Spark NGC koleksiyonu](https://catalog.ngc.nvidia.com/orgs/nvidia/-/collections/dgx-spark/-/artifacts),
[Spark NGC rehberi](https://docs.nvidia.com/dgx/dgx-spark/ngc.html)

26.08 sürüm notlarında CUDA 13.4.1 ve PyTorch `2.14.0a0+4fdf77b940` bildiriliyor; bu
paketler mevcut CPU referansındaki PyTorch 2.8.0 ile aynı ortam değildir. NVIDIA
container'ı bağımlılıkları koruyan `/etc/pip/constraint.txt` dosyası da kullanır. En yeni
container'ın eski ses kütüphaneleriyle doğrudan uyumlu olduğu varsayılmayacak; import
testinin ardından gerçek ses çıkarımı doğrulanacak. [NVIDIA PyTorch 26.08 sürüm notları](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-26-08.html)

### Mevcut CPU ortamından geçiş

Depodaki `pyproject.toml` şu anda `torch==2.8.0`, `torchaudio==2.8.0` ve açıkça
`pytorch-cpu` paket kaynağı tanımlar. Diarization ekinde `torchcodec==0.7.0` bulunur.
Bu ortam yerel referans testleri içindir. Spark'ta bu kilitle doğrudan `uv sync --all-extras`
çalıştırmak hedef CUDA ortamını oluşturmaz; container içindeki NVIDIA PyTorch paketini
değiştirmeye kalkabilir veya bağımlılık çözümünde başarısız olabilir.

Geçiş işi şu sırayla yapılacak:

1. Mevcut CPU test ortamını koru; Spark için ayrı image tarifi ve bağımlılık profili oluştur.
2. Seçilen container'ın PyTorch/CUDA paketlerini envantere al; ses bağımlılıklarını bu
   tabanla uyumlu sürümlere çöz. ARM64 paketi olmayan yerel uzantıları belirle.
3. Gerekli kaynak derlemelerini yalnız Spark image'ında ve sabit revision ile yap;
   her model ailesi aynı Python ortamına sığmıyorsa ayrı değerlendirme image'ı kullan.
4. Uygulama çekirdeğini ve ses adaptörlerini kur; CPU paket kaynağının Spark bağımlılık
   profiline taşınmadığını doğrula. Container'ın paket kısıtlarını körlemesine kaldırma.
5. GPU tensor işlemi, model yükleme ve bilinen sesle embedding üretimini doğrula;
   ardından uygun yazılım testlerini ve gerçek veri deneyini çalıştır.
6. Çalışan image digest'i, bağımlılık dökümü ve kurulum adımlarını repoya ekle.

Windows'taki `.venv`, `node_modules`, derlenmiş x86 dosyaları, model önbellekleri ve
geçici çıktılar Spark'a taşınmayacak. Kaynak kod ve kilit dosyaları taşınacak; hedef
mimari paketleri cihazda yeniden kurulacak. ARM64 taşıma ayrıntıları için
[NVIDIA Spark taşıma rehberi](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/index.html).

## Model öncelikleri

| Öncelik | Aday ve iş | Deney kararı |
| --- | --- | --- |
| P0 | Mevcut SpeechBrain ECAPA referansı | Spark'ta aynı seslerden çıkarım doğrula; yeni modellerin karşılaştırma tabanını oluştur. |
| P1 | WeSpeaker ResNet293-LM: kalıcı kimlik embedding'i | İlk güçlü alternatif. Önce aynı kosinüs protokolü; sonra ayrı kalibrasyonlu skor normalizasyonu deneyi. |
| P1 | 3D-Speaker ERes2NetV2: kalıcı kimlik embedding'i | ECAPA ve ResNet293 ile aynı Türkçe sorgular; mikrofon/oturum ayrılmış açık küme testleri. |
| P2 | 3D-Speaker ERes2Net-Large ve CAM++ | İndirilebilir checkpoint, revision ve ağırlık lisansı doğrulanır; doğruluk/hız karşılaştırmasına eklenir. CAM++ daha hafif kontrol adayıdır. |
| P2 | NeMo TitaNet-Large | İlk adayların hata örüntüsünü tamamlıyorsa karşılaştırmaya veya ikinci kontrol deneyine eklenir. |
| P1 | pyannote Community-1: konuşmacı bölümleme | Kimlik motorundan ayrı ölçülür; normal overlap çıktısı korunur. |

ResNet293-LM kartında 28,62 milyon parametre ve farklı LM/AS-Norm koşullarında farklı
VoxCeleb sonuçları bulunuyor. Bu sonuçları Türkçe 50 kişilik ürün doğruluğu olarak
kullanmayacağız. [Resmî ResNet293-LM kartı](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet293-LM)

3D-Speaker deposu ERes2NetV2, ERes2Net-Large ve CAM++ ailelerini, eğitim tariflerini ve
ayrı ön eğitimli checkpoint'leri listeliyor. Aynı mimari adı, aynı eğitim verisi veya
aynı model dosyası demek değildir. Her deneyde tam checkpoint ve revision kaydedilecek.
[3D-Speaker resmî deposu](https://github.com/modelscope/3D-Speaker)

Community-1'in dosya içi etiketleri kalıcı kişi kimliği olarak saklanmayacak; mevcut
profil eşleştirme katmanından geçirilecek. İlk model indirmesinde Hugging Face erişim
koşulları ve token gereklidir. [Community-1 model kartı](https://huggingface.co/pyannote/speaker-diarization-community-1)

`diar_streaming_sortformer_4spk-v2` dört konuşmacı çıkışına sahip olduğundan onlarca
konuşmacı hedefinin ana diarizer'ı olmayacak. Belleği artırmak bu çıkış sınırını kaldırmaz.
Bu sınırlama kayıtlı profil galerisine veya TitaNet'e genellenmeyecek.
[NVIDIA Sortformer 4spk-v2 model kartı](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2)

Yeni modele geçildiğinde kayıtlar uygun kaynak seslerinden yeniden vektörleştirilecek.
Farklı modellerin vektörleri aynı uzayda karşılaştırılmayacak. İki model birlikte
kullanılırsa her modelin ayrı profili ve kalibrasyonu olacak; skor birleştirme veya
ikinci kontrol yalnız ayrı geliştirme verisinde iyileşme gösterirse kabul edilecek.

## Bellek, parti boyutu ve eşzamanlılık deneyi

128 GB kapasitenin tamamını model ağırlıklarına ayırmayı planlamıyoruz. İlk işçi
tasarımında işletim sistemi ve uygulamalar için **en az 16 GiB kullanılabilir sistem
belleği bırakma** başlangıç hedefi kullanılacak; bu ölçülmüş tüketim veya garanti değildir.
Yük testi sonucu tamponlar, model sayısı ve parti boyutu birlikte ayarlanacak. Swap'a
dayanan yüksek parti boyutu kabul edilmiş performans sayılmayacak.

NVIDIA, Spark'ın ortak bellek mimarisinde `cudaMemGetInfo` bilgisinin işletim sisteminin
geri kazanabileceği belleği tam yansıtmadığını açıklıyor. Bu nedenle GPU allocator
ölçümleriyle birlikte Linux kullanılabilir sistem belleği, süreç tüketimi ve swap
gözlenecek; CPU RAM ve GPU bellek rakamları toplanarak toplam kapasite hesaplanmayacak.
[NVIDIA ortak bellek ve ölçüm rehberi](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/optimization.html)

| Deney ekseni | İlk tarama | Rapor |
| --- | --- | --- |
| Ses penceresi partisi | 1 / 8 / 16 / 32 / 64; güvenli olanlara kadar | Pencere/sn, p50/p95, tepe bellek, hata/OOM |
| İş eşzamanlılığı | Önce 1 iş; ardından 2 / 4 kayıt | Toplam ses/sn, iş bekleme ve bitiş süreleri, bellek baskısı |
| Sayısal tür | FP32 referansı; desteklenen modellerde BF16/FP16 adayı | Embedding/skor değişimi ve FPIR–DIR etkisi |
| Kayıt uzunluğu | Kısa pilot, 30 dk, 2 saat | Soğuk/sıcak başlatma, gerçek zaman katsayısı, tepe bellek |
| Model kullanımı | Tek model; ayrı A/B işleri; koşullu ikinci kontrol | Model yükleme bedeli, toplam kazanç ve yanlış kabul değişimi |

İlk işçi bir model örneğini yükleyip tekrar kullanacak. Her web isteğinin yeni GPU
modeli oluşturması engellenecek. Uzun sesler parça parça okunacak; iş kuyruğu geri
basıncı, iptal, durum ve hata kaydı sağlayacak. Bu tablo geliştirme işlerini tarif
eder; mevcut CLI'ın tüm bu yetenekleri sunduğu anlamına gelmez.

## Uygulama sırası ve karar kapıları

1. **Boilerplate tabanını hazırla:** Web/API altyapısını ve Python ses motorunu açık
   sınırlarla koru; ağır ses işlemleri için işçi sözleşmesini belirle.
2. **Spark ortamını doğrula:** Mimari/sürücü/container/ses kütüphanesi kontrolünü ve
   ECAPA gerçek çıkarımını geç. Bu gerçekleşmeden Spark'a hazır etiketi kullanma.
3. **Güçlü modelleri ekle:** Önce ResNet293-LM ve ERes2NetV2 adaptörleri, ayrı model
   kimlikleri ve ortak değerlendirme çıktıları. Belirsiz/yanlış kimlik güvenlik kuralları korunur.
4. **Türkçe kalibrasyon yap:** Beş kişi ve sonradan altıncı kişi senaryosu; ardından
   10/20/50 kişilik profil galerisi. Ayrı gün, cihaz ve bilinmeyen kişiler kullan.
5. **Otomatik bölümlemeyi ölç:** 5/10/20 konuşmacılı kayıtlar; 50 kişilik toplantı ayrı
   stres deneyi. Overlap ve diarization hatası kimlik başarısından ayrı raporlanır.
6. **Kaynakları ayarla:** Doğruluğu geçen adaylarda parti, hassasiyet, eşzamanlılık ve
   uzun kayıt testleri. En iyi açık küme sonucu, hata türleri ve kaynak bedeliyle model seç.
7. **Toplantı entegrasyonuna geç:** Kimlik hattı kabul edilince ASR ve platform ses
   aktarımı; profil güncelleme için kaynak ve geri alma akışı.

Ana kabul protokolü [EVALUATION_PLAN.md](EVALUATION_PLAN.md) içinde kalır: ilk hedef,
50 kişilik galeride ayrı oturumdan 3+ saniye temiz sorgu için FPIR ≤ %1 iken bilinen
doğru tanıma ≥ %95'tir. Bu hedef henüz ölçülmüş sonuç değildir. Daha büyük modeller,
daha yüksek bellek ve geçilen yazılım testleri gerçek ses doğruluğunun yerine geçmez.
