# Teams toplantılarında en yüksek doğruluk için rota

Tarih: 2026-11-17. Kullanıcının "projeyi incele, ortalama 7–8 ve en çok 15 kişilik Teams toplantılarında en yüksek
doğruluğu sağlayacak rotayı hazırla" talimatıyla yazıldı. Bu dosya karar öncesi çalışma belgesidir
([plans/README.md](README.md)); iş gereksinimlerinin otoritesi kabul edilmiş PRD'lerdir. Buradaki her adım kendi
PRD'siyle başlar ve o PRD kullanıcı tarafından açıkça kabul edilmeden uygulanmaz.
Profil: `kt-vibecoding-python-web-v2`; FastAPI/Python, React/Vite ve PostgreSQL/SQLAlchemy/Alembic korunur.

## 1. Hedef kullanım ve başarı ölçütleri

- Girdi: Teams toplantı kaydı (MP4), Türkçe, 30–90 dakika, ortalama 7–8 ve en çok 15 konuşan kişi.
- Çoğu toplantı aynı ekiplerin tekrarıdır; aynı kişiler haftalar boyunca yeniden görülür. Rotanın en büyük
  kaldıracı budur: kişi bir kez doğru kaydedilirse sonraki toplantılarda tanınır.
- Çalışma ortamı kurum içi ağdır; çalışma anında internet ve model indirme yoktur.

| Ölçüt | Hedef | Kaynak |
| --- | --- | --- |
| Yanlış kişiye atama | 0 | 30 Ekim 2026 hedef sırası |
| Konuşmacı ayırma hatası (DER, collar 0) | %20 altı | 30 Ekim 2026 hedef sırası |
| Toplantıda Türkçe kelime hatası (WER) | %15 altı | 30 Ekim 2026 hedef sırası |
| Kayıtlı kişiyi tanıma | %85 ve üstü | 30 Ekim 2026 hedef sırası |
| Kişi sayısı sapması | 8 kişide en çok 1, 15 kişide en çok 2 | Bu rotanın önerisi; PRD kabulünde kesinleşir |

## 2. Bugünkü ölçülmüş durum

| Alan | Ölçüm | Not |
| --- | --- | --- |
| Konuşmacı ayırma, AMI 34 toplantı, uzak mikrofon | DER %26,17 (kaçırılan 9,49 · yanlış alarm 4,87 · karışma 11,82) | `results.md`, `eval-ami4-array1-r2`; en büyük pay karışma |
| Konuşmacı ayırma, AMI test 16 toplantı | Uzak mikrofon %27,56 · yakın mikrofon %22,43 | Ek A'daki karşılaştırmanın taban çizgisi |
| Toplantılar arası tanıma, AMI | 33/46 (%71,7); yanlış kişi 1/46; yabancıyı tanıdık sanma 0/63 | 10 saniye kuralıyla |
| Türkçe okunmuş konuşma | FLEURS WER %6,49 | Toplantı değildir |
| Türkçe haber konuşması | MediaSpeech WER %14,03 | Toplantı değildir |
| Türkçe iki kişilik görüşme | cpWER %22–42 (6 görüşme) | Referans otomatik ve insan doğrulamasız |
| Gerçek Türkçe toplantı, 11 konuşmacı, 36 dk | 15 konuşmacı bulundu (13'ü 10 saniyeden uzun) | Etiket yok; yalnız sayım |
| Gerçek Türkçe toplantı, 4 konuşmacı, 84 dk | 7 konuşmacı bulundu (4'ü konuşmanın %98,5'i) | Etiket yok; yalnız sayım |
| Aynı iki toplantıda işaretli kelime payı | Belirsiz %6,3 ve %11,2 · örtüşme %5,3 ve %9,8 | 17 Kasım 2026, kayıtlı sonuçlardan |
| Aynı iki toplantıda ses kanıtı yetersiz konuşmacıların kelime payı | %3,4 ve %64,4 | Temiz kanıtı 10 saniyenin altında kalanlar; aşağıda T2 |

Ölçülmeyenler: gerçek Teams kaydı (eldeki MP4 bir Teams kaydı değildir), 7–15 kişilik etiketli toplantı,
toplantıda Türkçe kelime hatası, Türkçe toplantıda kişi tanıma.

## 3. Teşhis: hata nereden geliyor

T1 — Konuşmacılar 5 dakikalık parçalarda ayrılıyor, toplantı sonunda parça başına tek bir vektörle birleştiriliyor.
Ayırma modeli (`pyannote/speaker-diarization-community-1`) tüm kaydı tek geçişte işlemek için tasarlanmıştır;
ürün onu 310 saniyelik pencerelerde çalıştırır (`app/backend/app/domain/meeting.py` `CORE_SECONDS`), sonra
`reconcile_tracks` parça izlerini kosinüs benzerliğiyle kümeler. Ayrıca servis, modelin varsayılanından farklı bir
kümeleme ayarı kullanır (`meeting_models.py`: `Fa` 0,15; modelin kendi ayarı 0,07). 17 Kasım ölçümü (Ek A):
aynı model, modelin kendi ayarıyla ve tek geçişte çalışınca AMI test kümesinde DER
uzak mikrofonda %27,56'dan %19,90'a, yakın mikrofonda %22,43'ten %17,05'e iniyor; 16 toplantının 16'sında da
tek geçiş daha iyi. Farkın neredeyse tamamı konuşmacı karışmasıdır (12,25 → 4,93 ve 9,04 → 3,95 puan).
Bu, model kartının yayımladığı sayılarla örtüşür (AMI yakın %17,0, uzak %19,9).

T2 — Kişi sayısı fazla çıkıyor. İki gerçek Türkçe toplantıda 11 yerine 15, 4 yerine 7 konuşmacı bulundu. Az konuşan
kişinin bir parçadaki kısa izi gürültülü bir vektör üretir ve kendi kümesinde kalır. Katılımcı sayısı modele yalnız
parça başına üst sınır olarak gider; toplantı düzeyinde bir kısıt yoktur. Karışık kümeler hafızayı da kilitler:
4 kişilik 84 dakikalık toplantıda kelimelerin %64'ü, ses kanıtı "tutarsız ses" veya yetersiz süre nedeniyle
10 saniyenin altında kalan konuşmacılara aittir; bu kişiler ne tanınabilir ne kaydedilebilir.
17 Kasım ölçümünde tek geçiş aynı iki kayıtta tam 11 ve tam 4 konuşmacı buldu (Ek A). Bu kayıtların etiketi
olmadığı için bu yalnız sayım kanıtıdır; kimin hangi sözü söylediğinin doğruluğu ölçülmedi.

T3 — Kimlik kararı her konuşmacı için ayrı verilir. `MeetingMemory.persist` her toplantı konuşmacısını eşik ve farkla
tek başına değerlendirir; aynı profile iki konuşmacı düşerse ikisi de belirsiz kalır. Katılımcı listesi verildiğinde bile
"bu 8 kişi şu 8 profilden hangisi" sorusu birlikte çözülmez.

T4 — "Bir kez adlandır, hep tanı" akışı eksik. Otomatik kayıt, yanlış kişi riskinden dolayı varsayılan kapalıdır
(021 Decision 7). Sonuç ekranında ad vermek yalnız `display_name` yazar (`MeetingService.rename`); profil
oluşturmaz. Kullanıcı doğru adı verse de bu bilgi sonraki toplantıya taşınmaz. Belirsiz eşleşmede aday kişi
kullanıcıya onay için sunulmaz.

T5 — Metin ayarları geneldir. `LocalMeetingModels.transcribe` Whisper large-v3'ü sabit ayarla çağırır: toplantı
konusu, katılımcı adları ve kurum terimleri modele verilmez. Kurulu `faster-whisper` 1.2.1 bunun için `hotwords`
ve `initial_prompt` seçeneklerini taşır; kullanılmıyor. İki kişilik Türkçe görüşmelerde ölçülen cpWER (%22–42),
okunmuş konuşmadaki kelime hatasının (%6,5) birkaç katıdır; referans zayıf olduğu için bu yalnız yön gösterir.

T6 — Düzeltme döngüsü yok. Sonuç ekranında ad verme, dinleme ve tek satır metin önerisi var; iki konuşmacıyı
birleştirme, bir satırı başka kişiye atama ve dışa aktarma yok. Kullanıcının yaptığı düzeltme sisteme geri dönmüyor,
ölçüm etiketi olarak da kullanılamıyor.

T7 — Teams'in kendi bilgisi kullanılmıyor. Teams katılımcı raporu kişi sayısını ve adları verir. Teams dökümü
(`.vtt`) açıksa konuşmacıyı hesap kimliğinden yazar; kişi kendi cihazından katıldığında bu güvenilirdir, aynı
odadan tek cihazla katılanlarda değildir. Türkçe toplantı dökümü desteği bu çalışmada doğrulanamadı (Open Question 1).

T8 — Ölçüm zemini dar. AMI 4 kişilik İngilizce oda toplantısıdır. 7–15 kişilik, Türkçe ve Teams kanalından
geçmiş etiketli veri yoktur; hedeflere ulaşıldığı bugünkü veriyle kanıtlanamaz.

## 4. Rota

Adımlar uygulama sırasındadır. Her adım küçük tutulur, kendi ölçümüyle kapanır ve bir öncekinin kazanımını
geriletmediğini aynı ölçümle gösterir.

| Adım | İş | Önerilen PRD | Bağımlılık | Beklenen etki |
| --- | --- | --- | --- | --- |
| 1 | Tüm kayıtta tek geçişte konuşmacı ayırma | 030 | — | Ölçüldü: Ek A |
| 2 | Çok konuşmacılı ve Türkçe ölçüm kümesi | 031 | — | Sonraki adımların kanıtı |
| 3 | Onaylı kişi kaydı ve belirsiz eşleşmede öneri | 032 | 1 | Tanıma oranı; yanlış kişi riski olmadan |
| 4 | Katılımcı raporu ve liste içinde birlikte eşleme | 033 | 1, 3 | Tanıma oranı, kişi sayısı |
| 5 | Konuşmacı düzeltme ve dışa aktarma | 034 | 1 | Düzeltme süresi; etiket üretimi |
| 6 | Gerçek Türkçe toplantı ölçümü | 024 (taslak, kabul bekliyor) | 5 | Gerçek taban çizgisi |
| 7 | Metin: bağlam ipucu ve çözümleme ayarı | 035 | 2 veya 6 | Kelime hatası |
| 8 | Metin: model karşılaştırması | 036 | 7 | Kelime hatası |
| 9 | Model yükseltme adayları | Karşılaştırma sonucuna göre | 1–8 | Yalnız hedef tutmazsa |
| 10 | Kurum platformu ve verimlilik analizi | 018, 023 (taslak) | Platform cevapları | Kullanım |

### Adım 1 — Tüm kayıtta tek geçişte konuşmacı ayırma (PRD 030)

Neden: T1 ve T2. Tek ölçülmüş ve en büyük kazanım budur; yeni model, yeni paket ve yeni veri gerektirmez.

Önerilen tasarım ("önce ayır, sonra yaz"):

1. Yükleme tamamlanınca worker ilk iş olarak tüm kaydı çıkarım servisine tek istekte gönderir. Yeni uç nokta
   (`/v1/meeting-diarization`) tüm kayıt için konuşmacı aralıklarını, örtüşmesiz aralıkları ve konuşmacı
   vektörlerini döndürür. Tarif modelin kendi ayarıdır; sürümlü yeni bir tarif adıyla kaydedilir.
2. Sonuç toplantıya bağlı kalıcı bir kayıtta saklanır (şema değişikliği; 41 numaralı kuraldaki zorunlu sütunlar).
3. Parça istekleri yazıya çevirme ve ses kanıtı için sürer, ancak kendi ayırmasını yapmaz: worker, parçanın
   penceresine düşen toplantı düzeyi aralıkları istekle verir. Parça etiketi artık toplantı düzeyindeki
   konuşmacıdır; parçalar arası akustik eşleme (`choose_acoustic_track`) ve toplantı sonu birleştirme
   (`reconcile`) bu yolda çalışmaz.
4. Katılımcı sayısı tek geçişe `max_speakers` olarak verilir; kesin sayı zorlanmaz (herkes konuşmayabilir).
5. Geri dönüş: ölçülen süre veya bellek sınırını aşan çok uzun kayıtlar ve CPU modu mevcut parçalı yolu kullanır.
   Sınır tahminle değil ölçümle konur (Ek A'daki süre ve bellek değerleri başlangıçtır).

Dokunulacak yerler: `app/inference/voiceup_inference/` (`api.py`, `runtime.py`, `meeting_runtime.py`,
`meeting_models.py`), `app/backend/app/services/` (`meeting_worker.py`, `meeting_chunks.py`, `meeting_ports.py`),
`app/backend/app/infrastructure/meeting_inference.py`, `app/backend/app/domain/models/meeting.py`, Alembic
migrasyonu, ilerleme gösterimi için ön yüz durum metni. İstek boyutu: 90 dakikalık 16 kHz tek kanal kayıt
yaklaşık 173 MB'tır; akışla gönderim gerekir.

Ölçüm aracı PRD'nin parçasıdır: tek geçiş ile parçalı sonucu aynı puanlayıcıyla karşılaştıran betik
(`scripts/`, testleriyle). Ek A'daki ölçüm geçici betikle yapıldı; kalıcı değildir.

Kabul önerisi: AMI test kümesinde ürün akışıyla (API'den okunan `speaker-turns` ile) uzak mikrofonda DER
%21'in, yakın mikrofonda %18'in altındadır (Ek A'daki tek geçiş %19,90 ve %17,05); tanıma ve yanlış kişi ölçümü
(`eval-ami4-array1-r2` protokolü) gerilemez; iki gerçek Türkçe toplantıda 11 ve 4 konuşmacı bulunur; tam kalite
kapısı geçer; canlı tarayıcı geçişi yapılır.

Riskler: bellek kayıt süresiyle büyür (ayrı süreçte 84 dakikada 5,0 GiB; bu makinenin Docker sanal makinesi
7,35 GB) ve 2 saatin üstü ölçülmedi; CPU modunda tek geçiş süresi ölçülmedi; Ek A `test` kümesini bir kez
gördü, bu yüzden ayar yalnız AMI `dev` kümesinde yapılır ve `test` kabulde bir kez daha ölçülür.

### Adım 2 — Çok konuşmacılı ve Türkçe ölçüm kümesi (PRD 031)

Neden: T8. Adım 3–9'un kazancı bugünkü veriyle gösterilemez.

- Çok konuşmacılı gerçek toplantı: AMI'den kalabalık, açık lisanslı bir toplantı derlemi AMI hazırlayıcısının
  kalıbıyla eklenir. Dil İngilizce olabilir; konuşmacı ayırma ve kişi sayısı için kullanılır. Adaylar: NOTSOFAR-1
  (4–8 kişi, toplantı odası), VoxConverse (21 kişiye kadar), ICSI (3–10 kişi, ortalama 6). 17 Kasım aramasında
  ICSI için açık lisans doğrulanamadı (dağıtım LDC anlaşmasıyla görünüyor); her adayın lisansı ve erişimi kabulden
  önce doğrulanır.
- Sentetik Türkçe toplantı: konuşmacı kimliği ve metni bilinen Türkçe kliplerden 8 ve 15 kişilik, 25–40 dakikalık
  toplantılar üretilir. Konuşma payları dengesizdir (en az konuşan kişi %2'nin altında), kısa sıra değişimleri ve
  az örtüşme içerir, her konuşmacı ayrı bir kanal ve kodek zincirinden geçer. Aynı kişilerle ikinci oturum ve
  listede olmayan konuk da üretilir. Referans tamdır: zaman, kişi, metin. Aday kaynak Common Voice Türkçe'dir;
  kullanım koşulları konuşmacının gerçek kimliğini belirlemeye çalışmayı yasaklar, takma kimlikle eşleme
  ölçümünün bu koşula uygunluğu kabulden önce teyit edilir.
- Sınır açıkça yazılır: sentetik toplantı okunmuş konuşmadır; mutlak doğruluk kanıtı değil, adımlar arası
  karşılaştırma aracıdır.
- Tek komutla koşan ölçüm paketi: AMI test, çok konuşmacılı küme, sentetik Türkçe; toplu sonuç `results.md`'ye.

Kabul önerisi: kümeler `dev` ve `test` olarak ayrılır; hazırlayıcılar ve puanlayıcı testlidir; Adım 1 sonrası
ürünün bu kümelerdeki taban çizgisi `results.md`'dedir.

### Adım 3 — Onaylı kişi kaydı ve belirsiz eşleşmede öneri (PRD 032)

Neden: T4. Tekrarlayan toplantılarda doğruluğu en çok artıran ve yanlış kişi riskini insan onayıyla sıfırda
tutan adımdır. Kayıt, Teams sesinin kendisinden yapıldığı için sonraki Teams toplantısıyla aynı kanaldadır.

- Sonuç ekranında, yeterli temiz konuşması olan adsız konuşmacı için "Hafızaya kaydet": kullanıcı adı verir,
  mevcut kalite denetimleri çalışır, profil toplantı sesinden oluşur. Kaynak ses saklama süresi içinde olmalıdır.
- Belirsiz eşleşmede en iyi aday gösterilir; kullanıcı onaylarsa konuşmacı o profile bağlanır.
- Onaylanan tanıma, profile yeni örnek olarak eklenebilir (mevcut 20 örnek sınırı ve kalite kuralları).
- Otomatik kayıt varsayılanı kapalı kalır.

Dokunulacak yerler: `meeting_memory.py` içindeki kayıt dalının yeniden kullanımı, yeni uç noktalar, OpenAPI ve
tipler, `MeetingResults.tsx`, TR/EN metinler, kalıcı tarayıcı senaryosu.

Kabul önerisi: iki oturumlu ölçümde (AMI ve sentetik Türkçe) ilk oturumda onayla kaydedilen kişilerin ikinci
oturumda tanınma oranı raporlanır; onaysız hiçbir profil oluşmaz; yanlış kişi 0.

### Adım 4 — Katılımcı raporu ve liste içinde birlikte eşleme (PRD 033)

Neden: T2, T3, T7.

- Teams katılımcı raporu (CSV) toplantı oluştururken yüklenebilir: kişi sayısı ve adlar okunur, adlar kayıtlı
  profillerle eşleştirilir, belirsiz ad kullanıcıya sorulur. Sonuç mevcut `participant_count` ve
  `participant_profile_ids` alanlarına yazılır. Rapor adları ve katılma/ayrılma zamanlarını içerir ve yalnız
  düzenleyen kişi indirebilir; sütun adları kaynaklarda doğrulanamadı, gerçek bir örnekle sabitlenir (Open Question 2).
- Liste verildiğinde kimlik birlikte çözülür: konuşmacı–profil skor tablosunda bire bir en iyi eşleme aranır,
  her eşleme yine eşik ve fark koşulunu sağlamalıdır. Liste dışı daha iyi aday varsa karar belirsiz kalır (016).
- Aynı odadan tek cihazla katılanlar raporda tek kişi görünür; kişi sayısı bu yüzden üst sınır olarak değil
  ipucu olarak kullanılır ve kullanıcı düzeltebilir.

Kabul önerisi: liste verilen koşularda tanıma oranı listesiz koşuya göre artar, yanlış kişi ve yabancıyı
tanıdık sanma artmaz (AMI liste koşusu ve sentetik Türkçe).

### Koşullu adım — Teams dökümünü içe aktarma

Yalnız Open Question 1'in cevabı evetse ayrı bir PRD ile. `.vtt` dosyasındaki ad ve zaman bilgisi iki işe yarar:
konuşmacılara ad önerisi (kullanıcı onayıyla, Adım 3'teki kayıtla birlikte) ve Adım 6 için ölçüm etiketi taslağı.
Aynı odadan tek cihazla katılanlarda ad güvenilmezdir; içe aktarılan ad her zaman öneridir, kimlik kararı değildir.

### Adım 5 — Konuşmacı düzeltme ve dışa aktarma (PRD 034)

Neden: T6. Düzeltilmiş toplantı aynı zamanda ölçüm etiketidir; 024'ün etiketleme maliyetini düşürür.

- İki konuşmacıyı birleştirme, bir satırı başka konuşmacıya atama. Model çıktısı değişmez; düzeltme ayrı
  saklanır ve geri alınabilir (013'teki kayıtlı metin düzeltmesi kalıbı).
- Dışa aktarma: CSV (`start`, `end`, `speaker`, `text`; 024 Decision 2 biçimi) ve okunabilir belge.
- Kişi bazında puan veya sıralama üretilmez (023 Decision 6 ile aynı sınır).

### Adım 6 — Gerçek Türkçe toplantı ölçümü (PRD 024)

024 taslaktır; kabulü ve Open Question 3 ile 4'ün cevabı gerekir. Adım 5'in düzeltme ekranı ve dışa aktarması
etiketlemeyi uygulama içinde yapılabilir kılar. En az üç gerçek Teams kaydı ölçülür; biri 12–15 kişilik olmalıdır.

### Adım 7 — Metin: bağlam ipucu ve çözümleme ayarı (PRD 035)

Neden: T5. Yeni paket gerekmez.

- Toplantı konusu, katılımcı adları ve kiracıya ait terim sözlüğünden toplantı başına sınırlı bir ipucu listesi
  üretilir ve `hotwords` ile modele verilir. İpucu uydurma kelime ekletebilir; eklenen yanlış kelime oranı ayrıca
  ölçülür.
- Çözümleme ayarları tek tek ve eşlenmiş deneyle karşılaştırılır: sessizlikte uydurmayı azaltan seçenekler,
  konuşmacı aralıklarına hizalı kesitler (`clip_timestamps`), ışın genişliği, kurum GPU'sunda `float16`.
- Kelime–konuşmacı eşlemesi Adım 1'in toplantı düzeyi aralıklarıyla yeniden ölçülür (cpWER).

Kabul önerisi: sentetik Türkçe ve varsa 024 kümesinde kelime hatası ve cpWER taban çizgisine göre düşer;
ipucu kaynaklı yanlış ekleme raporlanır; `test` bir kez ölçülür.

### Adım 8 — Metin: model karşılaştırması (PRD 036)

Mevcut large-v3 ile Türkçe için ince ayarlanmış açık adaylar ve daha hızlı sürümler aynı kümede karşılaştırılır.
Yayımlanan sayılar çoğunlukla geliştiricinin kendi beyanıdır ve okunmuş konuşmaya aittir; karar yalnız kendi
ölçümümüzle verilir. Kazanan olursa lisans kaydı, sabit sürüm, paket özeti ve bağımlılık kabulü tamamlanır.

Dil modeliyle toplu son düzeltme (012/013 altyapısı, 018 uç noktası) burada ayrı bir seçenek olarak ölçülür:
yalnız öneri üretir, kaynak metin değişmez, yanlış düzeltme oranı raporlanır.

### Adım 9 — Model yükseltme adayları

Yalnız Adım 1–8'den sonra hedefler tutmuyorsa. Her aday yeni sürümlü bir vektör topluluğu, lisans incelemesi ve
bağımlılık kabulü demektir (46 numaralı kural).

- Konuşmacı ayırma: bağımsız karşılaştırmalarda çok konuşmacılı toplantılarda en iyi açık model DiariZen'dir,
  ancak yayımlanan ağırlıkları CC BY-NC 4.0 (ticari olmayan) lisanslıdır; ayrı lisans alınmadan veya izinli veriyle
  yeniden eğitilmeden kurum kullanımına aday değildir. Dört konuşmacıyla sınırlı modeller bu hedefe uymaz.
  Bugünkü modelin sonraki açık sürümleri aynı ölçümle izlenir.
- Ses izi: `docs/MODEL_RESEARCH.md`'deki daha güçlü adaylar ve skor normalizasyonu.

### Adım 10 — Kurum platformu ve verimlilik analizi

018 platform ekibinin cevaplarını, 023 kullanıcı kabulünü ve etiketli toplantıları bekler. Kurum GPU'sunda
modelleri parça aralarında bellekten indirmemek ve toplu yazıya çevirme hız kazandırır; doğruluk işi değildir.

## 5. Uygulayıcı için çalışma kuralları

1. Sıra: PRD taslağı → kullanıcı kabulü (`Status: Accepted`) → `plan.md` ve `tasks.md` → kırmızı test → kod →
   tam kalite kapısı → canlı geçiş → yol haritası satırı. Kabulsüz kod yazılmaz.
2. Kapı: `scripts/quality-gate.sh all`. Çıkış kodu ve `KT_GATE` satırları okunmadan "geçti" denmez.
3. Ölçüm: ayar yalnız `dev` kümelerinde yapılır; `test` her PRD'de bir kez ölçülür. Sonuçlar `results.md`'ye
   deney günlüğü aracıyla eklenir. Özel ses, metin ve kişi adı depoya girmez; yalnız toplu sayılar girer.
4. Yanlış kişi 0 hedefi hiçbir adımda eşik gevşetilerek veya otomatik kayıt açılarak aşılmaz; insan onayı kullanılır.
5. Yeni paket veya model: bağımlılık kabul kaydı, yayın tarihi kanıtı, lisans; çalışma anında indirme yok.
6. Git: dalda commit serbesttir; push ve birleştirme yalnız kullanıcı isteyince. Depo geçmişi yeniden yazılmaz.
7. Depo metinlerinde kurum adı geçmez; sır ve parola yazdırılmaz.
8. İşler kısa tutulur; uzun ölçümler arka planda koşar; rapor Türkçe ve sabit koşum raporu biçimindedir.
9. Bu geliştirme makinesinde: Docker sanal makinesi 7,35 GB'tır, ikinci bir büyük model sığmaz; çıkarım kodu
   imaja gömülüdür, değişiklikten sonra `sh scripts/stack.sh build inference` gerekir; ön yüz konteyneri
   düzenlemeleri görmez, tarayıcı denemesinden önce yeniden başlatılır; AAC çözmek için tarayıcı senaryoları
   kurulu bir tarayıcı kanalı ister.

## 6. Açık sorular

Open Question 1: Kurumun Teams ortamında toplantı dökümü açık mı ve Türkçe üretiyor mu? Açıksa `.vtt` dosyası
kişi adlarını hesap kimliğinden verir; bu, kişi adlandırma ve ölçüm etiketi için ayrı bir adım olur.

Open Question 2: Teams katılımcı raporu indirilebiliyor mu? Bir örnek dosya (adlar gizlenmiş) gerekir.

Open Question 3: Ölçüm için 3–5 gerçek Teams kaydı ve katılımcıların izni sağlanabilir mi? Biri 12–15 kişilik
olmalıdır.

Open Question 4: Etiketlemeyi kim yapacak (024 Open Question 2)?

Open Question 5: Aynı odadan tek cihazla katılım ne sıklıkta? Sık ise oda içi çok kişili ses ayrı ölçülmelidir.

## 7. Bu çalışmada bakılan diğer bulgular

- Depo GitHub'da herkese açıktır; `docs/GIT_WORKFLOW.md` özel olduğunu yazar.
- Otomatik testler yalnız çekme isteğinde çalışır; doğrudan `main` gönderimlerinde çalışmaz.
- Kapatılan altı bağımlılık güncelleme isteği `main`'e alınmadı; bağımlılık güncelliği kuralı açısından izlenmeli.
- `MeetingAudioReview.test.tsx` tam kapıda bir kez rastgele düştü; `tests/test_spark_startup.py` bu makinede
  PowerShell betik yasağı nedeniyle düşüyor.
- `04-meeting-upload.mjs` metni düzeltildi ama yeniden koşulmadı.

## Ek A — 17 Kasım 2026 ölçümü: tek geçiş ve parçalı akış

Soru: aynı ayırma modeli tüm kaydı tek geçişte işlerse ürünün parçalı akışına göre ne kazanılır?

Yöntem:

- Model `pyannote/speaker-diarization-community-1` @ `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`, `pyannote-audio`
  4.0.7, GTX 1080 Ti, `x86_64-cu126` imajı; çıkarım konteynerinde ayrı bir süreç.
- Tek geçiş: tüm kayıt tek çağrıda, modelin kendi ayarıyla (eşik 0,6 · `Fa` 0,07 · `Fb` 0,8). Kişi sayısı verilmedi.
- Taban çizgisi: ürünün aynı toplantılardaki kayıtlı sonuçları (`eval-ami4-array1-r2`, `eval-ami3-headset-r1`).
- Puanlama iki tarafta aynıdır: `scripts/run-ami-evaluation.py` içindeki `der_components`, aynı referans ve
  puanlama aralığı, örtüşen konuşma dahil.
- Küme: AMI `test`, 16 toplantı, koşul başına 9,06 saat.
- Sınır: bu, modelin tek başına ölçümüdür. Ürün akışı (yükleme, API, kelime eşleme, hafıza) çalıştırılmadı.
  Betikler geçiciydi ve depoda değildir; Adım 1 kalıcı ölçüm betiğini ekler.

| Koşul | Akış | DER | Kaçırılan | Yanlış alarm | Karışma | DER (±0,25 sn) | Kişi sayısı tam doğru |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Uzak mikrofon | Parçalı (bugün) | %27,56 | 11,00 | 4,31 | 12,25 | %19,96 | — |
| Uzak mikrofon | Tek geçiş | %19,90 | 11,16 | 3,81 | 4,93 | %13,21 | 12/16 |
| Yakın mikrofon | Parçalı (bugün) | %22,43 | 9,40 | 3,99 | 9,04 | %15,38 | — |
| Yakın mikrofon | Tek geçiş | %17,05 | 9,52 | 3,58 | 3,95 | %10,76 | 12/16 |

- Tek geçiş iki koşulda da 16 toplantının 16'sında daha iyidir. Kaçırılan konuşma ve yanlış alarm değişmez;
  kazanım konuşmacı karışmasındadır.
- Dört kişilik toplantılarda bulunan kişi sayıları 2 ile 6 arasındadır; 16 toplantının 4'ünde sayı sapar.
- Tarif kapsamla birlikte değişmelidir: servisin bugünkü tarifi (`Fa` 0,15) tek geçişte denendiğinde dört kişilik
  bir toplantıda (IS1009a, uzak mikrofon) 14 konuşmacı ve %28,97 DER verdi; modelin kendi ayarı aynı kayıtta
  4 konuşmacı ve %21,78 verdi (parçalı akış %29,74).

Gerçek Türkçe toplantılar (etiket yok, yalnız kişi sayısı):

| Kayıt | Gerçek konuşmacı | Ürün (parçalı) | Tek geçiş | Tek geçiş süresi |
| --- | --- | --- | --- | --- |
| 36 dakika | 11 (ve arka planda bir iki kısa ses) | 15 | 11 | 47 sn |
| 84 dakika | 4 | 7 | 4 | 111 sn |

`max_speakers` ipucu (13 ve 4) bu iki kayıtta sonucu değiştirmedi.

Maliyet: ses dakikası başına 1,29 saniye; GPU belleği en çok 1,6 GiB. Ayrı süreçte, model yükü dahil en yüksek
bellek 36 dakikalık kayıtta 3,8 GiB (44,1 kHz çift kanal girdi), 84 dakikalık kayıtta 5,0 GiB oldu.
