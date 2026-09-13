# Kullanılabilirlik ve doğruluk ilerleme planı

Tarih: 2026-09-13. Kullanıcının mevcut düzeyi değerlendirme, kapsamlı plan
oluşturma ve uygulamaya geçme talimatıyla hazırlanmıştır.
Profil: `kt-vibecoding-python-web-v2`; FastAPI/Python, React/Vite ve
PostgreSQL/SQLAlchemy/Alembic korunur. Bu dosya önceliklendirme ve kanıt
haritasıdır; iş gereksinimlerinin otoritesi bağlantılı Accepted PRD'lerdir.

## Şu anki düzey

Ürün **insan denetimiyle kullanılabilecek yerel pilot** düzeyindedir. Temiz
kayıtlarda yükleme → konuşmacılı metin → kalıcı kişi → sonraki kayıtta tanıma
akışı çalışıyor. Tek bir "kullanılabilirlik yüzdesi" vermek, metin, kimlik,
kurulum ve hata kurtarmayı yanlış biçimde birleştirir. Otomatik çıkarılmış
metin ve kişi ataması kontrol edilmeden kesin toplantı tutanağı sayılmaz.

| Alan | Gözlenen durum | Kullanım sonucu |
| --- | --- | --- |
| Türkçe okunmuş konuşma | FLEURS 743 klip, 12.914 kelime; kelime hata oranı (WER) %6,50 | Bu dar koşulda metin taslağı yararlı; test metadata'sı yalnız erkek etiketli, kişi kimliği yok |
| Türkçe haber konuşması | MediaSpeech 2.433 yeni klip, 71.767 kelime; WER %14,12 | Sayı, yazım ve kayıt sınırları daha fazla denetim gerektiriyor |
| Doğal Türkçe görüşme | Aynı altı kişinin iki yeni zinciri: her birinde 6 yeni/6 dönüş doğru; kimlik F1 %100 | Küçük grubun bu kayıtlarında hafıza çalışıyor; otomatik etkinlik/zayıf metin referansı, bilinen iki konuşmacı girdisi var |
| Görüşmenin metni | İki zincirde konuşmacı etiket eşlemesi sonrası WER (cpWER) %29,96 / %30,44 | Hafızanın doğru olması metnin doğru olması değildir; kaynakla inceleme gerekli |
| Kontrollü 50 kişilik eşleme | 11 Eylül denetimli klip galerisinde 49/50 profil, 95/100 doğru bilinen sorgu; ayrıca 40 yabancı sorguda yanlış kabul yok; precision %100, recall %95, F1 %97,44 | Temel eşleme umut verici; otomatik toplantı ayrımı ve kalıcı ilk kayıt bu ölçümde yok |
| Tam 50 kişilik zincir | Aynı tarihteki A: 37/50 ilk profil; B/C: baskın kaynakla 35/50 doğru dönüş | İlk profil ve konuşmacı gruplama hâlâ önemli açıklar; katı kaynak saflığında dönüşler 27/50 ve 28/50 |
| İşletim | Parçalı yükleme, kalıcı iş/checkpoint, retry ve küçük gerçek yeniden başlatma akışı var | Çok uzun kayıt ve eşzamanlı kullanım için ayrı kaynak/cihaz kabulü gerekiyor |
| Cihaz ve yayın | Yerel RTX 4060 toplantı akışı doğrulanmış; native Spark/Apple toplantı ve bağımsız güvenlik kabulü eksik | Bu ortamların kurulum/çalışma başarısı ayrı gözlenmeli |

Kaynaklar: [geniş Türkçe deneyler](../docs/evidence/2026-09-13-expanded-turkish/README.md),
[kontrollü 50 kişi](../docs/evidence/2026-09-11-accuracy-audit/nested-gallery-report.md),
[tam zincir](../docs/evidence/2026-09-11-accuracy-audit/README.md).
11 Eylül sonuçları dondurulmuş kaynak/imajın ölçümüdür; bugünkü ağacın yeniden
koşumu diye sunulmaz. Kontrollü ve tam zincir veri koşulları farklıdır;
aradaki fark tek başına bir bileşenin nedensel hata payını belirlemez.

## Uygulama sırası ve sahiplik

| Öncelik | İş / gerekçe | Yetkili kapsam | Çıkış kanıtı |
| --- | --- | --- | --- |
| 1 — şimdi | Türkçe parça sınırında çift yazmayı düzelt: `IŞIK YENİ` / `ışık yeni` aynı kaynakta dört kelimeye dönüşebiliyor | [002 Decision 25 / T24](../specs/speaker-identity/PRDs/002-long-recording-analysis/tasks.md) | Kırmızı/yeşil domain ve gerçek PostgreSQL testi; gerçek tekrarların, eski checkpoint'in ve özgün metnin korunması |
| 1 — şimdi | Transkript satırından sınırlı kaynak sesi dinlet; uzun dosyada kullanıcı kararını denetlenebilir kıl | [011 Accepted](../specs/speaker-identity/PRDs/011-meeting-audio-review/PRD.md) | Yetkili 30 saniyelik ses API'si, tek aktif oynatıcı, TR/EN, iptal/temizlik ve gerçek tarayıcı |
| 2 | İnsan denetimli Türkçe referans ve kişi/oturum açısından ayrılmış kalibrasyon/test oluştur | [001](../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md), [002 kalite kabulü](../specs/speaker-identity/PRDs/002-long-recording-analysis/PRD.md), [veri kiti](../docs/DATA_COLLECTION.md) | Doğru kişi, zaman, metin, örtüşme ve kaynak kimliği; ikinci dinleyiciyle anlaşmazlık çözümü |
| 3 | Konuşmacı ayrımı, kısa dönüşler ve ilk profil kabulünü ayrı teşhis ederek adayları karşılaştır | Aynı 001/002 kalite işi; [deney planı](../docs/EVALUATION_PLAN.md) | Tek bileşen değişen eşlenmiş deney; bütün başarısız kayıtlar paydada; temiz/karışık güvenlik kontrolleri korunmuş |
| 4 | Denetimli metin/kişi düzeltme, geri alma ve düzenleme geçmişi tasarımını netleştir | Ön karar çalışması; yeni Accepted düzeltme PRD'si gerekir | Ad değiştirme ile kimlik düzeltme ayrılmış; model çıktısı değişmez, insan düzeltmesi ayrı audit/sürümle izlenir |
| 5 | Uzun kayıt, kesinti, paralel iş, soğuk başlatma ve cihaz kurulumlarını doğrula | [002](../specs/speaker-identity/PRDs/002-long-recording-analysis/tasks.md), [004 Spark](../specs/speaker-identity/PRDs/004-spark-remote-inference/tasks.md), [005 CPU](../specs/speaker-identity/PRDs/005-local-cpu-runtime/tasks.md), [007 mikrofon](../specs/speaker-identity/PRDs/007-microphone-meeting-capture/tasks.md) | 1/2/4 saat kayıtta bellek/disk/iş süreleri; kesintiden devamda kelime/profil kaybı yok; cihaz başına gerçek rapor |
| 6 | Yayın güvenliği ve kullanıcı kabulünü kapat | Mevcut PRD'lerin güvenlik/L3 maddeleri | Onaylı çevrimdışı tarayıcı araçlarıyla güvenlik kapısı; normal rol/tenant, dev giriş ayarları ve gerçek kullanıcı denemesi |

İlk iki iş bu talimatla uygulanır; diğer mevcut Accepted kalite/cihaz hedefleri
tamamlanmış veya iptal edilmiş sayılmaz. İnsan düzeltme tasarımı henüz bir
silme/birleştirme operasyonunu yetkilendirmez. Teams'ten otomatik ses alma ve
canlı metin, kullanıcının mevcut dosya yükleme kararıyla [003](../specs/speaker-identity/PRDs/003-live-speaker-analysis/PRD.md)
altında ayrı kalır; bu plan önceliklerini onların kurulumuna bağlamaz.

## Veriyi daha yararlı hale getirme

Mevcut 3.256 Türkçe kısa klip ve görüşme pencereleri sürüm/hash ile korunur.
İncelenmiş test sonuçlarına göre ayar seçilen kayıtlar yeni bir "kör test"
diye adlandırılmaz. Aynı kaydı yüz parçaya bölmek kişi/oturum desteğini artırmaz.

1. Önce mevcut doğal görüşmelerin seçimi modelden bağımsız sabitlenen küçük
   bölümünde insan denetimli metin ve zaman referansı oluştur. Zayıf referanslı
   cpWER ile gerçek kelime kaybını ayır; iki dinleyici anlaşmazlıkları çözsün.
2. Sayı/yazım hatalarının ayrı açıklama alanı olsun; mevcut `turkish-words-v1`
   puanı korunur. Yeni yazım kuralı gerekiyorsa yeni sürüm ve eşlenmiş raporla
   yayımlanır; yanlış sözcükler daha yüksek skor için silinmez.
3. 50 kayıtlı + 20 farklı bilinmeyen Türkçe kişi için en az üç ayrı oturum,
   mümkünse iki mikrofon planını uygula. Önce veri kitinin küçük 5+2 kişilik
   sürümünde etiket ve iş akışını doğrula; sonra kapsamı aynı protokolle büyüt.
4. Kayıt için 30–60 saniye temiz konuşma; sorgularda 1–2, 3–5 ve 10+ saniye
   ayrı gruplar. Toplantıda parçalı temiz toplamın 20 saniyeyi aşması ilk profil
   için süre şartıdır; daha kısa bilinen kişi dönüşü ayrı değerlendirilir.
5. Galeri 5/10/20/50 ile tek toplantıda konuşan 2/5/10/20 kişiyi ayrı eksenler
   olarak ölç. 50 kişinin bir toplantıda bulunması ayrıca stres testi;
   100/200 galeri ek ölçek, uygulama kotası değildir.
6. Gerçek codec/mikrofon/oda değişimini gerçek oturumdan al. Gürültü ekleme,
   hız değişimi ve birleştirilmiş ses yalnız türetilmiş stres deneyi olarak
   etiketlenir; bağımsız insan ve doğal toplantı yerine sayılmaz.

Gerekli insan etiketleri ve izinli farklı oturum kayıtları mevcut açık
paketlerde tam karşılanmıyor. [Ek kaynak taraması](TURKISH_SPEAKER_MEMORY_SOURCES_ADDENDUM.md)
erişim/lisans/kişi etiketi sınırlarını gösterir. Yeni kişi kaynağı edinmek veya
satın almak, mevcut dosya hazırlama aracını çalıştırmakla tamamlanmış sayılmaz.

## Model değişikliğini nasıl seçeceğiz

Önce aynı ses ve doğru kişi sınırlarıyla kimlik motorunu; sonra gerçek
konuşmacı ayrımıyla uçtan uca akışı; en son sıralı yeni kişi/geri dönüş
hafızasını ölç. İlk kayıt, yanlış kişi kabulü, çekimserlik ve bozuk küme ayrı
sayılır. Tek başına precision veya işin `succeeded` olması geçiş ölçütü değildir.

Mevcut ECAPA192/Community256 eşleme korumaları, 85 temiz/karışık kontrol,
en az %99 kaynak saflığı ve bilinen profil örneklerinin değişmezliği korunur.
Eşiği düşürerek kayıt kapsamı artırmak, yanlış kişinin hafızaya girmesini
artırıyorsa aday reddedilir. Üst sayı bilgisi her parçaya zorlanmaz; iki sesi
yalnız kişi sayısını tutturmak için birleştirmeyiz.

Konuşmacı etiketlerini transkripte bağlamak için Community-1'in exclusive
çıktısı zaten kullanılmaktadır; bunu yeni bir iyileştirme diye tekrar
uygulamak gerekmez. [Birincil model kartı](https://huggingface.co/pyannote/speaker-diarization-community-1)
bu çıktıyı ve bilinen kişi sayısı seçeneğini açıklar. Whisper'ın bağlam, sessizlik
ve kelime zamanı seçenekleri [birincil kaynakta](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
mevcuttur; bunların bulunması Türkçe verimizde fayda sağladıkları anlamına gelmez.
Önceki gerçek VAD karşılaştırması yeni bir aç/kapat kararını desteklememiştir.

Yeni ASR/embedding modeli ancak sabit yerel paket, lisans, bağımlılık kabulü,
4060 uyumu ve ayrı kalibrasyon verisiyle aday olur. Her denemede yalnız bir
anlamlı değişken değişir; daha iyi metin yanında sessizlikte uydurulan söz,
kişi karışması, gecikme ve bellek de değerlendirilir. Büyük model veya daha
fazla bellek tek başına kalite garantisi değildir. İyi görünen aday, ayar
seçiminde kullanılmamış ayrı oturum testinden geçmeden varsayılan yapılmaz.

## Başarı kapıları

| Kapı | Kabul biçimi |
| --- | --- |
| İncelenebilir pilot | Doğru kaynak zamanı dinlenir; yanlış/eksik atama görülebilir; kaynak ömrü, tenant ve normal rol korunur; eski metin/hafıza değişmez |
| 50 kişilik kimlik | Mevcut mühendislik hedefi: 3+ saniye temiz farklı oturum sorgusunda bilinmeyen yanlış kabul oranı (FPIR) ≤%1 iken bilinen doğru tanıma ≥%95; ilk profil ve başarısız sorgular ayrıca paydada |
| Daha sıkı yanlış kabul | Aynı planın sonraki ≤%0,1 FPIR çalışma noktası ayrı test edilir; yeterli bağımsız bilinmeyen destek ve belirsizlik aralığı olmadan üretim garantisi yok |
| Türkçe toplantı metni | Önce insan denetimli doğal toplantı başlangıç ölçümü; sonra aynı referansta kelime/kişi hatası ve düzenleme yükünde azalma, isim/sayı/sessizlik alt gruplarında gerileme yok |
| Hafıza korunumu | Yanlış/karışık örnek kabulü, tekrar profil ve bilinen örnek değişimi ayrıca sayılır; mevcut saflık ve negatif kontrol regresyonları sıfır |
| Uzun kayıt / cihaz | Planlı 1/2/4 saat ve kesinti koşulları gerçek cihazda tamamlanır; gözlenmeyen cihaz başarılı sayılmaz |
| Yayın | Tam profil kapısı ve bağımsız güvenlik taraması; gerçek kullanıcı L3 kabulü; eksik araç veya temsilî veriyle "hazır" işareti verilmez |

Kimlik hedefleri [mevcut değerlendirme planından](../docs/EVALUATION_PLAN.md)
alınmıştır; eşik yapılandırması değildir. Doğal Türkçe için henüz güvenilir
bir DER/cpWER kabul yüzdesi ölçülmeden uydurulmaz. Kullanıcı eforu da ölçülür:
yanlış atamayı bulma, ilgili sesi açma, bir tutanağı denetleme ve düzeltme süresi.
Bu efor için başlangıç ölçümü yoktur; uygulanan inceleme akışıyla ölçülebilir hale gelir.

## Her değişiklikte kanıt

Önce davranışın kırmızı testi, sonra düzeltme ve dar regresyonlar; ardından
gerçek veri/dosya/HTTP veya tarayıcı sınırı. Model deneyi varsa
`results.md` aynı kaynak/ayar/protokol ve paydalarla güncellenir; UI veya
salt yazılım testi yeni model doğruluğu deneyi diye eklenmez.
Tam profil kapısı ve güvenlik kapısı gerçek çıkışlarıyla raporlanır.
Ham ses, kimlik ve hesap bilgileri yerel/Git dışı kalır. Commit/push ayrıca
istenmedikçe bu çalışma version-control yayın işlemi başlatmaz.

İlk iki iş uygulandı: Türkçe sınır düzeltmesi 62 dar test ve 28 korunmuş sınır
karşılaştırmasında doğrulandı; kaynak dinleme gerçek dosya, HTTP ve TR/EN
tarayıcıyla çalıştı. Tam kapı 687 arka uç + 158 ön yüz = 845 testi geçti.
İki normal hesapta 12 toplantının 36 ses bölümü ve 12 tekrarı kaynakla
birebir aynı; mevcut profiller/metinler korundu. Yeni 300 saniyelik RTX
testi arayüzde iki konuşmacı ve oynatılabilir kaynak üretti.

Kanıtlar [iyileştirme raporlarında](../docs/evidence/2026-09-13-usability-improvement/README.md)
ve [011 görevlerinde](../specs/speaker-identity/PRDs/011-meeting-audio-review/tasks.md).
Güvenlik kapısı `gitleaks` yokluğunda çalışamadı; tarayıcı eklentisi dosya
seçimini reddettiği için bu canlı testin yüklemesi gerçek API ile yapıldı.
Fiziksel ses, headless senaryo, genel 50 kişi ve cihaz hedefleri açık.
Sıradaki doğruluk işi insan denetimli Türkçe referans ve ayrı oturum
kalibrasyonudur; mevcut tarihsel puanlar yeni sürümün ölçümü diye değişmedi.
