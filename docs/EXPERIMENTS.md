# Deneyleri kaydetme

Kök [results.md](../results.md), model denemelerinin toplu sonuç günlüğüdür.
Otomatik birim test sayıları bu dosyada model doğruluğu gibi gösterilmez.
Her planlı model denemesi açık bir deney kimliği, veri rolü ve değişmez kaynak
bilgisiyle başlatılır. Kaynak kayıtları, referans metinleri ve özel işlem
durumları `data/` veya `outputs/` altında kalır.

## Standart komutlar

Bir deneme için yalnız yayımlanabilir alanlar içeren metadata dosyası hazırlayın:

```json
{
  "experiment_id": "tr-mediaspeech-calibration-fixed-v1",
  "date": "2026-09-13",
  "dataset": "mediaspeech-tr",
  "dataset_revision": "frozen-source-manifest-v1",
  "language": "tr",
  "role": "calibration",
  "pipeline": "meeting-asr",
  "models": [{
    "id": "Systran/faster-whisper-large-v3",
    "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478"
  }]
}
```

Örnek veri sürümü alanını gerçek sabit revision veya kaynak manifest hashine
göre doldurun. İsteğe bağlı `protocol_sha256`, `configuration_sha256`,
`code_commit` ve `elapsed_seconds` eklenebilir. Token, parola, kullanıcı/tenant
kimliği, kişi adı, ses veya metin eklenmez; beklenmeyen metadata alanı reddedilir.

Tam referanslı, kişi başına birleştirilmiş metin deneyi:

```powershell
.venv/Scripts/python.exe scripts/score-meeting-transcript.py `
  --input outputs/experiment/private-transcript.json `
  --output outputs/experiment/aggregate.json `
  --normalization turkish-words-v1 `
  --experiment-metadata outputs/experiment/metadata.json `
  --results-md results.md
```

Mevcut kimlik deneyinde `evaluate-public-speakers.py` komutuna aynı
`--experiment-metadata` ve `--results-md` seçenekleri eklenir. Gerçek koşucunun
son başarısı veya eksik durumu otomatik kaydedilir; metadata hashinin değişmesi
eski özel koşum durumuyla devam etmeyi reddettirir. Bu koşucu hâlâ İngilizce
LibriSpeech/ECAPA protokolüdür; Türkçe ses ona İngilizce etiketiyle verilmez.
Mevcut gözlemleri yeniden puanlayan `report-public-speakers.py` komutunda da
bu seçenekler `--metrics-protocol voiceup-open-set-v1 --manifest ...` ile kullanılır.

Bu seçenekler standart deney çağrısının parçasıdır. Metadata olmadan kullanılan
eski düşük seviyeli komutlar geriye uyumluluk için günlük yazmaz. Metadata
verildiğinde günlük varsayılanı depo kökündeki `results.md` olur; testlerde
mutlaka geçici bir günlük yolu verilir. `--results-md` tek başına kabul edilmez.

## Mevcut toplu sonucu tekrar kaydetme

```powershell
.venv/Scripts/python.exe scripts/record-experiment.py `
  --input outputs/experiment/aggregate.json `
  --experiment-metadata outputs/experiment/metadata.json `
  --kind transcript --results-md results.md
```

Desteklenen türler:

| Tür | Anlamı |
|---|---|
| `identity` | Manifest bağlı `voiceup-open-set-v1` kimlik ve bilinmeyen kişi metrikleri |
| `transcript` | Tam referanslı, kişi eşlemeli cpWER ve belirsiz akış cezalı maliyet |
| `asr_clips` | MediaSpeech Türkçe protokolünde klip başına hesaplanan kelime hatalarının toplamı |
| `meeting_identity` | Real-TurnTurk zincirinin açıkça zayıf otomatik referanslı tanı ölçümü |
| `observation` | Referansı veya tamamlanmış ölçümü bulunmayan sayısal gözlem; doğruluk skoru yok |
| `transcript_review` | Ham ve önerilen metnin eşlenmiş kelime hata oranı, referansa göre öneri isabeti ve temiz metni bozma oranı |

Bağlamsal düzeltme koşucusu `scripts/evaluate-transcript-review.py` önce
`prepare` ile örnekleri sabitler, sonra `run` ile çalışan arka uçtaki aynı
Ollama adaptörünü ve koruma politikasını kullanır. `--fixture` kontrollü
Türkçe örnekler; `--corpus` tamamlanmış gerçek ASR özel raporu içindir.
Gerçek örnekler temiz/hatalı katmanlardan kaynak SHA-256 sırasıyla seçilir;
ayrı klipler komşu konuşma diye birleştirilmez. Özel çıktı `outputs/` altında,
toplu skor `results.md` içinde tutulur. Başarısız istek ham metniyle paydada kalır.
İsabet, önerinin tek başına uygulanmasının referansa göre hatayı azaltmasıdır;
temiz metni bozma, başlangıçta sıfır kelime hatası olan satırın sonradan hatalı
olmasıdır. Kontrollü örnek ve veri setinin sağladığı, bu koşumda dinlenmemiş
referans birbirinden ayrılır; bunlar insan onaylı toplantı başarısı sayılmaz.

Real-TurnTurk'te konuşma etkinliği otomatik etiketlidir; metin ve zaman
damgaları insan doğrulamasıyla teyit edilmemiştir. Skor tablosundan önce bu
sınır gösterilir. Sıralı toplantılar bir kişiyi daha sonraki görünümünde
kaydedebilir: eski ham `enrollment_coverage` koşu sonundaki birikimli oran,
`first_enrollment_coverage` ilk görünümdeki orandır. Günlük yeni kayıtlarında
birikimli oranı `cumulative_enrollment_coverage` adıyla açıkça ayırır; eski
kayıtta ilk görünüm alanı yoksa yeni ölçülmüş gibi doldurmaz.

Toplantı adayında `use_known_speaker_count` alanı gerçek deney girdisini taşır:
true ise her kayıt için `expected_speakers=2` ve `participant_count=2`
gönderilmiştir; false ise kişi sayısı ipucu verilmemiştir. Bu alan yalnız
boolean kabul eder; eski sonuçta bulunmuyorsa kayıt yapılmış gibi eklenmez.

`--evidence docs/evidence/.../aggregate.json` ile yayımlanabilir gerçek bir
toplu JSON dosyasına bağlanılabilir; dosyanın SHA-256 özeti günlüğe yazılır.
Ham/private çıktı dosyası bu seçeneğe verilmez. Günlüğün kendi makine bloğu
ayrıca kanonik toplu nesnenin hashini taşır; hash ham sesin içeriğini açıklamaz.

## Tarihsel başlangıç çizgisi

```powershell
.venv/Scripts/python.exe scripts/record-experiment.py `
  --backfill-reviewed-history --results-md results.md
```

Bu işlem açıkça listelenmiş 13 tarihsel toplu kaydı aktarır: üç eski 50 kişilik
ECAPA skoru; ASR taban çizgisi ve reddedilen iki aday; 50 kişilik A/B/C'nin ayrı
metin ve hafıza gözlemleri; referanssız tek konuşmacılı Türkçe kaynak denemesi.
Dosya ağacında iyi skor aramaz, eski kanıtı değiştirmez veya modeli çalıştırmaz.
Eski `fresh` adı o tarihteki ayrımı anlatır; bugünkü kayıtta rolü regresyondur.
Reddedilen adayın daha düşük kelime hatası, bütün kabul koşullarını geçtiği
anlamına gelmez. Hafızada kesinleştirilemeyen atamalar için precision/F1
uydurulmaz; 35/50 doğru geri dönüş, yalnız doğrulanan alt kümeden yüzde yüz
başarı çıkarma gerekçesi değildir.

Bu envanter bütün eski debug dosyalarının sayısal doğruluk deneyi olduğunu
varsaymaz. Kontrollü saf eşleştirici galerileri ve native HTTP uçtan uca işler
ayrı protokollerdir; önceki raporlar kendi [kanıt dizinlerinde](evidence/) kalır.

## Yorumlama ve dayanıklılık

`calibration` ayar geliştirme verisi, `regression` önceden görülmüş kontrol,
`frozen-test` ayar seçiminden ayrılmış ve dondurulmuş test, `smoke` ise akış
denemesidir. Ayrılmış test sonucuna bakıp ayar seçilirse veri artık geliştirme
verisidir. Farklı kliplerin farklı mikrofon, kişi veya oturum olduğu varsayılmaz.

Aynı deneyin aynı toplu sonucunu tekrar kaydetmek değişiklik yapmaz. Devam eden
deneyin yeni sonucu aynı kimlik altında sonraki sürüm olur; eski sürümler korunur.
`failed`, `incomplete` ve `unscored` skorları `null`/`—` gösterilir. Yanlış veya
eksik toplu hesap kabul edilmez; eksik kelimeler ve başarısız kişiler uygun
metrik paydasından düşürülmez. Tamamlanmış ölçüm, başarılı ürün kabulü demek değildir.

Yazma, tek yazıcı kilidi ve geçici dosyadan atomik değiştirmeyle yapılır; hata
olursa önceki günlük korunur. Eşzamanlı yazar kilidi alamazsa açık hata alır.
İşletim sistemi çökmesinden kalan `results.md.lock` otomatik silinmez: önce
gerçekten çalışan yazar bulunmadığı doğrulanmalıdır. Elle yazılan açıklamalar
korunur; bozuk makine kanıt bloğu sessizce düzeltilmez. Veri ve günlük bağlantıları
yereldir; kayıt işlemi ağa çıkmaz, model veya uygulama veritabanına erişmez.

### Model seçimi ve görünür öneriler

`evaluate-transcript-review.py run --visible-model <kurulu-ad>` aynı dondurulmuş
örnekleri yeni `tr-context-words-v2` politikasıyla çalıştırır. Tam kurulu ad
ve digest eşleşir; metadata model kimliği `ollama/` önekiyle ve `:` yerine
`-` kullanılarak kaydedilir. Varsayılan eski komut 012'nin filtreli politikasını
korur. Kaynak karmasına yeni öneri domain dosyası da katılır.

Yeni `voiceup-context-review-visible-v1` protokolü kayda uygun yanıttaki bütün
eşlenebilir önerileri ölçer; anlamsal inceleme işaretli değişiklikler de paydada kalır. Makine
metriklerindeki `accepted_edits`, bu protokolde metne eşlenen düzenlemedir,
kullanıcı tarafından kaydedilmiş veya onaylanmış anlamına gelmez.
`rejected_edits` eşlenemeyen veya geçersiz/kesilmiş yanıttan dolayı kayda
alınamayan önerilerin sayısıdır. Böyle bir yanıtın kısmen eşlenen metni
görünür kalsa da kalite hesabında özgün metin kullanılır. Ham model cevabı
Git dışındaki satır kanıtında kalır; toplu rapor model durumlarını, kayda
uygun satırları ve inceleme işaretli değişiklik sayısını ayrıca verir.
Geçersiz/boş sonuçla referansa göre iyileşme uydurulmaz; eski günlük blokları
yeniden yazılmaz. Uygulamadaki kaydetme davranışı ayrı işlevsel deneydir.
