# PRD — Model seçimi ve kullanıcı tarafından kaydedilen düzeltmeler

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [013](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kabul: Kullanıcı 13 Eylül 2026'da kurulu diğer dil modellerini seçmeyi,
modelin düzeltmelerini her koşulda yeşil yazıyla metin üzerinde görmeyi ve
isterse düzeltilmiş hali kaydetmeyi açıkça istedi. Bekleyen commit/push
talimatı bu ek yeteneğin tamamlanmasıyla birlikte uygulanır.

## Amaç, kapsam ve önceki davranış

Toplantı okuyup analiz çalıştırabilen kullanıcı kurulu yerel dil modelini
seçer, bütün model önerilerini görür ve açık bir kaydetme eylemiyle yeni
bir metin sürümü oluşturur. 012'nin özgün ASR kaydı değişmez. Bu PRD,
012'nin kullanıcı ekranındaki yalnız filtrelenmiş/geçici öneri davranışını
genişletir; eski gövdesiz önizleme API'si ve eski deney politikası korunur.
Yeni kayıtlar eski doğruluk sonuçlarına sonradan katılmaz.

## Kararlar

Decision 1: Panel açılınca kurulu model listesi alınır; model seçimi tek
başına hesaplama başlatmaz. Açık “Kontrol et” eylemi yalnız bir istek gönderir.
Liste yalnız mevcut yerel Ollama uç noktasından gelir; model indirme, yeni
sunucu adresi, bulut modeli veya otomatik model değiştirme yapılmaz. Mevcut
ayarların sabit varsayılan modeli listede işaretlenir; alternatif model
kurulu ve yerel olmalıdır. Listeden seçilen tam ad ve digest çağrı öncesi ve
sonrasında tekrar doğrulanır. Embedding-only/uzak modeller kullanılamaz.

Decision 2: `GET /meetings/review-models` en çok 100 kurulu kayıt döndürür:
`items[{name,digest,size_bytes,selectable,unavailable_reason,is_default}]`.
`unavailable_reason` sınırlı kod veya null'dır. Liste okuma ve çalıştırma
izinlerinin ikisini gerektirir; model yolu veya gizli metadata döndürmez.
Yerel capability doğrulaması `/api/show` kullanır; liste ve doğrulama
sınırlı süre/yanıt büyüklüğündedir. Boş/hazır olmayan liste açıklanır.

Decision 3: Yeni `POST /meetings/{public_id}/transcript/{transcript_id}/correction-suggestion`
gövdesi yalnız `model_name` ve `model_digest` içerir. Hedef ve en fazla
üçer komşu satır sunucuda, aynı tenant'ın tamamlanmış ve silinmemiş
toplantısından seçilir; 012'nin 1024/4000 karakter ve 100 saniye sınırları
korunur. İstemci kaynak metin veya model adresi göndermez. Kaynak ve güncel
izinler modelden sonra tekrar denetlenir; ağ çağrısında DB işlemi açık tutulmaz.
Kamu proxy'si her iki önizleme yolunu en az 110 saniye bekler.

Decision 4: Yeni politika `tr-context-words-v2` bütün yapısal olarak geçerli
`original`/`replacement` önerilerini gösterir. 012'nin sayı, isim, olumsuzluk
ve yazım mesafesi gibi anlamsal kontrolleri öneriyi gizlemez; yalnız inceleme
işareti olur. Modelin düz metin yanıtı, JSON çözümlenemediğinde de en çok
8192 karakterle gösterilebilir; araç çağrısı, eksik/yanlış model kimliği ve
ulaşmayan cevap düzeltme sayılmaz. Yanıt kesilmişse açık durum belirtilir,
kesilmiş ham cevap kaydedilemez. Model metni hiçbir zaman HTML çalıştırmaz.
Üretim isteği 012'nin en fazla üç, alan başına 64 karakterlik küçük düzenleme
şemasını kullanır; bu biçime uymayan içerik ham yanıt olarak görünür fakat
kaynak üzerinde bir düzenleme olarak uydurulmaz.

Decision 5: Her öneri `original`, `replacement`, nullable `start_char/end_char`,
`assessment` (`checked`, `review_required`, `unmapped`) ve sınırlı neden
kodunu içerir. Ofsetler Unicode kod noktalarıdır. Özgün metinde tekil ve
örtüşmesiz eşlenebilen düzenlemeler düzeltilmiş cümlede yeşil ve altı çizili
görünür. Tekrarlı, bulunamayan veya çakışan öneriler konum uydurulmadan
ayrı model önerisi alanında yine gösterilir. Renk tek anlam taşıyıcısı değildir.
Özgün kelimeyi karşılaştırmak için görünür eski→yeni listesi bulunur.

Decision 6: Yeni öneri yanıtı `transcript_public_id`, `source_text_sha256`,
`original_text`, `suggested_text`, `proposals`, `model_output`,
`model_output_truncated`, `status` (`unchanged`, `suggested`, `unmapped`,
`invalid_output`), `model_name`, `model_digest`, `policy_version`,
`expected_revision`, nullable `save_token` ve nullable `expires_at` içerir.
Kaydetme yalnız en az bir değişiklik ve bütün önerilerin tam eşlendiği
durumda mümkündür; anlamsal inceleme işareti kullanıcı kaydını engellemez.
Ham kaynak her durumda korunur. Yanıt `Cache-Control: no-store` taşır.

Decision 7: `POST /meetings/{public_id}/transcript/{transcript_id}/corrections`
yalnız `save_token` alır. Token sunucunun imzaladığı, 15 dakika ömürlü,
aktör/tenant/toplantı/satır, bağlam/source hash, beklenen sürüm, model
kimliği, tam öneri ve tekil önizleme kimliğiyle bağlı kanıttır. İmzalama
mevcut uygulama sırrından amaç ayrımıyla türetilir; oturum açma tokeni
olarak kullanılamaz. Token/metin loglanmaz. Serbest istemci metni,
değiştirilmiş kanıt veya başka kaynağın önerisi kaydedilmez.

Decision 8: Kaydetme güncel okuma/çalıştırma yetkilerini, tenant'ı, kaynağın
yaşam döngüsünü, orijinal bağlam hash'ini ve beklenen düzeltme sürümünü
yeniden doğrular. Kısa kilitli DB işlemi aynı satırdaki yarışları sıralar.
Aynı önizleme kimliğiyle tekrar aynı kaydı döndürür; farklı eski öneri
409 `correction_conflict` üretir, otomatik üzerine yazmaz. Kaynak değişimi
409, bulunmayan/silinmiş kaynak 404, geçersiz veya süresi dolmuş token
422 üretir. Kullanıcı işlem sonucunu görüp yeni inceleme başlatabilir.

Decision 9: `MeetingTranscriptRevision` kaynak satırından ayrı ve eklemeli
bir tablodur. Standart kimlik, tenant, audit, props, soft-delete ve aktif
indeks bloğu kullanılır. Kaynak satırına tenant/toplantı/satır birleşik
FK ile bağlanır; sürüm numarası ve önizleme kimliği benzersizdir. Sınırlı
düzeltilmiş metin, kaynak/bağlam hash'i, düzenlemeler, model adı/digest,
politika ve kaydeden aktör tutulur. Kaynak `MeetingTranscript.text`,
konuşmacı, zamanlar, embedding ve ses hafızasına yazılmaz. Yeni sürüm
eski onaylı sürümü silmez; mevcut saklama/soft-delete temizliği sürüm
metinlerini de kaynakla birlikte erişilmezleştirir ve mevcut scrub sınırında
temizler. Ham model cevabı ve imzalı token kalıcı tabloda tutulmaz.

Decision 10: Mevcut transcript DTO'sunda `text` özgün kalır; ek
`correction` alanı nullable en son geçerli kaydı döndürür:
`public_id,revision,corrected_text,source_text_sha256,edits,model_name,model_digest,policy_version,saved_at`.
Kaydetme aynı kaydın DTO'sunu döndürür. Ekran kaydedilmiş sürümü yeşil
işaretlerle gösterir; “Orijinal / Düzeltilmiş” geçişi vardır. Sayfa yenilense
de kayıt görünür. Yeniden model incelemesi özgün kaynak üzerinde yapılır;
önceki kullanıcı kaydı sessizce yeni modele doğruluk referansı verilmez.

Decision 11: Model/satır/toplantı/tenant/kullanıcı değişiminde eski panel
yanıtı ve kaydetme kanıtı kullanılamaz. İstek/yanıt kaynak, seçilmiş model
ve sürümle bağlanır. Kaydetme sürerken tekrarlı tıklama engellenir; ağ
yanıtı kaybolursa aynı tokenla tekrar idempotenttir. Başlamış sunucu
işleminin tarayıcı kapanınca durduğu iddia edilmez. TR/EN, klavye ve
dar ekran davranışı birlikte teslim edilir. Okuma yetkisi olan kişi
kaydedilmiş metni görebilir; model/inceleme/kaydetme iki izni de gerektirir.

## Gereksinimler ve doğrulama

Requirement 1: Kırmızı/yeşil domain ve adapter testleri bütün önerilerin
görünürlüğünü, Unicode/HTML/metin eşleme/bozuk JSON sınırlarını, gerçek
kurulu model seçimini ve digest değişiminde kapalı davranışı kapsar.

Requirement 2: Gerçek PostgreSQL/API testleri ilk kayıt, tekrar, eşzamanlı
çatışma, yeni sürüm, özgün kaynak değişmezliği, normal roller, tenant,
token süresi/imzası, silinmiş kaynak ve retention scrub davranışını kapsar.
SQLAlchemy authority, `scripts/db.sh generate` ile üretilip incelenmiş
eklemeli migration, yerel apply/validate/status ve tam kapı birlikte yapılır.

Requirement 3: Model seçimi, yeşil kelimeler, filtreden geçmeyen öneriler,
kaydetme/yeniden açma ve özgün metne geçiş gerçek uygulamada test edilir.
Kurulu model sayısı neyse raporlanır; olmayan ikinci modele geçiş uydurulmaz.
Gerekirse yalnız ayrı test toplantısında kullanıcı onay akışı denenir.

Requirement 4: Yeni gerçek model denemeleri ayrı `results.md` kaydı olur.
012'nin filtreli sonuçları ve yeni görünür/human-approved çıktıları aynı
metrik sayılmaz. Doğruluk iddiası referanslı ölçüm olmadan yapılmaz.
Tam profil kapısı, mevcut güvenlik aracı eksikliği ve bütün gözlenmeyen
senaryo/ortamlar sabit rapor biçiminde sunulur; ardından commit ve GitHub
push yapılır, uzaktaki commit doğrulanır.

## Katmanlar ve etkiler

Şema: eklemeli tablo ve birleşik kaynak anahtarı; migration release önce,
uyumlu okuyucu/yazıcılar sonra. Geriye dönük DTO alanı nullable/default'tur.
Worker: mevcut retention scrub revizyonları da kapsar; model işi HTTP
üzerinden sınırlı isteğe bağlı çağrı olarak kalır, yeni görev kuyruğu yoktur.
Önbellek N/A — model listesi ve öneriler kısa HTTP isteğidir, no-store kullanır.
Yeni bağımlılık/ayar/Secret N/A — mevcut yerel sağlayıcı ve uygulama sırrı
kullanılır; backend dış ağa çıkışı açılmaz. Biyometrik model N/A — ses
kimliği veya konuşmacı hafızası değişmez. Gözlemlenebilirlik mevcut
rota/status/süre ve sınırlı hata kodlarıdır; model ve kullanıcı metni hariçtir.

- [x] Kurulu model seçimi ve tüm önerilerin görünürlüğü testli.
- [x] Onaylı sürüm saklama, tenant/yetki/kaynak/yarış/retention testli.
- [x] TR/EN yeşil değişiklik ve kayıt/özgün görünüm akışı canlı gözlendi; dar görsel yakalama ve doğrudan headless yürütüm eksikleri [tarayıcı raporunda](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/browser-report.md).
- [x] Model deneyleri, migration ve kalite/güvenlik kanıtları [teslim raporunda](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/README.md); 1.084 test başarılı, güvenlik aracı eksikliği açık.
- [ ] Kullanıcının istediği commit ve push uzaktan doğrulandı.
