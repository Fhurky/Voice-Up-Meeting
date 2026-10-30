# Toplantı doğruluğunu ölçme

Bir toplantıda doğru kişi sayısını bulmak, konuşulan her şeyi doğru kişiye
yazdığımızı tek başına göstermez. Kişi tanıma, konuşmacı aralıkları ve metin
hatalarını ayrı ölçeriz. Mevcut model zinciri Community-1 konuşmacı ayrımı,
WeSpeaker 256 boyutlu toplantı kimliği, bağımsız ECAPA 192 boyutlu kimlik denetimi
ve Whisper large-v3 metin çıkarımı kullanır. Yeni kişi kaydı bu modelleri yeniden
eğitmez; doğrulanmış ses örneğini ve modele özgü temsilleri saklar.

Kalıcı kişi tanımada, değerlendirmeye girecek kayıtlı kişiler ve sorgular
önceden sabitlenir. Her bilinen kişinin doğru kimlikle tanınması doğru kabul;
yanlış kimlikle tanınması hem yanlış kabul hem kaçırmadır. Bilinen kişinin
belirsiz veya kullanılamaz kalması da kaçırmadır. Galeri dışındaki bir kişinin
kayıtlı kimliklerden birine bağlanması yanlış kabuldür.

- **Precision (kesinlik):** Doğru kimlikle tanınan sorguları, doğru ve yanlış
  kimlik kabullerinin toplamına böleriz.
- **Recall (yakalama):** Doğru kimlikle tanınan bilinen sorguları, planlanan
  bütün bilinen sorgulara böleriz; profili oluşturulamayan kişiler paydada kalır.
- **F1:** Doğru kabullerin iki katını, doğru kabullerin iki katı ile yanlış
  kabuller ve kaçırmaların toplamına böleriz; kesinlik ve yakalamayı birlikte ölçer.
- **İlk kayıt kapsamı:** Gerçekte oluşturulabilen doğrulanmış profil sayısını,
  kaydedilmesi planlanan kişi sayısına böleriz.
- **Yanlış yabancı kabulü:** Galeri dışındaki kişilerden herhangi bir kayıtlı
  kimliğe bağlanan sorguları, bütün galeri dışı sorgulara böleriz.

Gerçekte kaydedilmiş kişilere koşullu yakalama da ayrıca verilebilir; bu sayı
ilk kayıt başarısızlıklarını içermediği için toplam yakalama yerine geçmez.
Bir payda boşsa skor üretilmez. Aynı sorguların 5/10/20/50 kişilik galerilerde
tekrar denenmesi bağımsız yeni ses örnekleri oluşturmaz; bu sonuçlar ayrı verilir.
Galeri büyüdükçe aynı sorguların bilinen/yabancı oranı da değişiyorsa precision
ve F1 değişimini yalnız galeri büyüklüğüne bağlayamayız; her aşamanın bilinen
ve yabancı sorgu sayısını ayrıca gösteririz.
Tek tek temiz kliplerle yapılan galeri ölçümü, uzun toplantının konuşmacı
ayrımı ve otomatik yeni kişi kaydıyla aynı uçtan uca deney değildir.

`cpWER`, her kişinin bütün sözlerini zaman sırasıyla birleştirip kişi etiketleri
arasında en düşük kelime hatası veren eşlemeyi bulur; değiştirme, silme ve ekleme
sayısının toplamını bütün referans kelimelerine böler. Eksik kişinin sözleri
silme, fazla kişinin sözleri ekleme olarak sayılır. Kelime hata oranı yüzde
100'ü aşabilir. Bu ölçü, isim verilmiş kalıcı kişilerin sonraki toplantıda aynı
kimlikle tanındığını kanıtlamaz. Tanım, [MeetEval'in kişi eşlemeli metin
değerlendirmesine](https://github.com/fgnt/meeteval) dayanır.

Kişisi belirsiz bütün metin ayrı bir akış olarak korunur. `assigned_only`, bu
akışı gerçek bir kişiye eşlemeyen ek bir hata ölçüsüdür; belirsiz kelime oranı
da ayrıca yazılır. Eksik referansta sıfır hata uydurulmaz. Tam referans olmayan
kesitler için metin puanı üretilmez. Kaynak aralığı uyuşması, kelime hata oranı
veya elle işaretlenmiş konuşmacı ayrım hatası olarak sunulmaz.

Çevrimdışı komut şu biçimde çalışır:

```powershell
.venv/Scripts/python.exe scripts/score-meeting-transcript.py --input evaluation.json --output metrics.json
```

Girdi her kişinin zaman sırasındaki bütün metnini bir kez içerir:

```json
{
  "schema_version": 1,
  "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reference_complete": true,
  "reference": [{"speaker_id": "reference-1", "text": "Toplantıya başlayalım"}],
  "hypothesis": [{"speaker_id": "observed-1", "text": "Toplantıya başlayalım"}]
}
```

Örnekteki hash yerine gerçek kaydın SHA-256 özeti yazılır; komut girdi dosyasının
hashini ayrıca hesaplar, kaynak sesi yeniden açmaz. Referansın gerçekten tam
olması ve zaman sırasının doğruluğu veri hazırlayıcısının sorumluluğundadır.
Belirsiz hipotez `speaker_id: null` kullanır. Çıktıda ham metin ve kişi adı yoktur;
mevcut çıktı dosyasının üzerine yazılmaz.

Sabit `unicode-words-v1` normalizasyonu Unicode NFKC ve küçük harf dönüşümü
uygular; harf, rakam, birleştirici işaret ve kelime içi kesme işaretini korur.
Noktalama ayırıcıdır; sayılar açılmaz ve kelimeler anlamına göre düzeltilmez.
Her tarafta en fazla 200 kişi akışı ve 50.000 kelime, çiftler toplamında en fazla
50 milyon karşılaştırma hücresi kabul edilir. Her tarafın toplam metni hem ham
hem Unicode dönüşümü sonrasında en fazla iki milyon karakter olabilir. Sınır aşımı hata verir; kelime veya
kişi sessizce kesilmez.

Model seçimini etkileyen önceki kayıtlar regresyon verisi olarak adlandırılır.
Yeni değerlendirme kişileri, parçaları ve hashleri onlardan ayrılır; seçim ve
normalizasyon sonuçlara bakılmadan sabitlenir. Kalite nedeniyle kaydedilemeyen
kişiler ve belirsiz sorgular paydada kalır. İngilizce sesli kitap ölçümü, doğal
Türkçe toplantı doğruluğu kabulü yerine geçmez.

Saklanan örnek ile toplantıdaki bütün konuşmacı grubu da ayrı değerlendirilir.
Bir kişinin temiz örneği korunurken, gruba yanlış bağlanan başka bir kişinin
sözleri aynı isimle gösterilebilir. Elli kişilik B/C denemelerinde 37 örneğin
tamamı değişmeden ve temiz kaldı; buna rağmen bazı tanınmış gruplarda yabancı
kaynak aralıkları bulundu. Bu nedenle örnek saflığı kimlik doğruluğu olarak
sunulmaz; bütün tanınmış satırlar, doğrulanamayan atamalar ve bütün 50 kişi
sonuçlarda görünür kalır.

Ek kaynak-süre ölçümü, kimlik atanmış her grubun sahip olduğu kaynak aralıklarını
profilin doğrulanmış sahibiyle karşılaştırır. Doğru sahip, başka kaynak, etiketsiz
eklenmiş boşluk ve yinelenen atama süreleri ayrı sayılır. Referanslar tam kaynak
cümlelerini ve iç sessizlikleri kapsadığı için bu ölçüm insan etiketli konuşmacı
ayrım hata oranı değildir. İlk tarif B görüldükten sonra keşif için oluşturuldu,
C sonucu görülmeden sabitlendi; [B raporu](evidence/2026-09-11-accuracy-audit/capacity50-native-b-memory-report.md)
ve [C raporu](evidence/2026-09-11-accuracy-audit/capacity50-native-c-memory-report.md)
ilk katı kişi eşleme sayılarıyla birlikte her iki ölçümü korur.

## AMI ile konuşmacı ayırma ve toplantılar arası kimlik

Konuşmacı ayırma ve kalıcı kimlik büyük ölçüde dilden bağımsız olduğundan, insan
etiketli İngilizce [AMI toplantı korpusu](https://groups.inf.ed.ac.uk/ami/corpus/)
ürünün gerçek HTTP akışıyla ölçülür. Ses CC BY 4.0'dır; referans RTTM/UEM dosyaları
Apache-2.0 lisanslı `pyannote/AMI-diarization-setup` deposunun
`67c2d539286e89f68952d5dcf83912bd9f01dfae` commit'indeki `only_words` kümesidir.
Resmî dev ve test bölümleri 34 toplantı ve 37 kişidir. Yakın mikrofon karışımı
(`headset`, Mix-Headset) ve tek uzak mikrofon (`array1`, Array1-01) ayrı koşulur. Bu
ölçüm Türkçe metin doğruluğu değildir; AMI metin skoru raporlanmaz.

Hazırlık açık bir ağ işlemidir. Referanslar sabit Git blob kimlikleriyle, sesler
manifestteki boyut ve SHA-256 değerleriyle doğrulanır; ham veri Git dışında
`data/ami/<commit>/raw/` altında kalır. Bazı AMI dosyaları yayın metadata parçaları
taşır ve sonlarında hiçbir RIFF parçasına ait olmayan fazladan bir bayt bulunur;
toplantı API'si böyle bir yüklemeyi reddeder. Bu yüzden ürüne gönderilen kopya
`audio/` altında yalnız `fmt` ve `data` parçalarından oluşan kanonik WAV'dır; ses
örnekleri bayt bayt aynıdır, çözülmez veya yeniden örneklenmez. Protokol dosyası her
iki kopyanın boyut ve SHA-256 değerini tutar. AMI aynası yalnız wget istemcilerine hizmet verdiğinden,
bilgisayarda wget yoksa indirme sabit imajdaki BusyBox wget ile yapılır:

```powershell
.venv/Scripts/python.exe scripts/prepare-ami-evaluation.py --download
.venv/Scripts/python.exe scripts/prepare-ami-evaluation.py --verify
```

Her koşum boş ve ayrılmış bir deney tenant'ında, `super_admin` olmayan sıradan bir
hesapla yapılır. Hesap aracı yalnız yerel geliştirme ortamında çalışır; parolayı
standart girdiden okur ve yazdırmaz. Parola ve adres, Git dışındaki
`outputs/ami/credentials-<ad>.private.json` dosyasında `url`, `username` ve `password`
alanlarıyla tutulur:

```sh
printf '%s\n' "$password" | sh scripts/stack.sh exec -T backend \
  python -m app.scripts.create_evaluation_account \
  --tenant-code eval-ami-array1-r1 --username eval-ami-array1-r1
```

```powershell
.venv/Scripts/python.exe scripts/run-ami-evaluation.py `
  --protocol data/ami/67c2d539286e89f68952d5dcf83912bd9f01dfae/protocol.json `
  --condition array1 --rotation 1 `
  --credentials outputs/ami/credentials-eval-ami-array1-r1.private.json `
  --state outputs/ami/eval-ami-array1-r1-state.private.json `
  --output outputs/ami/eval-ami-array1-r1-aggregate.json
```

Ortak kişisi olan toplantılar aynı bileşende toplanır; bileşenler kişi bakımından
ayrıktır. Rotasyon, bileşenleri dönüşümlü olarak galeri ve galeri dışı yarılara
ayırır; ikinci rotasyon rolleri değiştirir. Galeri toplantıları önce, otomatik hafıza
açıkken işlenir: bir kişinin ilk göründüğü toplantı kayıt, sonrakiler tanıma
denemesidir. Galeri dışı toplantılar otomatik hafıza kapalıyken işlenir ve orada
tanınan her kişi yanlış kabuldür. Ürüne yalnız karışık ses verilir; referans kişi
kodları değerlendiricide kalır. `--known-speaker-count` toplantının gerçek kişi
sayısını ipucu olarak verir. `--roster`, galeri toplantılarında o toplantıdaki
kişilerin daha önce kaydedilmiş profillerini katılımcı listesi olarak verir; henüz
kaydedilmemiş kişiler listede yer almaz. Listeli koşum, eşlenmiş karşılaştırma için
aynı koşul ve rotasyonda ayrı bir boş tenant ister.

Koşucu her toplantıdan sonra özel durum dosyasına yazar; aynı komut kesintiden devam
eder. Farklı yapılandırmayla, başka hesapla veya dolu bir tenant'ta devam etmez.
Durum dosyası ham kişi eşlemesi içerir ve yayımlanmaz.

Ölçütler:

- **DER (konuşmacı ayırma hata oranı):** UEM içindeki referans konuşma süresine göre
  kaçırılan konuşma, yanlış alarm ve kişi karışması; örtüşen konuşma dahildir. Collar
  0 ve sınırların iki yanında 0,25 saniye tolerans ayrı verilir. Toplantı bootstrap'ı
  ile %95 aralık hesaplanır.
- **JER (Jaccard hata oranı):** her referans kişinin, ona eşlenen küme ile zaman
  kesişiminin birleşimine oranından hesaplanan hatanın kişiler üzerinden ortalaması.
  Birden çok kümeye bölünen bir kişiyi, DER'deki kısa karışma süresinden daha görünür
  cezalandırır.
- **Kimlik:** bir toplantıda en az 3 saniye referans konuşması olan her kişi bir
  görünümdür. Bir kümenin konuşma süresinin en az yarısı tek kişiye aitse küme o
  kişiye bağlanır; profilin sahibi, profili oluşturan kümenin kişisidir. Tanınan
  profillerden biri başka kişiye aitse görünüm yanlış kişi, hepsi doğru kişiye aitse
  doğru; tanıma yokken yeni profil açılmışsa yinelenen profil, hiçbiri yoksa kaçırılan
  sayılır. Galeri dışı görünüm, herhangi bir tanıma varsa yanlış kabul, yoksa rettir. Tanıma oranı ve FPIR (galeri dışı yanlış kabul oranı)
  kişi bootstrap'ı ile verilir; aynı kişinin görünümleri bağımsız örnek sayılmaz.

Toplu sonuç `results.md` günlüğüne `--kind public_benchmark` ile yazılır. Metadata,
`dataset: ami`, `dataset_revision` olarak referans commit'i, `language: en`,
`pipeline: meeting-memory` ve `runtime_profile` alanını içerir; farklı GPU profillerindeki
sonuçlar tek seride birleştirilmez:

```powershell
.venv/Scripts/python.exe scripts/record-experiment.py `
  --input outputs/ami/eval-ami-array1-r1-aggregate.json `
  --experiment-metadata outputs/ami/eval-ami-array1-r1-metadata.json `
  --kind public_benchmark
```
