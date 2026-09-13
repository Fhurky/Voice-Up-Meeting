# PRD — Modern toplantı çalışma alanı

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [008 — modern-workspace](../../roadmap.md)
Kabul kaydı (11 Eylül 2026): Kullanıcı mevcut basit arayüzün modern, anlaşılır ve
yenilikçi bir görsel tasarımla yenilenmesini açıkça istedi. Bu kabul mevcut
yeteneklerin sunumunu kapsar; model doğruluğu veya yeni toplantı bağlantısı kabulü değildir.

## Amaç ve aktörler

Toplantı kaydı yükleyen, sonucu inceleyen ve kişileri adlandıran yetkili kullanıcı
bir sonraki eylemini kolayca bulur. Salt okunur kullanıcı aynı bilgi düzeninde
mevcut kayıtları inceler. Yerel yönetici mevcut açık giriş seçeneğini kullanır.
İlk kullanımda dosya, konuşmacılı metin ve kalıcı kişi hafızası arasındaki ilişki
anlaşılır; geçmiş işleri olan kullanıcı sonuçlara hızla ulaşır.

## Kararlar ve değişmezler

Decision 1: `kt-vibecoding-python-web-v2` profili, mevcut React/Vite istemcisi,
FastAPI sözleşmeleri ve yetki kontrolleri korunur. Bu çalışma yalnız sunum ve
erişilebilir etkileşim düzenidir; backend, şema, model veya eşik değiştirmez.

Decision 2: Görsel dil sıcak kırık beyaz çalışma yüzeyi, koyu lacivert gezinme
alanı, ölçülü mor vurgu ve ses dalgasını çağrıştıran yerel vektör öğeleridir.
Renk, aralık, yazı, gölge ve odak kararları merkezi anlamsal değişkenlerden gelir.
Paylaşılan düzen, kart, bölüm, form, durum ve boş sonuç örüntüleri kullanılır.
Yeni dış bağımlılık, uzak yazı tipi, çalışma anında ağdan görsel veya telemetri eklenmez.

Decision 3: Kullanıcının ana akışı yüklenen toplantı kaydıdır. Mikrofon, canlı
toplantı, otomatik platform bağlantısı veya çalışmayan bir eylem eklenmez.
Ana sayfa yalnız uygulanmış ve kullanıcının iznine açık eylemler sunar.
İstatistikler gösterilecekse mevcut gerçek veriden türetilir; örnek kayıt,
uydurulmuş doğruluk oranı veya doğrulanmamış cihaz bağlantısı ürün verisi gibi görünmez.

Decision 4: Kimlik kararları, yeterli konuşma eksikliği, belirsizlik, iş hatası,
yükleme durumu ve başarı farklı durumlar olarak görünür. Benzerlik puanı yüzde
güven olarak yeniden adlandırılmaz. Kısa konuşmanın metni hafızaya kayıt olmadan
görülebilir; 002'nin kişi gruplama ve kalıcı kimlik ayrımı korunur.

## Gereksinimler

Requirement 1: Giriş, ana sayfa, toplantı listesi/yükleme, toplantı sonucu,
konuşmacı profilleri, tek ses analizi ve iş sonucu aynı görsel dili kullanır.
Geçerli sayfa ve ana eylem belirgindir. Gezinti, dil değiştirme, çıkış ve içerik
başlıkları klavye ve ekran okuyucuyla erişilebilir olur.
Ana sayfa, mevcut servisler aracılığıyla izin verilen toplantı ve profil
toplamlarını ve en fazla dört son toplantıyı gerçek durumlarıyla gösterir;
isteklerin yükleme, hata ve boş sonuçları ayrılır. Toplantıya belirgin bir
geçiş ve yükle → incele → hatırla adımlarını açıklayan kısa bir rehber bulunur.
İzin verilmeyen kaynağa yalnız özet göstermek için istek gönderilmez.

Requirement 2: Dosya seçimi, başlık, konuşma dili ve iki ayrı isteğe bağlı kişi
sayısı girdisinin mevcut davranışı korunur. Uzun kayıt yükleme ilerlemesi,
kaldığı yerden sürdürme, iptal, bekleyen/işlenen iş ve hata açıklamaları
okunabilir ve tutarlı hiyerarşide sunulur. Mevcut doğrulama ve yükleme seçimi
durumu yalnız görünümü değiştirmek amacıyla sıfırlanmaz.
İsteğe bağlı kişi sayıları etiketli, klavyeyle açılabilir yerel bir ayrıntı
alanında toplanabilir; hatalı değer nedeniyle gizli bir geçersiz alan oluşmaması
için doğrulama sırasında ilgili bölüm görünür olur.

Requirement 3: Toplantı sonucunda metin, konuşmacı, zaman bilgisi ve kişi hafızası
durumu taranabilir biçimde ayrılır. Mevcut ad değiştirme, sayfalama, yeniden
deneme, silme ve profil bağlantıları yetki ve işlem durumlarını korur.
Profil listesi ve analiz sonucu yoğun içerik ile uzun adlarda taşmaz.

Requirement 4: Dar ve geniş görünümde ana eylemler erişilebilir kalır; sayfanın
tamamında yatay taşma oluşmaz. Formların görünür etiketleri, açıklamaları,
odak/hover/disabled durumları ve semantik buton/bağlantıları bulunur. Hareket
eklenirse azaltılmış hareket tercihi gözetilir. Görsel motifler dekoratiftir,
gerçek ses etkinliği veya işlem ilerlemesi olarak sunulmaz.

Requirement 5: Yeni ve değişen kullanıcı metinleri, erişilebilir adlar ve belge
başlıkları mevcut `tr` ve `en` kataloglarında eşit anahtarlarla bulunur. Tarih,
sayı ve süreler geçerli yerel ayara uygun biçimlenir. Dil değiştirmek oturumu,
mevcut veri yetkisini veya formun kullanıcı girdisini değiştirmez.

Requirement 6: Mevcut şifreli giriş ve açıkça etkinleştirilmiş yerel yönetici
girişi korunur. Salt okunur kullanıcıya yazma veya analiz başlatma eylemi
sunulmaz. Yeni görünüm gerçek API yükleme, boş, hata ve terminal durumlarını
gösterir; bu durumların hiçbiri örnek başarı görünümüne dönüştürülmez.

## Veri, güvenlik ve işletim

API/veri sözleşmesi, kalıcı şema ve migration: N/A — mevcut sözleşmeler ve
veri kaynakları kullanılır; yeni veri alanı veya uç nokta yoktur.
Tenant ve rol güvenliği: mevcut servis, korunan rota ve görünür eylem denetimleri
korunur; yalnız yöneticiyle yapılan görsel kontrol yetki kanıtı sayılmaz.
Yeni cache/worker/model/Secret/ortam ayarı: N/A — sunum yenilemesidir.
Gözlemlenebilirlik: mevcut HTTP hata ve yükleme durumları görünür kalır; kişisel
ses, metin, token veya ad yeni konsol kaydına yazılmaz.
Saklama politikası ve eşzamanlılık: N/A — mevcut kayıt ömrü ve iş protokolü değişmez.
Dağıtım: mevcut SPA üretim derlemesi ve ters proxy üzerinden sunulur; sabit
teknoloji profili, çevrimdışı çalışma ve mevcut chart sözleşmesi korunur.

## Test stratejisi ve kabul ölçütleri

Davranışa dokunan değişiklikler gözlenebilir sözleşme testleriyle korunur.
Mevcut form, giriş, yerelleştirme, yetki ve sonuç testleri çalıştırılır; saf renk
değişikliği için CSS değerini taklit eden test yazılmaz. Kalıcı tarayıcı senaryosu
ortak harness ile gerçek giriş ve iki dilde gezinmeyi sınar. Geniş ve dar ekran
görüntüleri yerleşim kanıtıdır; erişilebilirlik ağacı semantik durumları doğrular.

- [x] Ana ekranların tamamı ortak tasarım dilini kullanır; ana eylem ve etkin rota belirgindir.
- [x] TR/EN metinleri, klavye erişimi, etiketler, odaklar ve dar/geniş yerleşim doğrulanır.
- [x] Mevcut giriş, yükleme, sonuç, profil ve yetki sözleşmeleri otomatik testlerde korunur.
- [x] Gerçek ters proxy kökeninde şifreli girişle sıradan rol, gezinme ve iki dil gözlenir; konsol/ağ sonucu kaydedilir.
- [x] Mevcut gerçek toplantı sonucu tarayıcıda incelenir; tasarım kontrolü model doğruluğu kanıtı diye sunulmaz.
- [x] Kalıcı senaryo kalite manifestine kayıtlıdır; ön yüz kontrolleri ve `scripts/quality-gate.sh all` sonucu raporlanır.
- [x] Güvenlik ve çalıştırılamayan senaryo/ortam kontrolleri dahil eksik kanıtlar koşum raporunda açıkça adlandırılır.

Kanıt seviyesi görevlerde ve koşum raporunda kaydedilir. Tasarım isteği yeni
commit veya push yetkisi içermez; yayın işlemi ayrı kullanıcı talimatına bağlıdır.

11 Eylül kanıtı: 691 otomatik test ve 22 gerçek tarayıcı ekran kontrolü başarılı.
Kalıcı senaryo yürütücüsü ve güvenlik taraması ortam eksikleriyle çalışmadı;
kontrol sonuçlarının raporlanması bunların başarılı olduğu anlamına gelmez.
[Koşum raporu](../../../../docs/evidence/2026-09-11-modern-workspace/README.md).
