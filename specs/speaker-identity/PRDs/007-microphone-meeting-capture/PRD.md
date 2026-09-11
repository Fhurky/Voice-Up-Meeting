# PRD — Mikrofon kaydından toplantı analizi

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [007 — microphone-meeting-capture](../../roadmap.md)
Sabit profil: `kt-vibecoding-python-web-v2`.
Kabul kaydı: 10 Eylül 2026'da kullanıcı ses dosyası yükleme **veya** kayıt alma
isteğini açıkça iletti. Bu kaynak kapsamı başlangıçta 002 içinde Accepted idi.
Aynı gün kullanıcı "Kaydı yüklemek yeterli; tanıma ve hafızayı tamamla" yanıtıyla
güncel teslimi dosyaya daralttı. Önceki mikrofon isteği silinmeden bu bağımsız
yeteneğe taşındı; kabul edilmiş fakat uygulanmamış durumdadır. Güncel 002 dosya
tesliminin tamamlanması bu yeteneğin tamamlanmasını gerektirmez.

## Amaç, aktörler ve sınır

Yetkili kullanıcı tarayıcıda seçtiği mikrofonla kayıt alır, kaydı durdurur ve
doğrulanmış ses kaynağını 002'nin konuşmacılı metin/kalıcı hafıza akışına verir.
Aktörler toplantı sahibi, tenant yöneticisi ve analiz yürütücüsüdür. Varsayılan
mikrofon yalnız seçilen giriş cihazını yakalar; bilgisayarın bütün seslerini veya
uzak Teams katılımcılarını otomatik toplamaz. Canlı metin/kimlik yayını ve toplantı
platformu bağlantısı bu yeteneğe dahil değildir; 003 canlı kimlik taslağı ayrıdır.

## Kararlar

Decision 1: Mikrofon yalnız kaynak üretir; 002 model rolleri, kalıcı kimlik,
>20 saniye temiz kanıt, isimlendirme ve yetki kuralları tekrar uygulanmaz veya
gevşetilmez. Analiz kayıt durup son parça doğrulandıktan sonra başlar.

Decision 2: Tarayıcı kaydı desteklenen gerçek kapsayıcı/codec ile aktarılır;
WebM/Opus ilk hedeftir. MP4/AAC ancak bağımsız decoder kabulü ve gerçek tarayıcı
testiyle açılır. Uzantı değiştirmek ses dönüştürme değildir. Desteklenmeyen
kayıtta açıklama ve 002 dosya yükleme seçeneği gösterilir.

Decision 3: Tam kayıt tarayıcı RAM'inde biriktirilmez. 002'nin sıralı, boyut/hash
doğrulamalı aktarımı kullanılır; gönderilmemiş yerel tampon en çok 16 MiB olur.
Tampon dolarsa sessiz kayıp yerine kayıt durur ve eksik aktarım görünür olur.

## Gereksinimler

Requirement 1: Mikrofon izni, cihaz seçimi, kayıt süresi, durdurma ve iptal
erişilebilir TR/EN arayüzünde bulunur. İzin reddi, cihaz yokluğu/kesilmesi,
desteklenmeyen format ve bağlantı hatası ayrı yerelleştirilmiş durumlardır.

Requirement 2: İptal, sayfadan çıkma ve geç dönen izin sonucu bütün mikrofon
track'lerini kapatır. Durdurma son `dataavailable` parçasını bekler; henüz
aktarılmayan son ses tamamlanmış kabul edilmez. Yenileme kaybolan mikrofon
geçmişini yeniden yaratmaz; eksik kayıt tamamlanmış kaynak gibi işlenmez.

Requirement 3: Kaynak 002'nin yetkili yükleme portundan geçer; aynı tenant,
boyut/süre, hash, tekrar, kaynak sınırı ve iptal kuralları uygulanır. Gerekli
codec desteği gerçek kaynakla dondurulmadan hayalî model yanıtıyla kabul yapılmaz.

Requirement 4: Tam kaynak 002 analiziyle konuşmacılı metin verir; kısa kişinin
metni korunur ve biyometrik profil sonucu ayrı gösterilir. 002 sayı ipuçları ve
elle isim verme sözleşmesi kullanılır; kaynak kaydı ayrı kimlik sistemi üretmez.

## Veri, güvenlik ve çalışma

Şema N/A — ayrı kayıt/profil otoritesi oluşturulmaz; 002 kaynak ve iş verisi
kullanılır. Gerçek codec metadata'sı şema değişikliği gerektirirse bu PRD önce
güncellenip SQLAlchemy/Alembic eklemeli migrasyonuyla uygulanır. Önbellek N/A —
aktarılmış kaynak ve kalıcı iş checkpoint'i otoritedir.

JWT/tenant/rol denetimi 002 ile aynıdır; otomatik hafıza için ayrıca profil yazma
izni gerekir. Mikrofon kullanıcı eylemi ve tarayıcı izni olmadan başlamaz; ses,
transkript veya token loglanmaz. Saklama ve silme 002 kaynak/profil ayrımını
izler. Web/API Python 3.13/FastAPI ve React/Vite sınırında kalır; farklı backend
veya çalışma anında model/bağımlılık indirme eklenmez.

Decoder/lisans/hash, typed settings, ortam örnekleri, Compose/Helm, kaynak
istekleri ve readiness gerçek destekle birlikte güncellenir. Kod/bağımlılık
sürümleri mevcut admission kurallarıyla değerlendirilir; model hazırlığı bağımlılık
kabulü yerine geçmez. Gözlemlenebilirlik yalnız kayıt süresi, bekleyen byte,
onaylanan parça ve sınıflandırılmış hata/iptal sayısını içerir.

## Test ve kabul

- [ ] Requirement 1–2: Gerçek TR/EN tarayıcıda izin, gerçek kayıt, cihaz kesilmesi, durdurma/son parça, iptal, sayfadan çıkma ve geç izin track temizliği gözlenir.
- [ ] Requirement 2–3: 16 MiB tampon, bağlantı kesilmesi, tekrar, eksik/çelişkili parça, yetki ve tenant testleri gerçek HTTP/disk sınırında geçer.
- [ ] Decision 2 / Requirement 3: Kullanılan tarayıcı kapsayıcısı gerçek çevrimdışı decoder ile çözülür; desteklenmeyen format açıklaması dosya akışını bozmaz.
- [ ] Requirement 4: Durdurulan gerçek mikrofon kaydı 002 üzerinden konuşmacılı metne ve uygun hafıza sonucuna dönüşür; sahte capture veya token enjeksiyonu canlı kanıt sayılmaz.
- [ ] Tam profil/güvenlik/kontrat/chart ve gerçek tarayıcı kanıtı kaydedilir; eksik cihaz, ortam ve L3 kabulü açıkça raporlanır.

Open Question 1: Hedef tarayıcılar üzerinde doğrulanacak kapsayıcı/codec ve bağımsız
decoder kabulü; 002 dosya teslimi bu sorunun çözülmesini beklemez.
