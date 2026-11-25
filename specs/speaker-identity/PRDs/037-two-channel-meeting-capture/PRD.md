# PRD — Teams masaüstü toplantısını iki kanalla kaydetme

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [037 — two-channel-meeting-capture](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kabul: 25 Kasım 2026, kullanıcı (003 ile birlikte). Uygulama planı: [plan](plan.md), [görevler](tasks.md).
Kaynak (25 Kasım 2026): Kullanıcı, Teams masaüstü uygulamasıyla katıldığı toplantılarda bir tuşla kayda başlamak,
hem kendi sesinin hem toplantıdaki diğer kişilerin sesinin algılanmasını ve toplantı sürerken sonuç üretilmesini istedi.
Teams botu istenmedi. Kurumda tarayıcı Edge'dir; ekran ve sistem sesi paylaşımı kurum politikasıyla kapatılmamıştır.
Bu PRD kaynağı, toplantı sürerken aktarımı ve kanallara göre kesin sonucu kapsar. Toplantı sürerken ekranda ara sonuç
[003](../003-live-speaker-analysis/PRD.md)'tedir ve bu PRD'ye dayanır.

## Amaç ve önceki durum

Bugün tarayıcı kaydı ([007](../007-microphone-meeting-capture/PRD.md)) yalnız mikrofonu tek kanal kaydeder. Kayıt
durunca dosya mühürlenir, ancak ondan sonra yüklenir. Teams'teki diğer kişilerin sesi alınamaz. Yükleme, toplam boyutun
toplantı oluşturulurken bilinmesini ister (4 MiB parçalar, en çok 512 parça). Çok kanallı ses her okumada tek kanala
karıştırılır.

Hedef: Teams masaüstünde toplantıdayken tek "Kaydı başlat" ile bu bilgisayarın mikrofonu ve sistem sesi (Teams'teki
diğer kişiler) ayrı kanallarda kaydedilsin. Ses toplantı sürerken sunucuya aksın. "Bitir"den sonra işleme yükleme
beklemeden başlasın ve kanallar ayrı işlensin. Mikrofon kanalında yalnız bu bilgisayarın başındakiler, sistem kanalında
yalnız uzaktaki kişiler bulunur. Kaydedenin sesi uzaktakilerle karışmaz; aynı anda konuşma iki ayrı kanala düşer. Bu
beklentinin doğruluk etkisi Requirement 9 ile ölçülür.

## Kararlar

Decision 1: Kaynak Windows'ta Edge'dir. "Kaydı başlat" tek kullanıcı eyleminde iki izin ister:
- seçilen mikrofon (`getUserMedia`);
- ekran paylaşım penceresinde "Tüm ekran" ve "Sistem sesini de paylaş" seçimiyle sistem sesi (`getDisplayMedia`).

Teams'e bot, eklenti, Graph API veya Teams yönetici izni eklenmez; Teams uygulamasında hiçbir şey değişmez. Paylaşım
penceresi her kayıtta bir kez açılır; tarayıcı bunu atlatmaz. Dönen akışta ses izi yoksa kayıt başlamaz ve kullanıcıya
iki seçimi yapması gerektiği gösterilir. Görüntü izi, ses izi doğrulanır doğrulanmaz durdurulur; tek kare okunmaz,
saklanmaz, gönderilmez. Bu PRD yalnız tüm ekran ve sistem sesi yolunu destekler. Tarayıcı sistem sesi sunmuyorsa mod
gösterilmez; nedeni, 007 mikrofon kaydı ve dosya yükleme yolu gösterilir. Doğrulama yalnız Windows ve Edge'de yapılır.

Decision 2: Tek bir `AudioContext` 16 kHz istenerek açılır; gerçek hız doğrulanır ve WAV başlığına yazılır (007
Decision 2). Kanal 0 mikrofon, kanal 1 sistem sesidir. İki kanal aynı saatle örnek örnek hizalı, iç içe PCM16 olarak
yazılır. Sistem sesinde yankı giderme, gürültü bastırma ve otomatik kazanç kapalı istenir; mikrofonda 007'deki tarayıcı
varsayılanları kalır. 16 kHz iki kanal saatte yaklaşık 230 MB'tır. 007'nin 4 saat ve 2 GiB sınırları korunur.

Decision 3: Toplantı satırı kayıt başlarken oluşturulur; başlık, dil ve katılımcılar önce doğrulanır. Satır, son boyut
bilinmeden açılır.
- Ses en çok 2 saniyelik ham PCM parçalarıyla sırayla gönderilir. Her parça başlangıç örneğini, byte'larını ve SHA-256
  özetini taşır.
- Sunucu yalnız beklediği konumdan devam eden parçayı ekler.
- Aynı konum ve aynı özetle tekrar gelen parça başarılı sayılır. Aynı konumda farklı özet çakışmadır. Boşluk bırakan
  parça, beklenen konumla birlikte reddedilir.
- Aynı anda yolda bir parça bulunur.
- Onaylanmamış parçalar tarayıcı belleğinde en çok 32 MiB tutulur; bu 16 kHz iki kanalda yaklaşık 8,7 dakikadır.
- Bağlantı daha uzun koparsa kayıt OPFS'e sürer. Gönderilemeyen kısım "Bitir"den sonra mühürlenmiş OPFS dosyasından
  gönderilir.

Bugünkü 4 MiB'lık dosya yükleme ve sürdürme yolu (002, 029) değişmez.

Decision 4: "Bitir" ses üretimini durdurur ve kalan parçaları gönderir. Ardından toplam örnek sayısını ve parça
özetlerinin zincir değerini iletir: her adımda önceki zincir değeri ile parça özeti birlikte SHA-256'dan geçirilir. Sunucu
WAV başlığını dosyanın başında ayrılmış yere kendisi yazar. Zinciri ve dosyayı 002 doğrulamasından geçirir, toplantıyı
kuyruğa alır. Ses toplantı boyunca aktığı için "Bitir"den sonra yalnız son birkaç saniyelik parçalar beklenir.

Decision 5: Kayıt sürerken 2 dakika parça gelmezse toplantı sayfası "Kayıt kesildi" gösterir. Sahibi iki seçenekten
birini seçer:
- "Gelen kısmı işle": sunucu, alınan örneklerle dosyayı mühürler ve toplantıyı kuyruğa alır.
- Toplantıyı silmek.

Hiçbiri seçilmezse bugünkü 24 saatlik yarım yükleme temizliği uygulanır. Parçalar yeniden gelmeye başlarsa uyarı kalkar.
Sekme kapanıp yeniden açılırsa kayıt kaldığı yerden sürmez. Tarayıcıda kalıp gönderilemeyen ses kurtarılmaz (007
Decision 5).

Decision 6: Kesin işlemede her kanal ayrı bir ses izi gibi [030](../030-whole-recording-diarization/PRD.md) akışından
geçer. 120 dakikaya kadar kayıtta tek geçişte konuşmacı ayırma kullanılır; daha uzun kayıtta veya CPU modunda parçalı akış
kullanılır. Yazıya çevirme kanalın kendi sesiyle yapılır.
- Mikrofon kanalı da konuşmacılara ayrılır. Toplantı odasında tek bilgisayarı paylaşan birden çok kişi böylece ayrı
  konuşmacılar olur.
- Konuşmacı satırı kanalını taşır.
- Kişi hafızası için kanıt sesi ve vektörü konuşmacının kendi kanalından alınır.
- 10 saniye tanıma, 20 saniye otomatik kayıt, isimlendirme, katılımcı listesi (016) ve yetki kuralları değişmez.
- Metin satırları iki kanaldan zaman sırasıyla birleşir. Aynı anda konuşma iki ayrı satır olarak görünür.

Decision 7: Konuşmacı listesinde ve metinde kanal etiketi görünür: mikrofon için "Bu bilgisayar", sistem sesi için
"Toplantı sesi". Zaman aralığı dinlemesi bugünkü gibi iki kanalın karışımını çalar. Tek kanallı toplantılar etiketsiz ve
değişmeden kalır.

Decision 8: Kayıt sırasında iki kanalın ses seviyesi gösterilir. Uyarılar kaydı durdurmaz:
- Sistem kanalı kayıt başladıktan sonra 60 saniye sessiz kalırsa uyarı çıkar: "Toplantı sesi gelmiyor. Teams'in
  hoparlör ayarı Windows'un varsayılan ses çıkışıyla aynı olmalı."
- Mikrofon kanalı 60 saniye sessiz kalırsa ayrı bir uyarı çıkar.
- Sistem sesi mikrofona tekrar tekrar karışırsa "kulaklık kullanın" uyarısı çıkar. Karışma iki kanalın ses zarfı
  benzerliğiyle anlaşılır. Eşik, hoparlörlü ve kulaklıklı deneme ölçümüyle belirlenir ve plana yazılır.

Decision 9: Teams'te mikrofonu kapatmak bu kaydı durdurmaz; arayüz bunu kayıt başlarken söyler. "Mikrofonumu kaydetme"
anahtarı açıkken kanal 0'a sessizlik yazılır, zaman hizası bozulmaz.

Decision 10: Başlamadan önce ekran şunu söyler: kayıt bu bilgisayarın sesini alır ve Teams katılımcılara kayıt uyarısı
göstermez. Kullanıcı her kayıtta "Katılımcıları bilgilendirdim" kutusunu işaretlemeden kayıt başlamaz. Uygulama hukuki
uygunluk iddia etmez; uyum kurum politikasına bağlıdır.

Decision 11: Toplantı boyunca Edge, Teams'in arkasında veya simge durumunda kalabilir. Aktarım döngüsü zamanlayıcıya
değil, ses işleyicisinden gelen iletilere bağlıdır. Kayıt sürerken sayfadan ayrılmak tarayıcı onayı ister. Edge'in
"Paylaşımı durdur" düğmesi veya sistem ses izinin bitmesi kaydı "Bitir" gibi sonlandırır ve kullanıcıya nedeni
gösterilir.

Decision 12: Kayıt süren toplantı, kiracının eşzamanlı yükleme sınırına (`meeting_active_uploads`) sayılır. Kesin işleme
bugünkü worker sırasıyla yapılır. Yeni ayar eklenmez; 2 dakikalık kesinti süresi ve parça süresi alan sabitleridir.

## Gereksinimler

Requirement 1: Ön yüz ekranı TR/EN ve erişilebilir olur. Yeni toplantı ekranında "Teams toplantısı (bu bilgisayar)"
kaynağı yer alır. Ekranın içeriği:
- destek denetimi ve bilgilendirme kutusu;
- mikrofon seçimi;
- iki kanalın seviye göstergesi;
- geçen süre;
- "Mikrofonumu kaydetme" anahtarı;
- "Bitir";
- Decision 5 ve Decision 8 uyarıları;
- hata durumları: izin reddi, ses izi yok, paylaşım durduruldu, bağlantı koptu, sınıra ulaşıldı.

Requirement 2: Ön yüz kayıt modülü şunları yapar: iki kaynaklı yakalama, iki kanallı `AudioWorklet`, OPFS yazımı, sınırlı
bellekli parça kuyruğu, parça ve zincir özetleri, sıralı gönderim ve "Bitir"de kalan kısmın OPFS'ten gönderimi. Birim
testleri vardır.

Requirement 3: Arka uç API'si şunları sağlar:
- iki kanallı kayıt için boyutsuz toplantı oluşturma;
- parça ekleme;
- tamamlama;
- "Gelen kısmı işle";
- toplantı yanıtında kayıt biçimi, alınan süre ve son parça zamanı;
- konuşmacı yanıtında kanal.

Hata gövdesi ve kodları sabittir; JWT, kiracı ve izin kuralları bugünkü yükleme ile aynıdır. OpenAPI dışa aktarılır, ön
yüz tipleri yeniden üretilir.

Requirement 4: Şema ve depolama şunları kapsar:
- toplantıda kayıt biçimi, alınan örnek sayısı ve zincir değeri;
- konuşmacı satırında kanal;
- konuşmacı ayırma kaydının ve parça kayıtlarının kanal başına tutulması.

Alembic migrasyonu gözden geçirilir; tablo ve sütun açıklamaları veritabanına ulaşır. Saklama, silme ve temizlik toplantı
ile aynıdır.

Requirement 5: Arka uç ses okuma ve worker şunları yapar: kanal seçerek okuma (bloklar, pencereler, kanıt örnekleri);
kanal başına akış seçimi ve işleme; metnin zaman sırasıyla birleşmesi; kişi hafızası kanıtının kanaldan alınması. Birim
testleri ve canlı PostgreSQL entegrasyon testleri şunları kapsar: kiracı yalıtımı, tekrar, boşluk ve çakışan parça,
kesilen kaydın işlenmesi, 4 saat sınırı, tek kanallı toplantıların değişmemesi.

Requirement 6: Çıkarım servisi değişmez: her kanal bugünkü tek kanallı uç noktalara ayrı ayrı gönderilir.

Requirement 7: Worker günlüğüne `meeting_capture` olayı yazılır: alınan süre, parça sayısı, tekrar, reddedilen boşluk
ve kesinti bilgisi. Ses, metin, kişi ve kiracı bilgisi yazılmaz.

Requirement 8: `e2e/` altında kalıcı bir tarayıcı senaryosu bulunur. Senaryo gerçek giriş formunu ve Edge'in sahte
cihaz ile otomatik ekran seçimi ayarlarını kullanarak iki kaynaklı kaydı uçtan uca sürer. `e2e/QUALITY_MANIFEST.md`'ye
kaydedilir. Kanal içeriğinin doğruluğu (sesim kanal 0'da, diğerleri kanal 1'de) bu bilgisayarda gerçek bir Teams
görüşmesinde elle doğrulanır.

Requirement 9: Ölçümler şunlardır:
- (a) Bu bilgisayarda Edge ve Teams masaüstüyle, Edge arka plandayken en az 60 dakikalık kayıt; alınan ve kaydedilen
  süre farkı ölçülür.
- (b) Bilinen katılımcılı iki Teams deneme görüşmesi; her biri iki kanallı işlenir ve aynı kaydın tek kanala
  karıştırılmış hali bugünkü yoldan işlenir. Karşılaştırılan değerler: konuşmacı sayısı, kaydedenin konuşmasının doğru
  konuşmacıya düşen payı ve belirsiz satır oranı.
- (c) Hoparlörlü ve kulaklıklı denemede karışma uyarısı.

Toplu sonuçlar `results.md`'ye yazılır; toplantı sesi ve metni depoya girmez.

## Katmanlar

- Şema: Requirement 4.
- API ve OpenAPI: Requirement 3.
- Ön yüz: Requirement 1–2.
- Tarayıcı senaryosu: Requirement 8.
- Çıkarım: N/A — Requirement 6; uç noktalar değişmez.
- Vektör: N/A — yeni vektör sütunu yok; mevcut sütunlar kanal kanıtıyla kullanılır.
- Önbellek: N/A — önbellekli işlem yok.
- Gözlemlenebilirlik: Requirement 7.
- Yapılandırma: N/A — Decision 12; yeni ayar yok.
- Dağıtım: parçalar 2 saniyelik olduğu için nginx gövde sınırı (51 MiB) ve chart değişmez; chart çizimi kalite kapısında
  doğrulanır.
- Güvenlik: Görüntü okunmaz. Sahip ve izin denetimi bugünkü yüklemeyle aynıdır. Parça boyutu sınırlıdır. Günlüklere ses
  yazılmaz.

## Kabul ölçütleri

- [ ] Birim, entegrasyon, tarayıcı senaryosu ve tam kalite kapısı geçer.
- [ ] Bu bilgisayarda gerçek bir Teams toplantısında, Edge arka plandayken en az 60 dakikalık kayıt eksiksiz alınır.
      Alınan ile kaydedilen süre farkı en çok 1 saniyedir. "Bitir"den sonra işleme 10 saniye içinde başlar.
- [ ] İki Teams deneme görüşmesinde kaydedenin konuşmasının tamamı mikrofon kanalındaki konuşmacıya düşer. Sistem
      kanalında bulunan konuşmacı sayısı uzaktaki katılımcı sayısına eşittir. Tek kanallı işlenişle karşılaştırma
      `results.md`'dedir.
- [ ] Kesilen kayıt "Gelen kısmı işle" ile işlenir; kayıp yalnız gönderilememiş kısımdır.
- [ ] Karışma uyarısı hoparlörlü denemede çıkar, kulaklıklı denemede çıkmaz.
- [ ] Kullanıcı gerçek bir toplantıda sonucu kabul eder (L3).

Open Question 1: Katılımcı bilgilendirme metninin kurum politikasına göre son hali (sahibi: kullanıcı ve kurum hukuk
birimi). Uygulama Decision 10'daki metinle başlar.
