# PRD — Bağlama göre konuşma sözcüklerini gözden geçirme

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [012](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`.
Kabul: Kullanıcı 13 Eylül 2026'da bağlama göre küçük ASR sözcük hatalarını
düzeltmeyi ve kurulu Ollama `qwen3.5:27b` modeliyle test etmeyi istedi.
Kullanıcının kendi 30 saniyelik deneyindeki mevcut kaliteyi yeterli bulması
korunur; genel elli kişilik başarı iddiasına çevrilmez.

## Amaç ve aktörler

Toplantı okuyup analiz çalıştırabilen kullanıcı, tamamlanmış bir konuşma
satırını komşu konuşmaların bağlamında inceletir. Model yanlış duyulmuş küçük
sözcükler için sınırlı değişiklik önerir. Orijinal kayıt, metin, zaman ve
konuşmacı hafızası aynı kalır. Bu teslim seçilen satırın geçici önizlemesidir;
otomatik tüm toplantı düzenlemesi veya kalıcı insan düzenlemesi değildir.

## Kararlar

Decision 1: Sonuç ekranında her uygun satır için “Bağlama göre kontrol et”
eylemi vardır. Ham metin görünür kalır; önerilen metin ve eski→yeni sözcükler
ayrı gösterilir. Uygulama otomatik kaydetme, yeniden yazma, kişi birleştirme
veya özetleme yapmaz. Değişiklik yok ve güvenli bulunmayan öneri durumları
ayrı açıklanır; modelin kendi güven puanı kabul ölçütü değildir.

Decision 2: `POST /meetings/{public_id}/transcript/{transcript_id}/correction-preview`
yalnız yol kimliklerini kullanır; istemci ham metin, prompt, model veya sunucu
adresi göndermez. `meeting_analysis:read` ve `meeting_analysis:run` gerekir.
Hedef ve bağlam aynı tenant/toplantıdan, silinmemiş `succeeded` sonuçtan alınır.
Kayıt sesinin saklama süresi dolmuş olabilir; metin hâlâ geçerliyse metin
incelemesi yapılabilir. Metnin kendi yaşam döngüsü ve soft-delete korunur.

Decision 3: Sunucu hedefi ve en yakın önceki/sonraki en çok üçer satırı seçer;
hedef en çok 1.024 karakter, toplam kaynak bağlamı en çok 4.000 karakterdir.
Hedef kesilmez; uzun hedef 422 `text_review_context_limit` üretir. Komşular
deterministik bütçeyle alınır; bağlamın eksik olması sözcük uydurmayı haklı
kılmaz. Model yalnız metin/dil alır; tenant, hesap, profil, kişi adı veya
veritabanı kimlikleri prompta eklenmez. Alıntılanan konuşma talimat değildir.

Decision 4: Model cevabı yalnız `edits` dizisidir; en çok üç `original` ve
`replacement` çifti, her bir alan en çok 64 karakter. Eski metin hedefte
birebir ve yalnız bir kez bulunmalıdır. Yeni metin boş olamaz; kontrol/biçim
karakteri, sınır/örtüşme, aşırı kelime değişimi ve geniş yeniden yazım
reddedilir. En çok üç kelimelik küçük değişiklikler ve sınırlı yazım mesafesi
kabul edilir; salt noktalama/imla bu yeteneğin başarı ölçütü değildir.
Sayı/rakam/tarih, belirgin özel ad ve olumsuzluk değiştiren öneriler korumalı
denetimden geçer; koruma kapsamı testlerle açık belirtilir, bütün anlamsal
hataları yakaladığı iddia edilmez. Güvenli öneriler ayrı uygulanır, reddedilen
önerinin ham içeriği istemciye gönderilmez.

Decision 5: Yanıt `transcript_public_id`, `source_text_sha256`, `original_text`,
`suggested_text`, `status` (`unchanged`, `suggested`, `rejected`),
`edits` (`start_char`, `end_char`, `original`, `replacement`), `rejected_count`,
`model_name`, `model_digest` ve `policy_version` içerir. Karakter ofsetleri
Unicode kod noktalarıdır; kaynak ses zamanı veya sözcük hizası üretilmez.
İlk politika `tr-context-words-v1`; model değişimi deneyde ayrı kimliktir.
Model çalışırken DB işlemi/kilit açık tutulmaz; cevap öncesi tenant, kaynak
sonuç ve bağlam karması yeniden kontrol edilir. Değişmiş kaynak 409
`transcript_changed`, silinmiş kaynak 404 üretir. Yanıt `Cache-Control:no-store`.

Decision 6: Mevcut yerel Ollama HTTP sağlayıcısı kullanılacak; yeni paket,
model indirme, bulut servis veya otomatik başka modele geçiş yok. Operatör
tarafından belirlenen model adı/digest çağrı öncesi ve sonrası doğrulanır;
uzak modele yönlendirme işaretli model reddedilir. HTTP yönlendirmeleri,
proxy ortamı, araç çağrıları ve sınırsız cevaplar kapalıdır. JSON şema,
`stream:false`, `think:false`, sabit örnekleme ve küçük üretim bütçesi kullanılır.
`keep_alive:0` her cevap sonunda dil modelinin bellekte bekletilmesini önler;
RTX 4060'taki sonraki ses işi için GPU/bellek bırakılır. İlk geliştirme deneyinin
beş dakikalık sıcak model ayarı ayrı deney kimliğiyle korunur; son kullanımda
yükleme maliyeti ayrıca ölçülür. Eşzamanlı ağır ses ve metin işlerinin bütün
cihazlarda sorunsuz çalıştığı bu ayardan çıkarılmaz.
Kaynak metin, model cevabı, sırlar veya gelişigüzel hata içeriği loglanmaz.

Decision 7: Özellik varsayılan kapalıdır. Tipli ayarlar:
`text_review_enabled`, `text_review_url`, `text_review_model`,
`text_review_model_digest`; açık mod geçerli sabit model digest gerektirir.
Ollama tarafı önceden kurulmuş olmalıdır. Uygulama en çok 100 saniyede güvenli
yanıt/hata döndürür; aradaki halka açık proxy bu uç için en az 110 saniye
bekler, mevcut 120 saniyelik istemci sınırı korunur. Model veya
bağlantı hatası ham transkripti engellemez. Başlangıç/kurulum yardımcısı
yalnız mevcut modeli doğrular ve yerel ayarları sırları göstermeden günceller.

Decision 8: Yerel Docker erişimi mevcut kapalı Spark köprüsü örneğiyle
kurulur: yalnız nginx'in mevcut host-facing ağı, özel yayımlanmamış dinleyici,
yerel host-gateway ve yalnız gerekli Ollama uçları. İş/veri servislerine genel
internet erişimi açılmaz; Ollama'nın localhost dinlemesi veya Windows güvenlik
ayarları değiştirilmez. Kümede isteğe bağlı, aynı namespace içindeki açıkça
etiketlenmiş kurum içi model servisinin belirli portuna NetworkPolicy verilir;
ayrı Ollama kurulumu mevcut dış hizmet önkoşuludur, yeni image/dependency yoktur.

Decision 9: UI tek aktif inceleme paneli/isteği tutar; toplantı, sayfa, kullanıcı,
tenant değişimi veya kapanışta iptal eder. Geç cevap başka metne uygulanmaz;
yanıt kimliği ve orijinal metin kontrol edilir. Modelden gelen metin HTML olarak
çalıştırılmaz. Geliştirme modundaki React StrictMode kurulum/temizleme tekrarı
aynı seçimin gereksiz ikinci model çağrısını başlatmamalıdır; iptal edilen
kurulumun gönderimi başlamadan durdurulur. Kaynak sesi dinleme 011'in orijinal
aralıklarını kullanır. Tarayıcı iptali, başlamış sunucu hesaplamasının anında
durduğunu garanti etmez; sunucu süresi ayrıca sınırlıdır.

## Gereksinimler ve kabul

Requirement 1: Domain öneri doğrulaması, gerçek HTTP Ollama adaptörü, kısa DB
okumalı hizmet ve tenant/izin korumalı API birlikte test edilir. Temiz metin,
anlamsal küçük hata, sayı/isim/olumsuzluk, tekrarlanan ifade, Unicode, enjeksiyon,
bozuk JSON, limit, timeout ve model kimliği değişimi kapsanır.

Requirement 2: Üretilmiş OpenAPI ve frontend tipleri, TR/EN sonuç paneli,
klavye/iptal/tek panel ve kalıcı tarayıcı senaryosu birlikte teslim edilir.
Giriş/normal rol HTTP ve gerçek modelle kaynak/değişmezlik gözlenir.

Requirement 3: Önce sabit kontrollü Türkçe hatalı/temiz/korumalı örnekler,
ardından mevcut gerçek ASR çıktılarında eşlenmiş deney yapılır. Ham ve önerilmiş
kelime hata oranı, doğru metni bozma oranı, düzeltme isabeti, kapsama ve süre
ayrı hesaplanır. Otomatik/human olmayan referans etiketi korunur; gerçek sesi
dinlemeden model tercihi insan doğrusu sayılmaz. Öğrenilmiş ayarların seçildiği
veri kör test olarak sunulmaz. Her gerçek model deneyi `results.md` ve hash
bağlı ayrıntılı rapora kaydedilir; başarısız/boş sonuçlar paydadan çıkarılmaz.

Requirement 4: Tam `scripts/quality-gate.sh all`, ayar senkronizasyonu,
chart/yerel köprü kontrolleri ve güvenlik kapısı gerçek çıktısıyla raporlanır.
Gözlenmeyen cihaz, güvenlik aracı veya kullanıcı kabulü başarılı sayılmaz.

## Katmanlar, yaşam döngüsü ve gözlemlenebilirlik

Şema/migration N/A — geçici hesaplama sonucu saklanmaz; ham tabloya yazılmaz.
Önbellek N/A — sonuç saklanmaz, no-store ve UI yaşam süresiyle sınırlıdır.
Worker N/A — yalnız sınırlı, isteğe bağlı önizleme; ASR/kimlik worker'ı değişmez.
Model/embedding N/A — mevcut biyometrik modeller ve eşikleri değişmez; seçilmiş
yerel metin modeli ayrı sağlayıcı kimliğidir. Kalıcı insan düzeltmesi yeni kabul
gerektirir; mevcut preview onay/kayıt iş akışını varsaymaz.
Gözlemlenebilirlik mevcut rota/status/süre ile sınırlı; model metni loglanmaz.
Dağıtım ve Secret ayarları mevcut tek Secret sınırından verilir.

- [x] Tipli yerel model/alan sınırları ve kaynak değişmezliği testli; [arka uç kanıtı](../../../../docs/evidence/2026-09-13-contextual-transcript-review/backend.md).
- [x] Gerçek Qwen3.5 27B kontrol/gerçek veri deneyleri ve `results.md` kaydı mevcut; [model raporu](../../../../docs/evidence/2026-09-13-contextual-transcript-review/model-report.md). Gerçek örneklerde kelime hatası azalmadı.
- [x] TR/EN uygulama akışı, sözleşmeler, senaryo ve belgeler mevcut; [tarayıcı kanıtı ve gözlenmeyen dallar](../../../../docs/evidence/2026-09-13-contextual-transcript-review/browser-report.md).
- [x] Yerel bağlantı ve profil/güvenlik kontrolleri gerçek kanıtla raporlu; [967 testlik son kapı](../../../../docs/evidence/2026-09-13-contextual-transcript-review/quality-handoff-report.md). Güvenlik kapısının eksik araçta durması başarı sayılmadı.
