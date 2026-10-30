# PRD — Toplantı katılımcı listesi

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [016 — meeting-participant-roster](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (29 Ekim 2026): Kullanıcı, doğrulukta ilk odak olarak ölçüm altyapısını ve
toplantıya katılımcı listesi eklemeyi seçti. Bağımlılık:
[015](../015-public-benchmark-evaluation/PRD.md) taban çizgisi.
Kabul (29 Ekim 2026): Kullanıcı 015, 016 ve 017 taslaklarını kabul etti ve 015 ile başlanmasını istedi.

## Amaç ve önceki davranış

Bugün toplantıdaki her ses, tenant'ın bütün kalıcı profilleri arasında aranır
(`speaker_repository.ranked` ve `ranked_meeting`, ilk iki aday). Galeri büyüdükçe benzer
sesler ve yanlış eşleşme riski artar. Toplantıyı başlatan kullanıcı, davetli kayıtlı
kişileri seçebildiğinde arama 50 kişi yerine birkaç kişi arasında yapılır; liste dışı
bir sesin listedeki birine zorlanmaması da ayrıca güvence altına alınır. Model, boyut
ve 0,55 / 0,45 / 0,10 eşikleri değişmez.

## Kararlar

Decision 1: `MeetingCreate` isteğe bağlı `participant_profile_ids` alır: 0–50 adet,
tekil, aynı tenant'ta silinmemiş profil `public_id` değerleri. Liste yeni
`meeting_participant` bağlantı tablosunda tutulur: `(meeting_id, speaker_profile_id)`
birleşik anahtar, aynı tenant'a fiziksel FK ve zorunlu audit/soft-delete alanları;
bağlantı tablosu olduğundan `public_id` taşımaz. Liste toplantı oluşturulduktan sonra
değişmez; yeniden deneme aynı listeyi kullanır.

Decision 2: Liste verildiğinde kalıcı kimlik kararı şöyle verilir:

1. İki vektör popülasyonunda aday kümesi listedeki profillerle sınırlanır ve mevcut
   `decide` / `fuse_populations` kuralları uygulanır.
2. Aynı popülasyonlarda liste dışı en iyi aday ayrıca hesaplanır. Liste dışı bir profil,
   liste içi en iyi adaydan daha yüksek skor alırsa karar `ambiguous`, gerekçe
   `outside_roster` olur. Bu kontrol, listede olmayan bir kişinin listedekine
   zorlanmasını önler.
3. Liste içi karar `unknown` ise ses listedeki kimse değildir (misafir); karar listesiz
   mevcut akışla yeniden verilir. Böylece listede olmayan kayıtlı bir kişi tanınır ve
   yeni profil olarak kopyalanmaz; kimseye benzemeyen ses mevcut bilinmeyen kişi ve
   otomatik hafıza kurallarından geçer.

Decision 3: Toplantı içi atama kuralları korunur. Birbiriyle örtüşen veya doğal olarak
ayrı bilinen iki küme aynı profile bağlanamaz (`conflicting_assignment`). Örtüşmeyen
iki küme aynı listedeki kişiye bağlanabilir, çünkü konuşmacı ayırma tek kişiyi
bölebilir. Katı bire bir atama uygulanmaz.

Decision 4: Liste, konuşmacı sayısı ipucu türetmez. Listede yalnız kayıtlı kişiler
bulunur; kayıtsız katılımcılar eksik kalacağından liste uzunluğunu üst sınır yapmak
konuşmacı ayırmayı kişileri birleştirmeye zorlayabilir. Katılımcı sayısı ve kesin
konuşan sayısı yalnız kullanıcı girerse kullanılır; girilen katılımcı sayısı liste
uzunluğundan küçük olamaz. (29 Ekim 2026'da uygulama sırasında düzeltildi.)

Decision 5: Yükleme ve mikrofon formlarında aranabilir, etiketli çoklu profil seçici
bulunur; klavyeyle kullanılabilir, seçilen kişi sayısını gösterir. Alan
`speaker_profiles:read` gerektirir; izin yoksa gizlenir ve nedeni açıklanır. Toplantı
sayfasında katılımcı listesi ve her konuşmacının liste içi/dışı durumu görünür. TR/EN.

## Gereksinimler

Requirement 1: Şema otoritesi, üretilen ve incelenen Alembic migration; tablo ve
kolon açıklamaları; aktif kayıt için kısmi indeks.

Requirement 2: Repository'de liste kısıtlı ve liste dışı en iyi aday sorguları
(tenant ve model sürümü filtreleri korunur); servis katmanında Decision 2–4.

Requirement 3: API: oluşturma isteği, toplantı yanıtında katılımcılar, tipli hatalar
(`participant_not_found`, `participant_limit`, yinelenen değer); idempotency parmak
izine liste dahil edilir. OpenAPI ve frontend tipleri yeniden üretilir.

Requirement 4: Frontend seçici ve toplantı sayfası gösterimi; birim testleri ve kalıcı
tarayıcı senaryosu (TR/EN, dar/geniş).

Requirement 5: 015 protokolüyle AMI'de listeli ve listesiz koşumların eşlenmiş
karşılaştırması `results.md` içine kaydedilir.

## Güvenlik ve veri

Liste çözümlemesi tenant içinde yapılır; başka tenant'ın profili 404 ile reddedilir.
Otomatik hafıza `speaker_profiles:write` kuralı değişmez. Liste profil vektörlerini
değiştirmez. Vektör sözleşmesi: N/A — model, boyut, metrik ve eşikler değişmez.
Worker: mevcut toplantı worker'ı. Kubernetes: chart değişmez. Gözlemlenebilirlik:
yeni metrik yok; karar gerekçesi mevcut `reason` alanında.

## Kabul ölçütleri

- [ ] Migration, repository ve servis kararları gerçek PostgreSQL testleriyle doğrulanır (tenant yalıtımı, silinmiş profil, liste dışı daha iyi aday, misafir, bölünmüş kişi).
- [ ] API sözleşmesi, OpenAPI ve frontend tipleri günceldir; frontend birim testleri ve tarayıcı senaryosu geçer.
- [ ] AMI'de listeli koşumda galeri dışı yanlış kabul, listesiz taban çizgisinden yüksek değildir ve toplantılar arası doğru tanıma eşlenmiş karşılaştırmada raporlanır.
- [ ] Tam profil kalite kapısı geçer.
