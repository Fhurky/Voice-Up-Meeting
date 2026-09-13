# Türkçe deneyleri çalıştırma

Bu akışın gereksinimleri [009 PRD](../specs/speaker-identity/PRDs/009-turkish-evaluation-ledger/PRD.md),
veri seçimi [Türkçe araştırması](../plans/TURKISH_DATASET_RESEARCH.md),
deney günlüğü [results.md](../results.md) içindedir. Sabit uygulama profili
`kt-vibecoding-python-web-v2` korunur. İndirme açık bir hazırlama işlemidir;
normal uygulama ve model çalışması internete ihtiyaç duymaz.

Önceki küçük deneylerin ardından [010 kapsamı](../specs/speaker-identity/PRDs/010-expanded-turkish-benchmark/PRD.md)
2.433 kullanılmamış MediaSpeech kaydı, FLEURS'ün 743 kayıtlık resmî Türkçe test
bölümü ve 12 yeni görüşme kesiti ekler. Kaynak bazlı skorlar ve sınırlar
[genişletilmiş koşum raporunda](evidence/2026-09-13-expanded-turkish/README.md),
hazırlama, devam etme ve dağılım komutları aşağıdaki geniş test bölümündedir.

## İki farklı ölçüm

**Real-TurnTurk**, altı gerçek kişinin farklı ikili görüşmelerde tekrarını sınar.
Yayımlanan altı görüşmenin ilk 180 saniyesi, ayrı kanalların zaman sırası
korunarak eşit kazançla karıştırılır. Uygulamaya yalnız mono WAV gönderilir;
kişi etiketleri ve ayrı kanallar değerlendirme referansıdır. Sırayla altı ilk
görünüm ve altı dönüş görünümü vardır. İlk kayıt başarısız olsa bile dönüş
görünümü bilinen kişi paydasında kalır. Taban çizgisinde kişi sayısı modele ipucu
olarak verilmez. Eşlenmiş ikinci geliştirme deneyi, gerçekten iki kişinin
konuştuğu bu kaynaklarda mevcut kesin konuşmacı sayısı girdisini kullanır.

Konuşma etkinliği otomatik üretilmiştir; metinlerin insan denetimi ve kaynak
zamanlarının tam hizası doğrulanmamıştır. Örtüşen referans aralıkları kimlik
eşlemesine çift oy vermez. Kaynakta tekrarlanan veya sıçrayan WebM zaman
damgaları bulunduğundan çözülmüş ses örneklerinin sırası korunur. Bunlar
**zayıf referanslı tanılayıcı hafıza skorlarıdır**; insan işaretli konuşmacı
ayrım hatası, kesin biyometrik doğruluk veya 50 kişi başarısı değildir.
Kesit sınırını aşan beş referans cümlesi metin referansına alınmaz; ses ve
modelin ürettiği sözler korunur. Bu durum tanılayıcı metin skorunu etkiler.

**MediaSpeech Türkçe**, insan transkripsiyonlu haber sesinde metne çevirme
ölçümüdür. Sabit arşiv ve SHA-256 sıralamasıyla 40 geliştirme ve 40 ayrılmış
test klibi seçilir. Her klibin değiştirme, silme ve ekleme sayısı toplanıp bütün
referans kelimelerine bölünür. Klipler farklı kişiler sayılmaz; kişi/oturum
kimliği verilmediği için bu ayrım yalnız klip düzeyindedir. `segment.text`
üzerinden doğrudan model çıktısı ölçülür; uygulamanın kelime zaman damgası ve
konuşmacı gruplama işlemlerinin tamamını ölçmez.

## Veriyi hazırlama

Proje kökünde, mevcut araştırma Python ortamıyla:

```powershell
.venv/Scripts/python.exe scripts/prepare-turkish-meeting-evaluation.py --download --verify
.venv/Scripts/python.exe scripts/evaluate-turkish-asr.py prepare --download
```

Real-TurnTurk için video/yüz özellikleri indirilmez; 25 ses/etiket/kart dosyası
yaklaşık 233 MiB'dir. MediaSpeech arşivi 618.578.461 bayttır. Kaynaklar `data/`,
kesitler ve özel deney durumu `outputs/` altında Git dışında kalır. Mevcut
dosyanın içeriği farklıysa hazırlama üzerine yazmaz. Seçim sayısını büyütmek
önceki test kliplerini geliştirme bölümüne taşıyabileceğinden aynı manifest
sessizce genişletilmez; farklı protokol ve bağımsızlık açıklaması gerekir.

WebM çözmek için kabul edilmiş toplantı ortamındaki PyAV kullanılır. RTX yerel
kurulumunda mevcut imajla, yeni imaj veya paket indirmeden:

```powershell
docker run --rm --pull never --network none --entrypoint python --workdir /workspace --mount "type=bind,source=$PWD,target=/workspace" voiceup-inference-meeting:local scripts/prepare-turkish-meeting-evaluation.py --prepare
```

Bu hazırlama komutu GPU kullanmaz. Yerel Python ortamında PyAV zaten varsa
aynı hazırlama betiği doğrudan `--prepare` ile de çalışabilir. Varsayılan çıktı
`outputs/2026-09-13-turkish-evaluation/fixtures/protocol.json` olur. Kapsam ve
kaynak hashleri protokol ve `source_manifest.json` içinde korunur.

## Gerçek toplantı ve hafıza deneyi

Uygulamayı normal `scripts/start-local.ps1 -Mode Local` yolu ile açın. Boş
bir değerlendirme tenant'ındaki sıradan hesabın `meeting_analysis:read`,
`meeting_analysis:run`, `speaker_profiles:read` ve `speaker_profiles:write`
izinleri gerekir. Kimlik bilgileri yalnız özel yerel JSON'da bulunur;
mevcut kullanıcı galerisi deney için boşaltılmaz. Deney yeni toplantı ve
profil oluşturur. Bağımsız yeniden koşum için ayrı boş değerlendirme hesabı,
mevcut koşuma devam için aynı özel durum ve `--resume` kullanılır.

```powershell
.venv/Scripts/python.exe scripts/run-turkish-meeting-evaluation.py --protocol outputs/2026-09-13-turkish-evaluation/fixtures/protocol.json --credentials outputs/2026-09-13-turkish-evaluation/credentials.private.json --state outputs/2026-09-13-turkish-evaluation/meeting-state.private.json --output outputs/2026-09-13-turkish-evaluation/meeting-aggregate.json --experiment-metadata outputs/2026-09-13-turkish-evaluation/meeting-metadata.json --results-md results.md
```

Deney kimliği/veri rolü ve model sürümleri için metadata biçimi
[deney günlüğü rehberindedir](EXPERIMENTS.md). Aynı deneyin devamı, yeni bağımsız
örnek sayılmaz. Başarısız veya belirsiz kişiler paydalardan çıkarılmaz.
Zincir tamamlanmadığında nihai oranlar boş kalır; özel kontrol noktası ve
toplu günlüğe eksik durum yazılır.

Aynı görüşmelerle sayısı bilinen aday için **yeni boş hesap**, yeni durum/çıktı
yolları ve ayrı deney metadata dosyası kullanıp `--use-known-speaker-count`
ekleyin. Bu seçenek yalnız bu iki kişilik protokolde `participant_count=2` ve
`expected_speakers=2` gönderir; model/eşik değiştirmez. Aynı sesin ikinci kez
işlenmesi bağımsız yeni bir test kümesi oluşturmaz. Gerçek uygulamada toplantıya
katılanların üst sınırı ile gerçekten konuşanların kesin sayısı ayrıdır;
kesin sayı bilinmiyorsa zorla doldurulmaz.

## Doğrudan Türkçe metin deneyi

Mevcut CUDA toplantı imajı, yerel sabit Whisper paketi ve interneti kapalı
bir süreç kullanılır. Aynı GPU'da toplantı koşumuyla eşzamanlı başlatmayın.

```powershell
docker run --rm --pull never --network none --gpus all --entrypoint python --workdir /workspace --mount "type=bind,source=$PWD,target=/workspace" --env PYTHONPATH=/workspace/src:/workspace/app/inference:/workspace/scripts --env HF_HUB_OFFLINE=1 voiceup-inference-meeting:local scripts/evaluate-turkish-asr.py evaluate --role calibration --language tr --model-dir models/asr-large-v3/edaa852ec7e145841d8ffdb056a99866b5f0a478 --model-manifest scripts/asr-model-manifest.json --output outputs/turkish-asr-dev.private.json --experiment-id my-turkish-asr-dev-001 --results-md results.md
```

`--language auto` yalnız geliştirme adayını; `--role frozen-test` önceden
seçilmiş test kliplerini çalıştırır. Her yeni model koşumunun deney kimliği
ve çıktı yolu ayrı olmalıdır. Başarısız/eksik model koşumlarında başarı skoru
üretilmez. Skorlar `turkish-words-v1` normalizasyonuyla hesaplanır; tarihsel
`unicode-words-v1` sonuçları değiştirilmez. Yeni normalizasyon Türkçe harflerin
ölçümünü düzeltir, akustik modeli eğitmez.

Bu komutların gözlenen ortamı RTX 4060 ve mevcut x86_64 CUDA imajıdır; buradaki
deney sonucu Apple veya Spark üzerinde çalıştırılmış kanıt olarak sunulmaz.

## Daha geniş ve ayrı kayıtlarla test

[010 PRD](../specs/speaker-identity/PRDs/010-expanded-turkish-benchmark/PRD.md)
önceki 80 MediaSpeech klibini koruyarak kalan **2.433 klibin tamamını** ve
ikinci kaynak olarak **743 FLEURS Türkçe test kaydını** seçer. MediaSpeech
haber konuşması, FLEURS okunmuş konuşmadır. FLEURS test metadata'sındaki tüm
kayıtlar MALE olarak etiketlidir; 329 cümle kimliği 743 kez seslendirilmiştir.
Bu kaynaklarda sabit kişi/oturum kimliği yoktur. Klip sayısı kişi sayısı değildir.

```powershell
.venv/Scripts/python.exe scripts/evaluate-expanded-turkish-asr.py prepare-mediaspeech --root data/turkish/mediaspeech-expanded-v1
.venv/Scripts/python.exe scripts/prepare-fleurs-turkish.py --download
```

İlk komut mevcut doğrulanmış MediaSpeech arşivini okur; önceki dosya kimliği
ve ses hashlerini dışlar. FLEURS komutu yalnız sabit Türkçe test arşivi ve
etiket dosyasını indirir; özgün float WAV sesleri yeniden kodlamaz. Her iki
hazırlama mevcut farklı içeriğin üzerine yazmayı reddeder.

Mevcut yerel imajla tüm MediaSpeech ek testi:

```powershell
docker run --rm --pull never --network none --gpus all --entrypoint python --workdir /workspace --mount "type=bind,source=$PWD,target=/workspace" --env PYTHONPATH=/workspace/src:/workspace/app/inference:/workspace/scripts --env HF_HUB_OFFLINE=1 voiceup-inference-meeting:local scripts/evaluate-expanded-turkish-asr.py evaluate --root data/turkish/mediaspeech-expanded-v1 --model-dir models/asr-large-v3/edaa852ec7e145841d8ffdb056a99866b5f0a478 --model-manifest scripts/asr-model-manifest.json --output outputs/my-expanded-mediaspeech.private.json --experiment-id my-expanded-mediaspeech-001 --results-md results.md
```

FLEURS için `--root data/turkish/fleurs-tr-test-v1` seçip **yeni** çıktı yolu
ve deney kimliği kullanın. Model/çıkarım ayarları sabittir. İki GPU koşumunu
ve toplantı analizini aynı anda başlatmayın.

Kesilen aynı koşuma, aynı komuta `--resume` ekleyerek devam edilir. Klip
kontrol noktaları, manifest/ayar/model/deney bağlantısı doğrulanır; tamamlanan
klipler tekrar modele gönderilmez. Tamamlanmış koşumun devamı modeli yeniden
çalıştırmadan kaydedilmiş sonucu tekrar yayımlayabilir. Kaynak veya ayar
değiştiyse yeni deney gerekir. Özel `.clips` dizini ve `binding.json` birlikte
korunmalıdır; kilit/durum dosyalarını elle değiştirmeyin.

Sonuçların kelime ağırlıklı hata dağılımını ayrıca üretmek için:

```powershell
.venv/Scripts/python.exe scripts/report-expanded-turkish-asr.py --input outputs/my-expanded-mediaspeech.private.json --output outputs/my-expanded-mediaspeech-distribution.json
```

Bu rapor metinlerden metrikleri yeniden hesaplar; yalnız toplu kelime/süre,
tam eşleşme, klip hata yüzdelikleri ve 2.000 tekrarlı klip örnekleme aralığı
yayımlar. Aralık aynı kişi, oturum veya cümle bağımlılığını gidermez; toplum
geneline ait bir güven aralığı değildir. İki veri kaynağının skorları ayrı
okunur; haber ve okunmuş konuşma sonuçları tek toplantı doğruluğu olmaz.

## Kullanılmamış görüşme bölümleri

İlk deneydeki `[0,180)` aralığına dokunulmaz. Bütün altı görüşmede aynı
`[300,600)` ve `[600,900)` aralıkları seçilir; toplam 12 kesit ve 60 dakika
yeni ses içerir. Bunlar aynı altı kişinin aynı altı kaynak oturumundaki yeni
bölümleridir. Otomatik etkinlik ve doğrulanmamış metin/zaman uyarıları sürer.

```powershell
docker run --rm --pull never --network none --entrypoint python --workdir /workspace --mount "type=bind,source=$PWD,target=/workspace" voiceup-inference-meeting:local scripts/prepare-turkish-meeting-evaluation.py --prepare --preset window300 --output outputs/my-turkish-window300
```

İkinci hazırlama için `--preset window600` ve ayrı çıktı dizini seçilir.
Her pencere altı görüşmelik ayrı bir zincirdir; gerçek kişi sayısı bilgisi
bilindiğinden yürütücüye `--use-known-speaker-count` verilir. Her zincir için
**yeni boş ve sıradan yetkili değerlendirme hesabı**, farklı protokol/durum/
toplu çıktı/metadata yolları kullanılır. Önceki tenant veya kullanıcı
profilleri deney için silinmez. Günlükte ilk kayıt, dönüş başarısı ve son
birikimli galeri farklı ölçümlerdir.

Yeni deney kanıtları [geniş test raporunda](evidence/2026-09-13-expanded-turkish/README.md)
ve kök [results.md](../results.md) günlüğünde izlenir.
