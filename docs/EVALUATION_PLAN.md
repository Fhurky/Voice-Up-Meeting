# Türkçe toplantılarda konuşmacı tanıma değerlendirme planı

Plan tarihi: **8 Eylül 2026**; uygulama ve veri durumu **9 Eylül 2026** tarihinde
güncellendi. Bu belge Türkçe toplantılar için önerilen deneyleri ve kabul
ölçütlerini tanımlar. Açık İngilizce veride yapılan ölçümler ayrı kanıttır;
temsilî Türkçe toplantı kümesi ve üretim doğruluğu garantisi henüz bulunmuyor.
Aşağıdaki sayısal hedefler başlangıç hedefidir; pilot sonuçlarla gözden geçirilecek.

## 9 Eylül güncellemesi

İlk **RTX 4060** deneyi, gerçek CUDA akışını ve tekrarlı teknik örnekle hızı
doğruladı. Güncel model hesaplamaları Ethernet ve SSH üzerinden **NVIDIA DGX
Spark** üzerinde çalışıyor; Windows uygulama, iş kuyruğu ve veritabanını barındırıyor.
[Spark çalışma kılavuzu](SPARK_RUNTIME.md) bağlantı ve başlatma koşullarını açıklar.

[Açık veri protokolü](PUBLIC_DATASET_PROTOCOL.md) için LibriSpeech'in gelişim ve
test arşivlerinden **birbirinden ayrı 140 İngilizce konuşmacı ve 604 ses parçası**
hazırlandı. Kalibrasyon ve kör test havuzlarının her biri, kaydedilmesi planlanan
50 kişi ve başlangıçta bilinmeyen 20 kişi içeriyor. Kayıt ve sorgular farklı kitap
bölümlerinden gelir; bu ayrım farklı gün veya mikrofon kanıtı değildir. Veri
sayıları, başarılı profil veya doğru tanıma sayısı olarak sunulmaz.

Kalibrasyon, varsayılan tanıma eşiği ile kalite nedeniyle reddedilen kayıtları
ayrı incelemeye imkân verdi. Seçilen aday **tanıma eşiği 0,55; bilinmeyen eşiği
0,45; aday farkı 0,10** olarak
[sabit politika dosyasına](evidence/2026-09-09-public-speaker-evaluation/selected-policy.json)
kaydedildi. Bu seçim yalnızca kalibrasyona dayanır. Spark'ta doğrudan model ve
skor hesabıyla üretilen teşhis tablosu, gerçek uygulama üzerinden ölçümün yerine
geçmez; adayın uygulama koşumu ve kör test sonuçları ayrı raporlanır. Bu plan
kör test için tahminî başarı sayısı içermez.

Tamamlanan gerçek uygulama koşumu: kalibrasyonda 40/50 profil ve 109/150 doğru
tanıma; ayrı testte 29/50 profil ve 77/150 (%51,3) doğru tanıma. Testte 26 bilinen
sorgu ile 20/100 bilinmeyen sorgu kalite hatası verdi; yeni kişi kaydı ve dönüşü
de başarısız oldu. Yanlış kimlik gözlenmedi, fakat yüksek doğruluk hedefi
karşılanmadı. [Sonuçlar ve tüm paydalar](evidence/2026-09-09-public-speaker-evaluation/README.md)
hangi kayıtların dışarıda bırakılmadığını ve kalan kabul eksiklerini gösterir.

[Türkçe veri toplama kiti](DATA_COLLECTION.md) 001/T09 için beş kayıtlı + iki
bilinmeyen kişiyle 30 ilk kayıt ve iki sonraki kayıt hazırlar. Bu temsilî veri
gereksinimi sürer; İngilizce açık veri, Türkçe toplantı kabulünün yerine geçmez.
Sıra **gerçek kişi doğruluğu → uzun dosyalarda bölümleme ve kimlik sürekliliği → canlı analiz**;
[uzun kayıt stratejisi](LONG_RECORDING_STRATEGY.md) deney parametrelerini ve sınırları tanımlar.

## Tekrarlanabilir açık veri koşumu

9 Eylül ölçüm genişletmesi: [konuşmacı ölçüm protokolü](SPEAKER_METRICS.md), kimlik
precision/recall/micro F1, kişilere eşit ağırlıklı macro F1 ve bilinmeyen F1'i
tanımlar. `VoiceUp Score` son iki değerin harmonik ortalamasından üretilen ayrı
0–100 bileşik skordur; standart F1 veya doğruluk yüzdesi değildir. İlk kayıt
kapsamı ve kalite hataları ayrıca gösterilir. Mevcut raporların bu protokolle
yeniden puanlanması yeni model deneyi veya mevcut kabul hedeflerinin değişmesi
anlamına gelmez.

Sabit teknoloji profili `kt-vibecoding-python-web-v2` korunur. Hazırlama aracı
`scripts/prepare-public-speaker-dataset.py`, uygulama koşucusu
`scripts/evaluate-public-speakers.py`, anonim özetleyici
`scripts/report-public-speakers.py` hazırdır. Ayrıntılı PowerShell komutları
[açık veri protokolünde](PUBLIC_DATASET_PROTOCOL.md) bulunur.

Kalibrasyon adayı ve kör test farklı, başlangıçta boş değerlendirme tenant'ları
ve ayrı durum dosyaları kullanır. Aday komutlarında
`--policy docs/evidence/2026-09-09-public-speaker-evaluation/selected-policy.json`
belirtilmelidir. Bu seçenek servis ayarlarını değiştirmez; uygulamanın döndürdüğü
politikanın beklenen değerlerle eşleşmesini denetler. Seçenek verilmezse koşucu
ilk ölçümü tekrarlamak için tarihsel 0,75 tanıma eşiğini bekler.

Sesler ve manifestler Git dışında tutulan `data/public-speaker-evaluation/`
altında; kimlik bilgileri, ham sonuçlar, kişi/iş kimlikleri ve devam durumu
`outputs/public-speaker-evaluation/` altında kalır. Paylaşılabilir kanıt, ayrı
özetleyicinin ürettiği kimliksiz toplamları kullanır. Hazırlayıcının manifest
SHA-256 değeri dosyanın ham baytlarını, koşucunun aynı adlı alanı ise anahtarları
sıralanmış, gereksiz boşlukları kaldırılmış JSON içeriğini özetler. Özetleyici koşucunun kanonik değerini
korur ve ham sonuç dosyasının özetini ayrıca kaydeder; bu değerler birbirinin
yerine karşılaştırılmaz.

Planlanan galeri büyüklüğü ile gerçekten kaydedilen profil sayısı ayrı tutulur.
Kayıt hataları o kişinin sorgularını paydadan çıkarmaz. İşlemlerin tamamlanması
tanıma hedefinin geçtiği anlamına gelmez; yanlış kimlik, belirsiz, bilinmeyen,
kalite hatası ve çalıştırılmayan sorgu ayrı görünür. Bilinmeyen sorguların hata
durumları doğru reddetme sayılmaz. İç içe 5/10/20/50 galerileri aynı sorguları
yeniden kullandığından bağımsız deneyler değildir. Türkçe, gerçek toplantı,
örtüşen konuşmacılar, uzun kayıt ve canlı akış kabulü açık kalır.

## Başarı tanımı

Başarı yalnızca bir kayıtta beş farklı etiket üretmek değildir. Aynı kişiyi farklı gün ve mikrofonla tekrar tanımak, kayıtlı olmayan birini mevcut kişiye yapıştırmamak, yeni kişiye kalıcı kimlik vermek ve yanlış kararla mevcut profili bozmamak birlikte ölçülecek.

İki ölçeği ayrı raporlayacağız:

- **Kayıtlı kişi sayısı:** Birincil doğruluk odağı yaklaşık 50 kişi; 5, 10, 20 ve 50 ana ölçekler, 100/200 ek ölçek deneyleridir. Ürün profil sayısını 50'de engellemez.
- **Bir toplantıda konuşan kişi sayısı:** Önce 2–5, sonra 10 ve 20; 50 kişilik toplantı ayrı stres testi. Depoda 50 kişinin olması 50 kişinin aynı anda konuştuğu anlamına gelmez. Overlap oranı bağımsız eksendir.

## Veri ve doğru cevaplar

İlk pilot için katılımı kabul eden 10–15 kişiyle veri toplanıp protokol doğrulanacak. Ölçek testi 50 kayıtlı ve 20 ayrı bilinmeyen konuşmacıyla yapılacak; bilinmeyen sorguları profillere eklenmediği için kapasiteyi kullanmaz. Her kayıtlı kişiden en az üç ayrı oturum, mümkünse iki farklı mikrofon alınacak. Bunlar asgari ürün garantisi değil, veri toplama başlangıç planıdır.

| Kayıt türü | Önerilen içerik | Amaç |
| --- | --- | --- |
| Kayıt / enrollment | Kişi başına toplam 30–60 sn temiz doğal Türkçe; birkaç ayrı parça | Kalıcı profil oluşturma |
| Bilinen kişi sorgusu | Başka gün ve oturumda, aynı ve farklı mikrofonla 1–2 / 3–5 / 10+ sn net konuşma | Kısa sözler, kanal ve oturum değişimi |
| Bilinmeyen kişi sorgusu | Kayıt deposunda hiç bulunmayan kişilerin aynı koşullardaki kayıtları | Açık küme yanlış kabul ölçümü |
| Toplantı | Gerçek konuşma sırası, kesmeler, sessizlik, uzaktan bağlantı sıkıştırması, düşük/yüksek overlap | Uçtan uca bölütleme ve kimlik başarısı |
| Geri dönüş | Yeni kişinin sonraki bir oturumda tekrar konuşması | Yeni kimliğin kalıcı tanınması |

Ana ölçüm gerçek insan kaydıyla yapılacak. Sentetik ses, saf ton veya tek dosyanın farklı kırpımları yalnızca yazılım akışını kontrol eder; ses tanıma doğruluğunun kanıtı sayılmaz. Katılımcı kimliği, oturum, cihaz, kayıt zamanı, konuşma aralıkları ve örtüşen konuşmacılar etiketlenecek. Etiket anlaşmazlıkları ikinci dinleyiciyle incelenecek.

## Sızıntıyı önleyen ayırma

1. **Enrollment**, **kalibrasyon** ve **kör test** kayıtları ayrı tutulacak. Aynı orijinal kaydın kırpımları farklı kümelere dağıtılmayacak. Aynı kişinin farklı oturumu tanıma testi için kullanılabilir; aynı oturumun art arda parçaları bağımsız oturum sayılmaz.
2. Kalibrasyonda eşik seçmek için kullanılan geliştirme konuşmacıları ile son testin konuşmacı havuzu mümkün olduğunca ayrılacak. Son testin bilinen kişileri kendi enrollment örneklerine sahip olacak; kör sorguları ayrı oturumdan gelecek.
3. Bilinmeyen test kişileri enrollment deposunda ve eşik seçilen bilinmeyen havuzunda bulunmayacak.
4. Aynı mikrofon/farklı oturum ve farklı mikrofon/farklı oturum sonuçları ayrı raporlanacak. Ortak kaynak sesin yeniden kodlanmış sürümü cihaz genellemesi kanıtı değildir.
5. Eşikler, kalite filtreleri, aday farkı ve güncelleme kuralları kör testten önce dondurulacak. Test sonucu görüldükten sonra ayar değiştirilirse yeni bir kör test sürümü oluşturulacak.

## Üç aşamalı karşılaştırma

**A — Kimlik motorunu izole et:** Doğru konuşma sınırları ve tek konuşmacılı parçalarla tüm embedding adaylarına aynı ses verilecek. Model, pencere uzunluğu ve profil birleştirme seçenekleri burada karşılaştırılacak. Böylece diarization hatası embedding hatasıyla karışmayacak.

**B — Gerçek bölümleme ekle:** Aynı karışık kaydı Community-1 ile böl; bulunan yerel konuşmacıları aynı profil motoruna bağla. A ile B arasındaki fark, bölümleme ve overlap maliyetini gösterir. Modelin konuşmacı sayısını kendisinin tahmin ettiği sonuç ana rapor olacak; gerçek sayı verilmiş deney yalnızca teşhis amacıyla ayrı gösterilecek.

**C — Kalıcı kayıt akışını ölç:** Toplantıları zaman sırasıyla işlet; yeni kişiler eklenip tekrar gelsin. Sabit profillerle çalışma ve otomatik profil güncellemesi ayrı deneyler olsun. Güncellemenin yararı kadar yanlış kimlik aktarımı da raporlansın.

## Ölçümler ve paydalar

| Ölçüm | Tanım / raporlama |
| --- | --- |
| Bilinmeyen yanlış kabul oranı, FPIR | Bilinmeyen sorguların herhangi bir kayıtlı kişiye kabul edilen kısmı. Payda bütün bilinmeyen sorgular. Her galeri büyüklüğü için ayrı. |
| Bilinen doğru tanıma oranı, DIR / recall | Doğru kalıcı kimliğe kabul edilen bilinen sorgular / bütün bilinen sorgular. Reddedilenler paydadan çıkarılmaz. FPIR çalışma noktasıyla birlikte verilir. |
| Bilinen yanlış kimlik oranı | Başka kayıtlı kimliğe atanan bilinen sorgular / bütün bilinen sorgular. Bilinmeyen olarak reddetmeden ayrı tutulur. |
| Bilinmeyen tespit recall | Bilinmeyen olarak doğru reddedilen sorgular / bütün bilinmeyen sorgular. `Belirsiz` kararları ayrıca raporlanır; sessizce başarı sayılmaz. |
| Kabul edilenlerde kesinlik | Doğru kimliğe verilen kabul kararları / bütün kimlik kabul kararları. Kapsama oranıyla birlikte verilir; çoğu sesi reddederek yüksek kesinlik sağlanması görünür olur. |
| EER / ROC | Aynı kişi ve farklı kişi eşleştirmeleriyle teşhis ölçümü. Ana ürün kararı açık küme FPIR–DIR eğrisine dayanır. |
| Yeni kişi kümeleme | Tek kişiden açılan fazladan profiller, farklı kişilerin aynı profile birleşmesi, doğru yeni kayıt oranı ve tekrar geldiğinde tanıma oranı. |
| Profil bozulması | Yanlış kişiden eklenmiş örnek sayısı / toplam eklenmiş örnek; güncelleme sonrası eski kayıtlı kişilerde performans değişimi. |
| Süre / kaynak | Ses süresine oranla işleme süresi, p50/p95 gecikme, CPU/GPU modeli, RAM/VRAM, model yükleme ve sıcak çalışma ayrı. |

**Diarization:** Ana DER ölçümü `collar=0`, `skip_overlap=False` olacak; kaçırılan konuşma, yanlış konuşma tespiti ve konuşmacı karışıklığı ayrı verilecek. Ek raporda overlap dışındaki DER, yalnızca overlap bölgelerindeki hata, overlap oranı ve konuşmacı sayısı hatası gösterilecek. Pyannote metriği varsayılan olarak overlap'ı korur ve yerel etiketleri referansa en uygun eşler. [Resmî metrik uygulaması](https://raw.githubusercontent.com/pyannote/pyannote-metrics/develop/src/pyannote/metrics/diarization.py)

**Kalıcı kimlik ölçümü:** DER'in en uygun etiket permütasyonu, kişilerin adlarının/toplantılar arası kimliklerinin yanlış eşleştirilmesini gizleyebilir. Bu nedenle ayrıca kalıcı `speaker_id` etiketlerini yeniden eşleştirmeden, zaman ağırlıklı kimlik hatası hesaplanacak. Hem doğru bölümleme verildiğindeki tanıma hem otomatik bölümleme sonrasındaki tanıma raporlanacak.

## Deney matrisi

İlk teknik referans **RTX 4060 Laptop / 8 GB, ayrı CUDA servisi** üzerinde alındı.
Güncel açık veri kimlik değerlendirmesi **NVIDIA DGX Spark / GB10, Linux ARM64,
128 GB ortak bellek** üzerinde yürütülür. İlk Windows/CPU yazılım doğrulaması ve
tekrarlı teknik CUDA hız deneyi ayrı referanslardır. Model adayları önce aynı FP32 ve
ses penceresi koşullarında karşılaştırılacak; ardından desteklenen hassasiyet, parti
boyutu ve 1/2/4 eşzamanlı kayıt deneyleri raporlanacak. Ortak bellek, GPU allocator ve
sistem kullanılabilir belleğiyle izlenecek; CPU/GPU rakamları toplanmayacak. Ayrıntılar
[DGX_SPARK_PLAN.md](DGX_SPARK_PLAN.md) içindedir; gerçekleşen Spark işletim ve hız
kanıtı [çalışma kılavuzunda](SPARK_RUNTIME.md) izlenir. Hız kanıtı kişi doğruluğu
sonucu olarak yorumlanmaz.

| Eksen | Başlangıç değerleri |
| --- | --- |
| Profil galerisi | 5 / 10 / 20 / 50 kişi |
| Tek oturumdaki kişi | 2 / 5 / 10 / 20; 50 ayrıca stres testi |
| Bilinmeyen sorgu payı | %0 / %20 / %50 |
| Kullanılabilir net konuşma | 1–2 / 3–5 / 10+ saniye |
| Kanal | Aynı cihaz, farklı cihaz, uzaktan toplantı codec'i |
| Ortam | Temiz, gerçek arka plan sesi, yankı |
| Örtüşme | %0, düşük, yüksek; gerçek ölçülen oranı belirt |
| Model | ECAPA; WeSpeaker ResNet293-LM; CAM++; ERes2NetV2; gerekirse TitaNet |

Tüm kombinasyonları baştan toplamak yerine önce temiz/farklı oturum koşulu, sonra mikrofon ve overlap koşulları eklenecek. Galeri alt kümeleri birden fazla sabit rastgele tohumla kurulacak; kolay veya zor kişilerin seçilmesi sonucu belirlemesin. Model revision, örnekleme, ses normalizasyonu, skor yöntemi ve her profilin net konuşma süresi sonuç dosyasında bulunacak.

## İlk hedefler ve karar kapısı

Bu hedefler **henüz ulaşılmamış mühendislik hedefleridir**. İlk etapta, 3+ saniye temiz tek konuşmacılı sorgu ve farklı oturum koşulunda, 50 kişilik galeride **FPIR ≤ %1 iken bilinen doğru tanıma ≥ %95** hedeflenecek. Daha sonra **FPIR ≤ %0,1** için eşik ve doğru tanıma kaybı incelenecek. Kısa, bozuk veya örtüşen parçalarda aynı başarı varsayılmayacak; kaliteye göre karar vermeme oranı raporlanacak.

DER için ilk hedeften önce gerçek toplantı baseline'ı ölçülecek. Dış kaynaklardaki AMI, VoxCeleb veya Çince toplantı skorları Türkçe hedef veri yerine kabul ölçütü yapılmayacak. VAD, overlap ve collar farklarının karşılaştırmayı etkilediği model notları [MODEL_RESEARCH.md](MODEL_RESEARCH.md) içinde bulunuyor.

Her oran örnek sayısıyla ve güven aralığıyla verilecek. Aynı kişinin yüzlerce bitişik kırpımı yüzlerce bağımsız kanıt sayılmaz; kişi/oturum gruplarıyla bootstrap yapılacak. Çok düşük yanlış kabul iddiası için yeterli sayıda bağımsız bilinmeyen denemesi gerekir. Kaba “3/n” yaklaşımında sıfır hata görülen yaklaşık 3.000 bağımsız deneme, %95 üst sınırın yaklaşık %0,1 olması içindir; bu sayı tek başına bağımsızlığı ya da Türkçe genellemeyi garanti etmez.

## Kullanıcının örneğini doğrulayan senaryo

1. İlk toplantıda beş kişi için beş tutarlı aday oluşur; yeterli temiz kanıtla beş kalıcı kimlik kaydedilir.
2. Farklı gündeki ikinci toplantıda bu kişilerin yeni kayıtları aynı kimliklere eşlenir; dosya içindeki konuşma sırası değişebilir.
3. Altıncı kişi girdiğinde ilk beşten birine yanlış kabul edilmez; yeni aday olarak belirlenir, yeterli kanıtla altıncı kimlik kaydedilir.
4. Üçüncü toplantıda altıncı kişi doğru tanınır. Diğer beş kişinin kayıtları değişmemiş kimliklerle tanınmaya devam eder.
5. Belirsiz kısa söz, sessizlik ve iki kişinin eşzamanlı konuşması tek başına kalıcı profil açmaz veya var olan profili değiştirmez.
6. Aynı senaryo 10, 20 ve 50 kişilik galerilerle yinelenir; gerçek ses sonuçları yazılım testlerinden ayrı raporlanır. Galeride 50 aktif profil olsa da yeni kişi normal kayıt kurallarıyla eklenebilir. 100/200 kişilik ek ölçek sonuçları ayrı verilir; toplantıya katılan kişi sayısı ve toplam kalıcı profil sayısı aynı sayılmak zorunda değildir.

Önce tek konuşmacılı gerçek veri baseline'ı, sonra uzun toplantı dosyalarında bu senaryo doğrulanır; ardından canlı kimlik analizi gelir. Transkript hizalama ve toplantı platformu bağlantısı ayrıca ele alınacak. İlk değerlendirme araçları yalnızca embedding eşleştirmesini ölçüyorsa burada tanımlanan uçtan uca DER ve zaman ağırlıklı kimlik ölçümleri tamamlanmış sayılmayacak.
