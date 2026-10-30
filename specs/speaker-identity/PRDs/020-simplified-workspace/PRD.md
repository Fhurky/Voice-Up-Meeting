# PRD — Sade çalışma alanı tasarımı

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [020 — simplified-workspace](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (30 Ekim 2026): Renk teması ([019](../019-institutional-visual-theme/PRD.md))
uygulandıktan sonra kullanıcı arayüzün karmaşık göründüğünü, daha basit ve daha şık bir
genel tasarım gerektiğini belirtti. Kabul edilirse [008](../008-modern-workspace/PRD.md)
Requirement 1–3'teki sayfa yerleşimi ve ana sayfa içeriği bu PRD ile değişir; 008'in
erişilebilirlik, yerelleştirme, yetki ve davranış kararları ile 019 paleti korunur.
Kabul (30 Ekim 2026): Kullanıcı taslağı kabul etti ve Open Question 1'de mevcut yan menünün
korunmasını (c) seçti.

## Amaç ve önceki durum

Bugün ekranlar iç içe renkli kutular (panel içinde rehber kutusu, onun içinde uyarı ve
metin kutusu), sürekli görünen uzun açıklamalar, büyük dekoratif ana sayfa alanı, yan
menüdeki tanıtım notu ve tek ekranda birden çok iş (toplantı listesi ile tam yükleme formu,
profil listesi ile kayıt paneli) içerir. Hedef: her ekranda tek bir ana iş, az ve kısa
metin, tek katman kart, tutarlı yazı ölçeği ve bol boşluk. Özellikler, API, yetkiler ve
veriler değişmez.

## Kararlar

Decision 1: Mevcut yan menü ve dar ekrandaki yatay gezinme korunur; yan menüdeki tanıtım
notu ve bölüm etiketi kalkar. Marka, dört bölüm bağlantısı, hesap ve çıkış kalır.

Decision 2: Sayfa iskeleti: ortalanmış, en fazla 1120 px içerik; tek başlık ve en fazla
bir satır açıklama; açık zemin üzerinde tek katman beyaz kartlar. Kart içinde renkli
alt kutu yalnız gerçek uyarı veya hata için kullanılır; yardım metni küçük gri metin veya
açılır "Ayrıntılar" alanıdır. Yazı ölçeği 28/20/16/14/12 px, boşluklar 8 px katları,
köşe yarıçapı tek değerdir; büyük harfli üst etiketler kaldırılır.

Decision 3: Ana sayfa: "Merhaba, {ad}" karşılaması; izinli ana eylemler iki büyük eylem
kartı olarak (Toplantı kaydı yükle, Mikrofonla kaydet); küçük toplam göstergeleri ve son
toplantılar listesi. Büyük dekoratif alan ve üç adımlı rehber kalkar; rehber yalnız hiç
toplantı yokken boş durum olarak görünür. Güvence satırı sayfa altında küçük metindir.

Decision 4: Toplantılar: önce toplantı listesi ve "Yeni toplantı" ana düğmesi. Düğme
yükleme akışını aynı sayfada açar: kaynak seçimi (dosya / mikrofon) iki büyük seçenek,
ardından ad ve dil. Katılımcı listesi, kişi sayıları ve hafıza seçeneği "Gelişmiş
seçenekler" altında kapalı başlar; mevcut varsayılanlar ve doğrulama korunur, hatalı
gelişmiş alan varsa bölüm açılır.

Decision 5: Toplantı sonucu: başlıkta ad, tarih, durum ve tek satırlık özet (süre,
konuşmacı sayısı); ikincil eylemler (yenile, sil) sağda sessiz düğmeler. İçerik "Metin"
ve "Konuşmacılar" sekmeleriyle ayrılır; erişilebilir sekme rolleri ve klavye geçişi
bulunur.

Decision 6: Konuşmacılar: profil listesi sade satırlar/kartlar (avatar, ad, örnek sayısı,
eylemler); "Yeni profil" düğmesi kayıt panelini açar. Okunacak metin kayıt başlarken
görünür, öncesinde tek satırlık yönlendirme yeterlidir.

Decision 7: Giriş ekranı: hafif marka gradyanı üzerinde ortalanmış tek giriş kartı; ürün
adı, kısa açıklama ve güvence satırı. Adım şeridi ve büyük dalga görseli kalkar.

Decision 8a: Yan menüden sayfa değiştirirken ekran boşalmaz: sonraki sayfanın kodu
yüklenirken mevcut sayfa ve menü görünür kalır; sayfa kodları giriş sonrası arka planda
önceden yüklenir. (30 Ekim 2026'da kullanıcının bildirdiği 1 saniyelik beyaz ekran üzerine
eklendi.)

Decision 8: Yeni bağımlılık, yazı tipi veya ağdan görsel eklenmez; panel ve menüler yerel
HTML öğeleri (`dialog`, `details`, sekme rolleri) ve mevcut değişkenlerle yapılır.

## Gereksinimler

Requirement 1: Bütün sayfalar Decision 1–7'ye göre yenilenir; mevcut eylemler, yetki
gizlemeleri, yükleme/hata/boş durumları ve TR/EN metinler korunur. Kısaltılan veya
taşınan metinler iki katalogda eşit anahtarlarla güncellenir.

Requirement 2: Ön yüz birim testleri yeni yerleşime göre güncellenir; davranış testleri
zayıflatılmaz. Yerleşimden etkilenen kalıcı tarayıcı senaryoları (gezinme, toplantı
yükleme, katılımcı listesi, mikrofon kaydı, profil kaydı) aynı kabul noktalarıyla
güncellenip geçer.

Requirement 3: TR/EN, 1440 ve 390 px'te bütün sayfaların ekran görüntüleri incelenir;
yatay taşma yoktur; 019 kontrast testi geçer.

## Katmanlar

Backend, API, şema, worker, vektör, gözlemlenebilirlik ve Kubernetes: N/A — yalnız ön yüz
sunumu, kataloglar ve tarayıcı senaryoları değişir.

## Kabul ölçütleri

- [ ] Yeni yerleşim bütün sayfalarda uygulanır; tam ön yüz kapısı ve etkilenen tarayıcı senaryoları geçer.
- [ ] TR/EN dar/geniş ekran görüntüleri incelenir.
- [x] Kullanıcı görsel sonucu kabul eder (L3). (30 Ekim 2026: kullanıcı inceledi, "şimdilik yeterli".)

Open Question 1 (kapandı, 30 Ekim 2026 — c): Gezinme biçimi: (a) üst çubuk (Decision 1, önerilen), (b) yalnız simge
ve etiketten oluşan ince yan menü, (c) mevcut yan menü korunur, yalnız sayfa içerikleri
sadeleşir.
