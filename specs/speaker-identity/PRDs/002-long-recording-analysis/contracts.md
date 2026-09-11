# Yerel toplantı sağlayıcısı sözleşmesi

Bu belge Accepted 002'nin Decision 2, Decision 4 ve T03 maddelerini somutlaştırır.
Sabit teknoloji profili `kt-vibecoding-python-web-v2` korunur. Web arka ucu
modelleri içe aktarmaz; `MeetingAnalysisPort` üzerinden kurum içindeki FastAPI
çıkarım servisine erişir. İlk gözlenen çalışma ortamı Linux x86_64, Python 3.13.14,
RTX 4060, PyTorch 2.8.0+cu128'dır. Spark ARM64 ve yeni toplantı sağlayıcısının
macOS/CPU çalışması bu kanıtla kabul edilmiş sayılmaz.

## Gerçek üretici dayanağı

Sabit ASR modeli gerçek GPU üzerinde 16 saniyelik kamuya açık bir kayıtta iki
segment ve 56 ham kelime üretti. Gözlenen kelime alanları `start`, `end`, `word`,
`probability` oldu. Bir ham kelimenin süresi sıfırdı; pozitif süre gerektiren
sağlayıcı sözleşmesinde bu kelime çıkarılır, segment metni korunur. Özel HTTP
yolunda 55 kelime gözlendi. Ham ASR kaydının SHA-256 değeri
`de4f314c9dc1f83d71c3ab0300bf79466ed545c5f1d70277679cc705487c2b67`'dir.

Gerçek HTTP çıktısının son başarılı kaydı
`ae4d4b26a8fd3c33fae2d279b0f1088fa525109540919590fdd2da46ed962196`
SHA-256 değerine sahiptir. Metni ve varsa biyometrik vektör değerleri açıkça
sanitizasyon uygulanmış test kopyası
[`meeting_chunk_actual.json`](../../../../app/backend/tests/fixtures/meeting_chunk_actual.json)
dosyasındadır. Bu kayıt iki yerel etiket içerir; iki etiket için de profil kanıtı
yetersiz/tutarsızdır. Metin başarısı, doğru kalıcı kişi kaydı veya 50 kişi düzeyinde
doğruluk iddiası değildir. Gerçek sağlayıcının NumPy `float64` zaman değerleri
sayısal olarak doğrulanıp JSON `number` değerlerine çevrilir; bool, metin, sonsuz
ve ters zaman aralıkları kabul edilmez.

## İstek ve yürütme sınırı

`POST /v1/meeting-chunks` yalnız iç servis uç noktasıdır. `X-Inference-Key`, UUID
biçiminde `X-Job-Id` ve `X-Tenant-Id` zorunludur. Web tarayıcısı bu anahtarı alamaz.
İstek gövdesi dosya yolu veya URL değil, en çok 310 saniyelik sestir. Mevcut web
adaptörü orijinal örnekleme hızında, mono, PCM16 WAV üretir; 8–192 kHz kabul edilir
ve model tarafında 16 kHz'e çevrilir. Web adaptörü en çok 120 MiB istek ve 8 MiB
yanıt kabul eder; sıkıştırılmış yanıtları reddeder ve yanıtı sınırlı akışla okur.
Ana dosya WAV/FLAC aktarım katmanında saklanır; MP4/WebM desteği bu sözleşmeye dahil
değildir. Modelde dalga biçimi kullanıldığı için TorchCodec/FFmpeg dosya çözme
yolu bu akışın kanıtı değildir.

İsteğe bağlı sorgu alanları:

| Alan | Kabul |
|---|---|
| `language` | `tr`, `en` veya alanın gönderilmemesi; son durumda model dil algılar. |
| `max_speakers` | 1–1000 arasında tam sayı üst sınırı veya gönderilmemesi. |
| `num_speakers` | 1–1000 arasında tam sayı; üst sınır verilmişse onu aşamaz. |

Sayı verilmezse sağlayıcıya kişi sayısı zorlanmaz. 50 bir kota değildir. Toplantı
genelindeki beklenen sayı her uzun kayıt parçasına aynen uygulanmaz; işçi kesin
sayıyı yalnız bütün toplantı tek parça olduğunda kullanır. Uzun kayıtta verilen
katılımcı/beklenen sayı yalnız uygun üst sınır bilgisidir.

İstek gövdesi okunmadan önce mevcut pilotla ortak, engellemeden reddeden tek iş
kilidi alınır. Community-1 GPU aşamasından sonra CPU'ya taşınır ve kendi değiştirdiği
Torch hassasiyet ayarları geri yüklenir. Whisper GPU üzerinde `int8_float16`, batch 1
ile doğal 30 saniyelik metin pencerelerini kullanır; çıktı tüketilince GPU modeli
CPU'ya boşaltılır. Ardından mevcut ECAPA kanıtı hesaplanır. Dış ağ veya model indirme
yolu çalışma zamanında kullanılmaz. Token yalnız yetkili model hazırlığına aittir;
kapısız ASR paketleyicisi token okumaz.

## Yanıt

Asıl doğrulama tipi `app/services/meeting_ports.py` içindeki `MeetingChunkResult`'tır.
Bilinmeyen alanlar reddedilir; sayılar sonlu olmak zorundadır.

| Alan | Şekil ve anlam |
|---|---|
| `input_seconds`, `sample_rate`, `device` | Doğrulanmış 16 kHz model dalga biçiminin süresi, `16000`, gözlenen `cuda:0`. |
| `turns` | En çok 4096 `{start, end, speaker}` normal diarization aralığı; örtüşme korunur. |
| `exclusive_turns` | Aynı şekil ve sınır; tek konuşmacı gösterimi için yardımcı aralıklar. |
| `segments` | En çok 4096 `{start, end, text}` ASR segmenti. |
| `words` | En çok 16384 `{start, end, word, probability}` kelime; olasılık 0–1. |
| `language`, `language_probability` | Dil kodu ve 0–1 olasılığı; sessizlikte `null` ve `0`. |
| `tracks` | En çok 1000 yerel etiket ve aşağıdaki ayrı ses kanıtı kaydı. |
| `model_identity` | Aşağıdaki üç sabit model kimliği; diarization vektörü kalıcı kişiyle karşılaştırılmaz. |

Süre, gönderilen gerçek WAV başlığından
`ceil(frames * 16000 / source_rate) / 16000` olarak yeniden doğrulanır. Yeniden
örnekleme kesirli bir kaynak sonuna en çok bir 16 kHz örnek ekleyebilir; bütün
çıktı aralıkları doğrulanan bu dalga biçiminin içinde kalır. Asıl kayıt koordinatına
dönüşte kayıt sonu ayrıca korunur. Geçerli model tamponlaması kaynak aralığına
kırpılır; yalnız kaynak dışında kalan aralıklar çıkarılır. Sıfır/ters diarization
aralıkları reddedilir. Sıfır süreli ASR kelimeleri çıkarılır.

`model_identity` alanları:

| Alt alan | `model_id` | `revision` |
|---|---|---|
| `diarization` | `pyannote/speaker-diarization-community-1` | `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee` |
| `asr` | `Systran/faster-whisper-large-v3` | `edaa852ec7e145841d8ffdb056a99866b5f0a478` |
| `embedding` | `speechbrain/spkrec-ecapa-voxceleb` | `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286` |

`embedding.dimensions` tam olarak 192'dir. Her `tracks` kaydı `speaker`, `status`,
`embedding`, `dimensions`, `validated_ranges`, `validated_seconds`, `used_seconds`,
`windows_count`, `min_pair_similarity`, `preprocessing_version`, `tracking` alanlarını içerir.
`status`, `usable`, `insufficient_speech` veya `inconsistent_audio` değeridir.

`tracking`, Decision 12 uyarınca yalnız toplantı içi eşlemedir. Varsa
`{embedding, model_id, model_revision, component, dimensions}` biçimindedir;
`model_id=pyannote/speaker-diarization-community-1`, `model_revision` yukarıdaki
sabit Community revision, `component=embedding`, `dimensions=256` olur. Vektör sonlu
ve birim normlu 256 sayıdır; 192 boyutlu ECAPA alanına dönüştürülmez. Gerçek native
çıktı float64 `(N,256)` olarak gözlendi; satır sırası `speaker_diarization.labels()`
ile doğrulanır. Native VBx, özgün WeSpeaker vektörlerinin ağırlıklı merkezini döndürür.

Native model, çok kısa bir etikete karşılık sıfır dolgu centroid döndürebilir:
gerçek 16 saniyelik örnekte normlar `[3.3386496435549446,0.0]` gözlendi. Bu etiketin
konuşma aralığı korunur, `tracking=null` olur; sıfır vektör eşleme kanıtı sayılmaz.
Sonlu olmayan değer, yanlış şekil veya etiket/satır uyuşmazlığı hata olarak kalır.
Eski checkpoint'lerde alan bulunmazsa `null` kabul edilir. İzleme vektörü, mevcut
`status`, temiz süre ve ECAPA kayıt kapısını değiştirmez; genel API'ye çıkmaz.

## Profil kanıtı

Normal diarization aralıklarından diğer bütün konuşmacıların örtüşmesi çıkarılır
ve kalan aralıklar Silero konuşma bölgeleriyle kesiştirilir. En az 1,5 saniyelik
özgün bloklar mevcut genlik/kırpılma kontrollerinden geçer. Mevcut pilotun 3–8
saniyelik pencere ve `.55` tutarlılık eşikleri değiştirilmez. Ayrıca uygun özgün
blokların tamamı birbirleriyle ve havuzlanan ECAPA vektörüyle karşılaştırılır;
başarılı uzun bölümün arkasında kalan kısa başka ses sessizce kabul edilmez.

`validated_ranges` yalnız bu denetimleri geçen, gerçek PCM örnekleriyle sınırları
içe alınmış, birbirini tekrar etmeyen özgün kaynak aralıklarıdır. İç pencere
sınırları ortak örnek sınırını paylaşır; yapay boşluk üretilmez. `validated_seconds`
bu aralıkların toplamıdır; sessizlik, örtüşme, bağlam ve tekrar denemeleri süreye
eklenmez. `used_seconds`, havuzlanan mevcut pilot pencerelerinin ayrı süresidir.
Her pencere 3–8 saniyedir, en çok 20 pencere kullanılır.

`usable` kayıt, sonlu ve birim normlu 192 değerli vektör, en az 3 saniye/1 pencere,
`.55` veya daha yüksek tutarlılık ve boş olmayan doğrulanmış aralık gerektirir.
Web adaptörü aralıkların aynı etiketin normal diarization kapsamı içinde olduğunu,
başka etiketle örtüşmediğini, kaynak sınırını aşmadığını ve toplamla uyuştuğunu
yeniden denetler. Diğer durumlarda `embedding=null`, `validated_ranges=[]` ve
`validated_seconds=0` zorunludur. Yetersiz kimlik kanıtı metni silmez.

Ses etkinliği bulunmayan parçada hem diarization hem ASR atlanır; bütün aralık,
kelime, segment ve etiket listeleri boştur. Bu yol Whisper'ın sessizlikten metin
üretmesini önler; zayıf gerçek konuşmanın bulunmasını garanti etmez.

## Toplantı boyunca birleştirme

Yeni özel parça sonucu üst düzey `vad` nesnesi taşır: `model_id="silero-vad"`,
`model_version="6.2.1"`,
`model_sha256="e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720"`
ve `ranges:[{start,end}]`. Bu aralıklar diğer parça aralıkları gibi 16 kHz
girdinin yerel **saniyeleridir**; sıralı, örtüşmesiz ve girdi süresinin içindedir.
Bu nesne mevcut olduğunda `model_identity.diarization.recipe` tam olarak
`community-vbx-fa015-v1` olmalıdır. Sessizlikte nesne korunur, `ranges=[]` olur.
Eski sonuçlarda iki yeni alan bulunmayabilir; bilinmeyen kimlik, hash, tarif,
örtüşme veya kaynak dışı aralık model sözleşmesi hatasıdır.

Bütün native etiketler mevcut akustik benzerlik politikasıyla eşlendikten sonra
ham konuşma ve VAD aralıkları özgün kaynak örneklerine içe yuvarlanır. Doğal
bağlam üretimi artık toplantı akustik kişisi üzerinde gerçekleşir. Özgün native
örtüşmeler, rakip veya eşlenmemiş konuşmalar bağlama engeldir. Engelsiz en çok
bir saniye boşluk bağlanabilir; yalnız VAD ile kesişen kişinin sesi tutulur.
3–8 saniyelik bağlam ana kaynak bölgesine kırpılır ve bileşenin son 0,25 saniyesi
ses alt kümesinden çıkarılır; üç saniyenin altına kırpılan bağlam kullanılmaz.
Kaynak sırasındaki ilk 256 örtüşmesiz aday, kaynak hash'i ve açık işleme sürümüyle
checkpoint'e kaydedilir. Bunlar temiz süre değildir; ayrı son örnek
doğrulamasına gider. Üst düzey `vad` mevcutken native etiketlerin eski
`candidate_contexts` alanı kullanılmaz; boş VAD/eksik izleme vektörü açık boş
yeni aday listesi bırakır. Yalnız `vad=None` tarihsel sözleşmeyi seçer.

İşçi 300 saniyelik ana bölgeler ve iki yanda en çok 5 saniyelik bağlam kullanır.
Yeni toplantı oluşturulurken `props.window_core_seconds=300` kaydedilir; alanı
taşımayan eski toplantılar 60 saniyelik özgün ana pencereleriyle devam eder.
İlerleme toplamı ve checkpoint devamı aynı toplantı ayarından hesaplanır;
yeniden deneme mevcut parçaların kaynak sınırlarını değiştirmez.
Bir parçanın son 5 saniyelik dökümü komşu parça görülene kadar ertelenir. Komşu
kelimeler kaynak zamanında karşılıklı eşleştirilip tek bir birleşme sınırı seçilir;
eşleşme yoksa gözlemler görünür belirsizlikle korunur. Bu yöntem kusursuz ASR
garantisi değildir. Özel checkpoint sürüm 1, sağlayıcı sonucunu, bekleyen
kelime/aralıkları ve `committed_until` değerini kapsar.

Kelime orta noktası tek ana bölgeye sahiplik verir. Normal aralıklar örtüşmeyi
korur; exclusive aralıklar yalnız konuşmacı seçimine yardımcıdır. Kararsız eşitlik,
düşük kelime olasılığı, örtüşme ve sınır uyuşmazlığı belirsizlik olarak görünür.
Normal aralığa oturmayan kelime, mevcut regular etikete ait gözlenen exclusive
konuşma aralığıyla kesişiyor ve olasılığı en az `.5` ise kişi atanmadan belirsiz
korunur. Başka bir yerde konuşma olması veya yüksek ASR olasılığı tek başına
desteksiz boşlukta kelime kabul ettirmez.
Yerel etiket, toplantı akustik kişisi, bildirilen platform katılımcısı ve kalıcı
profil ayrı kimliklerdir. Kalıcı profil yalnız tekil, uygun konuşma toplamı
**20 saniyeyi aştığında** ve ayrıca ilgili sürümlü son kayıt kalite kapısı geçildiğinde
oluşturulur; kesin 20 saniye bekler. Manuel görünen ad biyometrik eşleşme kanıtı
değildir.

## Hatalar ve hazırlık

`/ready` mevcut pilotun hazırlığını korur. `/meeting-ready` toplantı modellerinin
hazırlığını ve sabit kimliğini verir; kapalı özellik `meeting_disabled` döndürür.
HTTP `503/inference_busy` yeniden denenebilir meşgul durumudur. Hazır olmayan,
kapalı veya ulaşılmayan sağlayıcı web katmanında `inference_unavailable` olur.
Zaman aşımı `job_timeout`, geçersiz/bozuk sağlayıcı çıktısı `model_mismatch` olur.
Model istisnası, yol, token veya ham ses istemci hata gövdesine taşınmaz. Durumsuz
çıkarım tekrar çalışabilir; idempotency, tenant yetkisi, worker fencing ve kalıcı
profil tekilliği web uygulaması/işçi işlemlerinin sorumluluğudur.

## Toplantıya özel hafıza doğrulaması

Decision 13 için `POST /v1/meeting-memory` özel JSON uç noktası kullanılır.
Genel kullanıcı API'si değildir; aynı çıkarım anahtarı ve iş/tenant başlıkları
zorunludur. Girdi `audio_base64`, `sample_rate`, `contexts`, `target` ve
`competitors` alanlarını taşır. Mono PCM16 WAV en çok 60 saniye, JSON gövdesi
en çok 36 MiB, yanıt en çok 128 KiB'dir; sıkıştırılmış yanıt kabul edilmez.
Bağlam sayısı en çok 20, rakip merkez sayısı en çok 999'dur.

Her bağlam `{start, end, voiced_ranges:[{start,end}]}` şeklindedir. Bütün
aralıklar yüklenen WAV'ın **özgün örnekleme hızında tam sayı örnek indeksleri**
taşır; 16 kHz'e dönüştürülmüş veya toplantının mutlak saniyesi değildir.
Bağlamlar sıralı, örtüşmesiz ve 3–8 saniyedir; ses aralıkları kendi bağlamlarının
alt kümesidir. `target` ve `competitors` önceki `MeetingTracking` sözleşmesindeki
256 boyutlu normalize vektör, Community model/sürüm kimliği ve `embedding`
bileşenini taşır. Sunucu özgün kaynak örneklerine dönüş haritasını ayrıca tutar.

Yanıt alanları:

- `ecapa_model_id`, `ecapa_model_revision`: sabit gerçek 192 boyutlu model kimliği.
- `input_sha256`, `input_frames`, `sample_rate`: doğrulanan özgün WAV kimliği.
- `quality_version`: `meeting-natural-context-v1`.
- `status`: `usable`, `insufficient_speech`, `inconsistent_audio` veya `clipped_audio`.
- `accepted_context_indices`, `validated_ranges`, `validated_seconds`, `windows_count`.
- `retained_sha256`: yalnız doğrulanmış son örneğin WAV hash'i; ret durumunda boş.
- `embedding192`, `memory_embedding`, `device`: iki bağımsız gerçek modelin sonucu.

Ret sonucu vektör, hash, kabul edilmiş indeks veya doğrulanmış aralık taşıyamaz;
süre ve pencere sayısı sıfırdır. Kullanılabilir sonuç en az 3 saniye doğrulanmış
ses taşır. Sunucu dönen aralıkların kabul edilmiş bağlamların ses alt kümesi
olduğunu, süre hesabını, girdi hash'ini ve yeniden çıkardığı son örneğin hash'ini
ayrıca doğrular. Yeni profil için 20 saniyeden fazla özgün konuşma ve en az üç
farklı PCM bağlamı gerekir. Tanıma daha kısa kaliteli sesle mümkündür.

İki vektör tam olarak saklanan son örnekten hesaplanır. Kalıcı profilin mevcut
ECAPA alanları korunur; 256 boyutlu alanlar ayrı model/sürüm/işleme kimliği,
kaynak hash'i ve tenant kapsamlı `Recording` referansı taşır. Aramalar exact
cosine ile ayrı yapılır; sayısal skorlar birbirine karıştırılmaz. Belirsizlik veya
iki farklı kişi kararı yeni profil oluşturmaz. Kaynak kalite reddi eski kalite
yoluna düşmez; aday alanı bulunmayan eski checkpoint'ler eski sözleşmeyle sürer.
Genel izleme sonucu `preprocessing_version` içinde yeni sürümü açıkça gösterir;
özel vektör ve kaynak yollarını göstermez.
