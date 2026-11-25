# PRD — Toplantı sürerken canlı ara sonuç

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [003 — live-speaker-analysis](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kabul: 25 Kasım 2026, kullanıcı (037 ile birlikte; 037 tamamlandıktan sonra uygulanır). Uygulama planı: [plan](plan.md), [görevler](tasks.md).
Bağımlılık: [037](../037-two-channel-meeting-capture/PRD.md) iki kanallı Teams kaydı ve kesintisiz aktarım,
[030](../030-whole-recording-diarization/PRD.md) kesin konuşmacı ayırma.
Kaynak (25 Kasım 2026): Kullanıcı, Teams masaüstü toplantısında kayda başladığında mümkün olduğunca gerçek zamanlı sonuç
istedi. Bu sürüm, 9 Eylül tarihli taslağın yerini alır: ses kaynağı, teslim kuralları ve sonuç iletimi artık 037 ile
belirlidir; canlı metin de kapsama girer.

## Amaç

037 kaydı sürerken kullanıcı, konuşulanları birkaç saniye gecikmeyle ekranda görür:
- metin satırları;
- konuşmacı etiketi ("Konuşmacı n");
- kanal etiketi ("Bu bilgisayar" veya "Toplantı sesi");
- kişi hafızasında tanınan biri için "muhtemelen <Ad>" ön tahmini.

Bu sonuç geçicidir. "Bitir"den sonra 037'nin kesin işlemesi biter ve kesin sonuç geçici sonucun yerini alır. Kesin
sonuç canlı sonuçtan hiçbir girdi almaz.

## Kararlar

Decision 1: Canlı görünüm yalnız 037 iki kanallı kayıtlarında vardır. Dosya yükleme ve 007 mikrofon kaydı değişmez.
Canlı görünüm CPU modunda sunulmaz; ekranda nedeni gösterilir ve kayıt 037 olarak sürer.

Decision 2: Kayıt parça alırken worker, her kanalın yeni sesini yaklaşık 3 saniyede bir işler.
- Pencere, yeni sesi ve öncesindeki bağlamı kapsayan en çok 15 saniyedir.
- Yeni seste konuşma yoksa o kanal o turda atlanır.
- Çıkarım servisi pencerede konuşma bölütlerini ve yerel konuşmacı kümelerini bulur. Her küme için konuşmacı izleme
  vektörünü (030'daki 256 boyutlu vektör) döndürür.
- Yalnız kapanmış bölütleri yazıya çevirir. Bir bölüt, sessizlikle ya da en çok 10 saniyede kapanır.
- Açık bölüt bir sonraki tura kalır.

Bunun için yeni bir çıkarım uç noktası eklenir; bugünkü parça uç noktaları değişmez.

Decision 3: Yerel kümeler oturumun canlı konuşmacılarıyla izleme vektörlerinin kosinüs benzerliğiyle eşlenir.
- Başlangıç eşiği, 021 birleştirme eşiğidir (0,6). Eşik Requirement 6 ölçümüyle doğrulanır ve plana yazılır.
- Eşleşmeyen ve en az 2 saniye konuşması olan küme yeni canlı konuşmacı olur.
- Canlı konuşmacının vektörü kanıt süresine göre ağırlıklı ortalamayla güncellenir.
- İki canlı konuşmacının vektörleri sonradan eşiği geçerse birleştirilir. Satırlarının etiketi güncellenir ve sürüm
  numarası artar.

Canlı konuşmacılar `meeting_speaker` satırlarına ve kişi hafızasına hiçbir şey yazmaz.

Decision 4: Ön tahmin şöyle çalışır:
- Canlı konuşmacı 10 saniye temiz konuşmaya ulaşınca, konuşmacının kendi kanalındaki temiz sesinden ECAPA vektörü çıkarılır.
- Vektör kişi hafızasıyla bugünkü eşleme kuralıyla (`MatchPolicy`) ve katılımcı listesi sınırıyla karşılaştırılır.
  Karşılaştırma 20 ve 40 saniyede yinelenir.
- Eşleşme "muhtemelen <Ad>" olarak, geçici işaretiyle gösterilir. Belirsizse "Konuşmacı n" kalır.
- ECAPA vektörü saklanmaz; yalnız karar ve puan saklanır.
- Profil güncellenmez, otomatik kayıt yapılmaz.

Decision 5: Canlı veri toplantıya ait iki yan tabloda tutulur: canlı konuşmacılar ve canlı satırlar. İkisi de
`public_id` taşımaz (41 numaralı kuraldaki yan tablo istisnası). Silinme anları şunlardır:
- kesin sonuç hazır olunca (durum `succeeded`);
- toplantı silinince;
- 037'nin yarım yükleme temizliğinde.

Satırlar sıra numarasıyla eklenir. Yazılmış satırın metni değişmez; yalnız konuşmacı etiketi Decision 3 birleştirmesiyle
değişebilir.

Decision 6: Tarayıcı, kayıt sürerken 2 saniyede bir canlı sonuç uç noktasını yoklar ve son gördüğü sıra numarasını ile
sürümü gönderir. Yanıtın içeriği:
- yeni satırlar;
- değişen konuşmacılar;
- güncel sürüm;
- canlı işlemenin ne kadar geride olduğu.

SSE veya WebSocket kullanılmaz. Projede sunucudan itme altyapısı yoktur. Yoklama nginx ve kurum ağ geçidinde ek ayar
istemez. Gecikmeyi asıl belirleyen işleme süresidir.

Decision 7: Kayıt ekranı kontrollerin altında canlı metni gösterir:
- her satırda zaman, konuşmacı etiketi veya ön tahmin, kanal etiketi ve "geçici" işareti;
- "~n sn geride" göstergesi;
- otomatik kaydırma ve "Takip et" anahtarı.

Ekran okuyucuya her satır tek tek okunmaz; yalnız yeni satır sayısı duyurulur. "Bitir"den sonra toplantı sayfasına
geçilir; kesin sonuç hazır olunca bugünkü sonuç ekranı gösterilir.

Decision 8: Çıkarım servisi aynı anda tek iş alır. Bu yüzden canlı işleme önceliklidir.
- Bir canlı oturum sürerken worker, başka toplantıların tek geçişini veya parça analizini başlatmaz; onlar sırada bekler.
- Bir çıkarım servisi aynı anda bir canlı oturum işler. İkinci eşzamanlı kayıt 037 olarak kaydedilir. Ekranında
  "Canlı görünüm şu an dolu; toplantı bitince işlenecek" görünür.
- Kurum platformunda eşzamanlı oturum sayısı ve servis kopyası rotanın 10. adımındaki platform analizine bağlıdır.

Decision 9: Canlı işleme 60 saniyeden fazla geride kalırsa en yeni sese atlar. Atlanan aralık ekranda "canlı görünümde
atlandı" olarak işaretlenir; kesin işleme o aralığı kapsar. Bekleyen iş ve bellek böylece sınırlı kalır.

## Gereksinimler

Requirement 1: Çıkarım servisi yeni bir canlı pencere uç noktası sunar. Uç nokta tek kanallı 16 kHz PCM16 ses (en çok 30
saniye), yazıya çevrilecek aralık ve dil alır. Konuşma bölütlerini, yerel kümeleri, izleme vektörlerini ve kapanmış
bölütlerin kelimelerini döndürür. Testler şunları kapsar: meşgul, hazır değil, bozuk girdi, sınır, CPU modunda ret.

Requirement 2: Arka uç şunları kapsar:
- canlı tabloların şeması ve gözden geçirilmiş Alembic migrasyonu;
- worker'da oturum kilidiyle canlı döngü, Decision 8 önceliği ve Decision 9 atlaması;
- eşleme, birleştirme ve ön tahmin;
- canlı sonuç uç noktası (toplantı okuma izni, kiracı kapsamı) ve temizlik.

Birim testleri ve canlı PostgreSQL entegrasyon testleri şunları kapsar: kiracı yalıtımı, birleştirme ve sürüm, atlama,
başka toplantıların beklemesi, ikinci oturumun reddi, kesin sonuçla silinme. OpenAPI dışa aktarılır, ön yüz tipleri
yeniden üretilir.

Requirement 3: Ön yüzün canlı paneli TR/EN ve erişilebilir olur. Yoklama, sayfadan çıkınca ve oturum değişince eski
yanıtları yok sayar. Ön yüz testleri vardır.

Requirement 4: Worker günlüğüne `meeting_live_cycle` olayı yazılır: kanal, işlenen ses süresi, işleme süresi, geride
kalma ve üretilen satır sayısı. Ses, metin, kişi ve kiracı bilgisi yazılmaz.

Requirement 5: `e2e/` altındaki 037 senaryosu, canlı panelde en az bir geçici satırın göründüğünü ve "Bitir"den sonra kesin
sonucun geldiğini doğrular.

Requirement 6: Ölçümler şunlardır:
- (a) Bu bilgisayarda (GTX 1080 Ti) en az 30 dakikalık gerçek bir Teams görüşmesinde gecikme ölçülür: konuşmanın
  bitişinden satırın ekranda görünmesine kadar, ortanca ve %95'lik değer.
- (b) AMI test kümesinden 4 uzak mikrofon toplantısı, gerçek API üzerinden gerçek zamanlı hızla sistem kanalına
  oynatılır. Ölçülenler: yanlış ön tahmin (yanlış kişiye ad gösterme), canlı ve kesin konuşmacı sayısı ve iki sonucun
  DER'i.
- (c) Canlı oturum sırasında GPU ve RAM kullanımı.

Toplu sonuçlar `results.md`'ye yazılır; toplantı sesi ve metni depoya girmez.

## Katmanlar

- Şema: Requirement 2.
- Vektör: canlı konuşmacının 256 boyutlu izleme vektörü yalnız oturum boyunca saklanır. Model, kayıtlı
  `pyannote/speaker-diarization-community-1` sürümüdür; vektörler normalize edilir. Uzaklık kosinüstür; dizin yoktur ve
  oturum başına en çok birkaç düzine vektör uygulama kodunda tam karşılaştırılır. Vektörler kesin sonuçla silinir.
  Kaynak, toplantı sesiyle aynı yetki ve saklama kuralına bağlıdır. Model değişiminde yeniden vektörleme N/A — vektörler
  oturumla birlikte silinir.
- API ve OpenAPI: Requirement 2.
- Ön yüz: Requirement 3.
- Çıkarım: Requirement 1.
- Önbellek: N/A — önbellekli işlem yok.
- Gözlemlenebilirlik: Requirement 4.
- Yapılandırma: N/A — tur süresi, pencere ve eşikler alan sabitleridir.
- Dağıtım: inference belleği Requirement 6(c) ile 8 GiB chart sınırına karşı doğrulanır; değişiklik gerekirse aynı işte
  yapılır.
- Güvenlik: canlı uç nokta toplantı okuma iznini ve kiracı kapsamını uygular; ön tahmin kişi hafızasını değiştirmez.

## Kabul ölçütleri

- [ ] Birim, entegrasyon, tarayıcı senaryosu ve tam kalite kapısı geçer.
- [ ] Bu bilgisayarda gerçek bir Teams görüşmesinde gecikme ortancası en çok 10 saniye, %95'lik değeri en çok 20
      saniyedir.
- [ ] AMI canlı oynatmasında yanlış kişiye ad gösterilmez (0). Canlı ve kesin sonuç farkları `results.md`'dedir.
- [ ] Canlı oturum sürerken kayıt eksiksiz alınır ve kesin sonuç 037'deki gibi üretilir.
- [ ] Kullanıcı gerçek bir toplantıda canlı görünümü kabul eder (L3).
