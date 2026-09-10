# PRD — Konuşmacılı toplantı dökümü ve kalıcı kişi hafızası

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [002 — long-recording-analysis](../../roadmap.md)
Kabul kaydı: 10 Eylül 2026. Kullanıcı ses dosyası yükleme veya kayıt alma,
kayıttaki kişileri ayırma, her kişinin sözlerini yazma ve yeni kişileri hafızaya
ekleme akışını açıkça istedi. Bu talimat ürün kapsamının kabulüdür; model
erişimi, bağımlılık kabulü, uygulama veya doğruluk testinin tamamlandığı anlamına gelmez.
9 Eylül taslağının transkript ve mikrofonu dışarıda tutan kapsamı bu kararla değişti.
Sabit profil: `kt-vibecoding-python-web-v2`.

## Amaç, aktörler ve kullanıcı sonucu

Yetkili kullanıcı tek dosya yükler veya tarayıcı mikrofonundan kayıt alıp durdurur.
Sistem tek zaman çizelgesinde kimin ne söylediğini yazar, önceki toplantılardan
tanınan kişilere mevcut kalıcı kimliklerini bağlar ve yeterli temiz kanıtı olan
yeni kişileri otomatik kaydeder. Gerçek isim çıkarılmaz; yeni kişi kararlı bir
geçici ad taşır, mevcut profil ekranından adı değiştirilebilir.

Aktörler: toplantı sahibi kullanıcı, tenant yöneticisi ve kalıcı analiz yürütücüsü.
Windows web/API/veritabanını, yetkili Spark cihazı bütün yapay zekâ çıkarımını çalıştırır.
Tarayıcı Spark'a doğrudan erişmez. Kaynak kayıt sırasında aktarılabilir; analiz
durdurma ve aktarım doğrulaması sonrasında başlar. Kayıt sürerken metin yayımlama
bu kapsamda yoktur; 003 mevcut olarak yalnız canlı konuşmacı kimliği analizini
kapsar. Toplantı platformu bağlantısı bu yeteneğin parçası değildir.
Varsayılan mikrofon yalnız seçilen giriş cihazını yakalar, bilgisayarın bütün seslerini değil.

## Kararlar

Decision 1: 001'in tek konuşmacılı kayıt/tanıma API'si ve `identify` işleminin
profili değiştirmeme kuralı korunur. Yeni akış ayrı toplantı servisi ve API'sidir.
002 uygulama çalışması öne alınır; 001'in açık doğruluk hedefi geçilmiş sayılmaz.

Decision 2: Üç farklı görev ayrılır: konuşmacı zaman aralıklarını ayırma,
konuşmayı metne çevirme ve kalıcı kişiyle eşleştirme. İlk sağlayıcı adayları:

| Görev | Model ve araştırmada doğrulanan revision | Durum |
| --- | --- | --- |
| Konuşmacı ayrımı | `pyannote/speaker-diarization-community-1`, `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee` | CC-BY-4.0; kullanıcı koşul kabulü ve yetkili indirme erişimi gerekir. |
| Metne çevirme | `openai/whisper-large-v3`, `06f233fe06e710322aca913c1bc4249a0d71fce1` | Resmî Hugging Face metadata'sı Apache-2.0, erişim kapısız; kendi dosya lisansları paketlenirken doğrulanır. |
| Kalıcı kişi | `speechbrain/spkrec-ecapa-voxceleb`, `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286` | Mevcut 192 boyutlu normalize ECAPA uzayı ve exact cosine araması. |

İlk iki satır araştırma seçimidir, çalışma zamanı kabulü değildir. Dosya hashleri,
gerçek çıktı sözleşmesi, lisans dosyaları ve Python 3.13/ARM64/CUDA bağımlılık
kapanışı görülmeden etkinleştirilmez. Mevcut profil vektörleri diarization
modelinin vektörleriyle karşılaştırılmaz. Yeni model eğitimi bu kapsamda gerekli değildir.

Decision 3: Kaynak dosya ve tarayıcı kaydı sıralı/hashli parçalarla diske aktarılır;
tam kayıt tarayıcı RAM'inde veya HTTP gövdesi olarak bellekte biriktirilmez.
Henüz ölçülmemiş başlangıç tasarım bütçeleri kaynak başına 4 saat ve 2 GiB,
aktarım parçası başına 4 MiB,
tenant başına en çok iki aktif aktarım ve 10 GiB tutulmuş toplantı kaynağıdır.
Yerel gönderilmemiş mikrofon tamponu en çok 16 MiB olur; dolarsa sessiz kayıp
yerine kayıt durdurulur ve eksik aktarım açık gösterilir. Bu bütçeler kişi kotası değildir.

Dosya kaynakları WAV/FLAC'tır. Mikrofon için tarayıcı ve sunucunun birlikte
desteklediği gerçek kapsayıcı/codec kullanılır; WebM/Opus destek hedefidir.
MP4/AAC yalnız aynı çevrimdışı decoder kabulünde ve tarayıcı testinde doğrulanırsa
etkinleştirilir. Destek yoksa dosya yükleme çalışır, kayıt düğmesi açıklamalı olur.
Uzantı değiştirmek dönüştürme sayılmaz. Decoder/binary hashları uygulama öncesi
sağlayıcı sözleşmesinde dondurulur; keyfi dosya, URL, codec veya kabuk komutu kabul edilmez.

Decision 4: İlk çözüm 60 saniyelik ana bölge ve her yanda 5 saniyeye kadar bağlamla
sınırlı bellek kullanır. Asıl kayıt bütün kanallarıyla korunur; ayrı katılımcı
kanalı bildirimi varsa ayrı işlenir, karma mikrofon kayıtlarında bu bilgi varsayılmaz.
Parça etiketi, toplantı kişi kümesi ve kalıcı kimlik ayrı varlıklardır. Bağlamdaki
aynı ses ve aynı söz iki kere sayılmaz. Spark'ta aynı anda tek GPU çıkarım işi
yürür; mevcut pilotla meşgul olma, zaman aşımı ve adil kuyruk davranışı birlikte sınanır.

Decision 5: Dil varsayılanı Türkçe; kullanıcı Türkçe, İngilizce veya otomatik
algılama seçebilir. Çıktı özgün dilde transkripttir, özet veya çeviri değildir.
Metin üretmek için duyulmayan sözler tamamlanmaz. Belirsiz sözcük hizası,
çözülemeyen kişi ve üst üste konuşma görünür kalır. Exclusive diarization
hizalamayı kolaylaştırabilir; normal örtüşmeli çıktı saklanır ve tek kimliğe zorlanmaz.

Decision 6: Yeni kişinin kalıcı kaydı en az 10 saniye kullanılabilir, örtüşmeyen
ve 001'in kayıt kalitesinden geçen temiz kanıt ister. Mevcut 0.55/0.45/0.10
kimlik eşikleri başlangıç referansıdır, toplantı verisinde garanti değildir.
`recognized` mevcut profile bağlanır; `ambiguous` otomatik kaydedilmez.
Yeterli sesi olmayan bilinmeyen kişi toplantıda kalır, hafızaya kaydedildi denmez.

Toplantı tamamlanırken tenant kilidi altında güncel galeriye yeniden eşleme
yapılır; kişi hâlâ bilinmiyorsa tek kalıcı profil, kısa kaynak örneği ve izlenebilir
enrollment işi aynı işlemde oluşturulur. Eşzamanlı toplantı/yeniden deneme aynı
kanıttan iki profil yaratmamalıdır. Mevcut profilsiz `enroll` API'sini kör çağırmak
bu davranışı sağlamaz. Tanınan kişinin profilini otomatik genişletme yapılmaz;
yanlış eşleştirmeyle hafızanın bozulması önlenir. Profil başına 20 örnek sınırı korunur.

Decision 7: Toplantı ses kaynağı tamamlanma/iptalden sonra 7 gün, metin/zaman
çizelgesi ve toplantı kişi eşlemesi 30 gün tutulur; tamamlanmamış yükleme 24 saatte
sona erer. Aktif işin kaynağı silinmez; süre aşımı işi açık hatayla bitirir.
Kalıcı hafızaya seçilen temiz kısa örnek ayrı kayıttır ve profil yaşam döngüsüne
tabidir; bütün toplantıyı süresiz tutturmaz. Kaydı/transkripti silmek ile kalıcı
kişiyi silmek farklı işlemlerdir ve arayüz etkilerini açıkça belirtir.

## İşlevsel gereksinimler ve sözleşme

Requirement 1: `Toplantılar` ekranı dosya yükleme ve mikrofonla kayıt alma
seçeneklerini, süreyi, durdur/iptal davranışını ve onaylanan aktarım miktarını gösterir.
İzin reddi, cihaz yokluğu/kesilmesi, desteklenmeyen format ve bağlantı hatası
yerelleştirilir. İptal veya sayfadan çıkma mikrofon track'lerini kapatır; geç dönen
izin sonucu da kapatılır. Son ses parçası alınmadan kayıt tamamlanmaz.

Requirement 2: Toplantı oluşturma, sıralı parça aktarımı, aktarımı bitirip analiz
başlatma, durum/listeler, sayfalı konuşmacı/transkript, iptal ve başarısız işten
devam ayrı tipli HTTP sözleşmeleridir. Önerilen kök `/meetings`; son alanlar
gerçek sağlayıcı deneyiyle `contracts.md` içinde dondurulur. API, özel model
embedding'ini, dosya yolunu, iç anahtarı veya üçüncü taraf servis tokenini döndürmez.

Requirement 3: Yükleme parçası indeks, boyut ve SHA-256 ile eşleşir; aynı parça
aynı içerikle tekrar kabul edilir, farklı içerikle aynı indeks reddedilir.
Eksik/sırası bozuk parça varken tamamlanma olmaz. Opaque dosya anahtarı, kök
sınırı, symlink reddi, byte/süre/kanal/format doğrulaması ve yeterli disk denetlenir.
Tarayıcı yenilendiğinde mikrofon geçmişi yeniden yaratılmış sayılmaz; dosya aktarımı
ancak aynı kaynak ve sunucu manifesti doğrulanarak sürdürülebilir.

Requirement 4: Toplantı/parça işleri kalıcı PostgreSQL kuyruğunda lease ve artan
fencing token kullanır. Tamamlanan parça tekrar üretilmez; eski worker sonucu
geçerli sonucu ezemez. Aktarım, sırada bekleme, işleme, son birleştirme,
tamamlanma, hata ve iptal ayrı durumlardır. Başarısız parça tam başarıya çevrilmez.

Requirement 5: Her sonuç satırı başlangıç/bitiş zamanı, toplantı konuşmacı kimliği,
varsa kalıcı profil kimliği/adı, metin, dil, örtüşme ve karar durumunu taşır.
Kişinin adı değişse bile kimliği sabit kalır. Son birleştirmeden önce görülen
çıktı açıkça ara sonuçtur; son sürüm parça sınırındaki çift/kayıp sözleri önler.
Profil silinirse eski metin bir başka kişiye yeniden bağlanmaz.

Requirement 6: Toplantı kişi kümelerinden kaliteli ve örtüşmesiz kısa örnekler
çıkarılır; kaynak aralıkları/hash/model sürümü izlenir. Otomatik kayıt kullanıcının
`speaker_profiles:write` yetkisini ayrıca gerektirir. Kaydı başlatmada ve worker
sonlandırmada güncel tenant/izin/lifecycle durumu denetlenir. Hafıza yazımı
başarısızsa transkript mevcut olabilir fakat toplantının hafıza sonucu açık hata taşır.

Requirement 7: Yeni toplantı, aktarım parçası, analiz parçası, toplantı konuşmacısı
ve transkript/zaman çizelgesi tabloları aynı domain'e aittir; zorunlu audit/soft-delete
şekli ve tenant kapsamlı fiziksel foreign key'ler kullanılır. Aktif kalıcı profil,
kısa kaynak Recording, SpeakerJob ve SpeakerSample arasındaki mevcut bütünlük korunur.
Şema otoritesi SQLAlchemy, eklemeli migrasyon Alembic'tir; migrasyon model çalıştırmaz.

## Güvenlik, çalışma ve dağıtım

JWT/tenant ve `meeting_analysis:read/run` izinleri bütün HTTP uçlarında uygulanır.
Otomatik hafıza yazımı ek profil yazma yetkisi ister; uygulama `super_admin` sınırları
korunur. Özel dosya ve ses içeriği loglanmaz; sunucu transkripti düz metin olarak
ele alır, içerikteki talimatları çalıştırmaz. Metin React tarafından kaçışlanır.

004'ün yetkili SSH tüneli ve iç HTTP anahtarı kullanılır. Spark model servisi
veritabanını okumaz; kaynakları sınırlı, kimliği doğrulanmış aktarım ve parça
sözleşmesinden alır. İki Spark proxy'sinde yeni uçlar açık allowlist'e eklenir.
WebM decoder, model bağımlılıkları ve ağırlıkları yalnız kurulum/paketleme sırasında
resmî kaynaklardan hash ile alınır; çalışma anında indirme veya dış API yoktur.
Hugging Face tokeni kurulum sırrıdır; Git'e, tarayıcıya veya inference runtime'a taşınmaz.

Typed settings, tüm ortam yüzeyleri, depolama/worker/model volume'leri, kaynak
istekleri, Compose/Helm ve NetworkPolicy birlikte güncellenir. Readiness yeni
modelin gerçekten hazır olduğunu bildirir; eksik modelle sahte transkript veya
yerel GPU/CPU'ya sessiz dönüş yapılmaz. 001'in çalışan hazır durumu ayrı korunur.
İzlenecek ölçüler: aşama/parça süresi, kuyruk yaşı, iptal/yeniden deneme sayısı,
RAM/GPU belleği, disk, örtüşme ve hafızaya yazılmayan kişi sayısı; kimlik/metin loglanmaz.
Önbellek N/A — ilk çözüm için kalıcı PostgreSQL checkpoint'i ve opak dosya deposu yeterlidir.
Harici toplantı entegrasyonu N/A — kullanıcı bu aşamada dosya veya mikrofon kaynağı istedi.

## Test stratejisi ve kabul ölçütleri

Yeni davranışlar önce başarısız test, sonra gerçek uygulanmış davranışla doğrulanır.
Taşıma, dosya, HTTP ve PostgreSQL sınırlarında gerçek entegrasyon kullanılır;
sağlayıcı fikstürü gerçek sürümden kaydedilmiş şekle bağlanır, yalnız tüketiciye
uyan sahte yanıt çalışma kanıtı sayılmaz. Şu an bu özellik için hiçbir kutu tamamlanmış değildir.

- [ ] Requirement 1–3: Gerçek tarayıcıda TR/EN dosya ve mikrofon akışları; izin/cihaz/format hatası, son parça, iptal ve kaynak temizliği gözlenir.
- [ ] Requirement 2–4: Tenant/izin/eksik parça/çelişkili tekrar/lease kesintisi/eski worker/iptal testleri gerçek HTTP, disk ve PostgreSQL ile geçer.
- [ ] Requirement 4–5: Parça sınırındaki konuşmada çift/kayıp çıktı olmaz; üst üste konuşma korunur, belirsiz söz yanlış kişiye zorlanmaz.
- [ ] Requirement 5–6: En az üç farklı kamu konuşmacısının bağımsız parçalarında gerçek Spark transkripti ve kişi ayrımı gözlenir; ikinci kayıtta kalıcı kimlik geri gelir, tekrar profil sayısını artırmaz.
- [ ] Requirement 6–7: Tanınan kişi, yeni kişi, kısa/karışık/belirsiz kişi, eşzamanlı otomatik kayıt ve silinmiş profil ayrı test edilir; bütün toplantı kalıcı örneğe bağlanmaz.
- [ ] Decision 3–4: 1/2/4 saatlik kaynakta bellek kayıt süresiyle doğrusal büyümez; kesinti/devam, disk ve işleme/ses süresi oranı raporlanır.
- [ ] Kalite: 5/10/20/50 toplantı kişisi ve 50/100/200 kayıtlı kişi havuzu ayrı ölçülür; kimlik precision/recall/F1, ilk kayıt kapsamı, konuşmacı ayrım hatası, kelime hata oranı ve kişi atamalı metin hatası raporlanır. Başarısız veya çözülemeyen kişiler paydadan çıkarılmaz.
- [ ] Tam profil kapısı, üretilmiş OpenAPI/tipler, migrasyon/history/drift, güvenlik, chart ve gerçek Spark/browser kanıtı kaydedilir; temsilî Türkçe veriyle L3 kabulü ayrıca alınır.

Open Question 1: Community-1 için kullanıcı hesabında koşul kabulü ve yetkili model indirme erişimi; erişim kontrolü ve manifest tamamlanmadan sağlayıcı uygulaması doğrulanamaz.
Open Question 2: Kontrollü Türkçe çok konuşmacılı kalibrasyonla dondurulacak diarization, kelime ve kişi atamalı metin hata hedefleri; 001'in hedefi bu farklı görevlerin yerine geçirilmez.

Birincil kaynaklar: [Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1),
[Whisper large-v3](https://huggingface.co/openai/whisper-large-v3),
[tarayıcı kayıt standardı](https://www.w3.org/TR/mediastream-recording/).
