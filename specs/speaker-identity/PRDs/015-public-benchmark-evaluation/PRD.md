# PRD — Kamuya açık kıyaslarla doğruluk ölçümü

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [015 — public-benchmark-evaluation](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (29 Ekim 2026): Kullanıcı, insan denetimli Türkçe toplantı seti beklenmeden
doğruluk geliştirmeye devam etmeyi ve işe ölçüm altyapısı ile katılımcı listesinden
başlamayı seçti.
Kabul (29 Ekim 2026): Kullanıcı 015, 016 ve 017 taslaklarını kabul etti ve 015 ile başlanmasını istedi.

## Amaç ve kapsam

Her doğruluk değişikliği aynı dondurulmuş protokolde önce/sonra ölçülür. Dilden büyük
ölçüde bağımsız bileşenler — konuşmacı ayırma, parçalar arası birleştirme ve toplantılar
arası kimlik — insan etiketli gerçek toplantılarla; Türkçe metin ise depodaki insan
transkriptli Türkçe kohortlarla ölçülür. Taban çizgisi bugünkü sistemdir. Bu yetenek
model, eşik veya ürün davranışı değiştirmez; yalnız ölçüm ve bir salt okunur API ekler.

## Kararlar

Decision 1: Kıyas kümeleri ve rolleri:

| Küme | Kullanım | Lisans / not |
| --- | --- | --- |
| AMI toplantı korpusu, resmî dev + test bölümleri (34 toplantı, 37 kişi) | Ayırma (DER/JER), toplantılar arası kimlik, yanlış kabul | Ses CC BY 4.0; referans RTTM/UEM `pyannote/AMI-diarization-setup` `only_words` (elle etiket 1.6.2), sabit commit; deponun lisansı edinimden önce kaydedilir |
| 010 FLEURS (743) ve MediaSpeech (2.433) dondurulmuş Türkçe kohortları | Türkçe WER regresyonu | Mevcut kaynak ve hash'ler değişmez |
| Mevcut LibriSpeech galeri protokolü | 5/10/20/50 galeri ölçeği | CC BY 4.0; okunmuş İngilizce |
| DAI-ASR-I18N Türkçe (isteğe bağlı) | Türkçe iki kişilik WER/cpWER/DER | Erişim ve sözleşme hukuk incelemesinden sonra; sözleşme kimlik testini yasaklar |

VoxCeleb, resmî indirme sayfasının araştırma amacı sınırı nedeniyle ticari ürün
değerlendirmesine alınmaz.

Decision 2: AMI iki ses koşulunda koşulur: Mix-Headset (yakın) ve Array1-01 (tek uzak
mikrofon, ürünün masaüstü kaydına yakın). Toplantılar `language=en` ile gönderilir;
AMI sonucu Türkçe başarı iddiası değildir ve AMI metin skoru raporlanmaz.

Decision 3: Ölçütler: DER ve JER (collar 0 ve 0,25 s, örtüşme dahil, UEM içinde);
toplantılar arası doğru tanıma, yanlış kişi kabulü, galeri dışı kişide yanlış kabul
(FPIR), gereksiz yeni profil ve kayıt kapsamı ayrı alanlardır; Türkçe WER mevcut
`turkish-words-v1` normalizasyonudur. Belirsizlik toplantı ve konuşmacı kümeli
bootstrap ile verilir; aynı kişinin tekrarlı aramaları bağımsız örnek sayılmaz.

Decision 4: AMI kimlik protokolü `voiceup-ami-public-benchmark-v1`: ortak kişisi olan
toplantılar aynı bileşende toplanır; böylece bileşenler kişi bakımından ayrıktır (yedi
bileşen: altısı 4 toplantı ve 4 kişi, biri 10 toplantı ve 13 kişi). Bileşenler ad
sırasıyla dönüşümlü iki yarıya ayrılır. Galeri yarısındaki toplantılar önce, ürünün
mevcut otomatik hafıza akışı açıkken sırayla işlenir; bir kişinin ilk göründüğü
toplantı kayıt, sonrakiler tanıma denemesidir. Diğer yarının bütün toplantıları
otomatik hafıza kapalıyken galeri dışıdır ve tanınan her kişi yanlış kabuldür. Yarılar
yer değiştirilerek ikinci koşum yapılır (rotasyon 1: 16 galeri ve 18 galeri dışı
toplantı; rotasyon 2: tersi). Referans kişi etiketleri yalnız değerlendiricide kalır;
ürüne yalnız karışık ses ve isteğe bağlı sayı ipucu verilir. (29 Ekim 2026'da uygulama
sırasında düzeltildi: sabit commit'teki gerçek bölümler 34 toplantıdır ve bazı kişiler
birden çok grupta bulunduğundan grup yerine kişi bileşeni kullanılır.)

Decision 5: Hipotez, ürünün gerçek HTTP akışından alınır. Transkript satırları
1,5 saniyeye kadar boşlukları birleştirdiği için DER'e uygun değildir; bu nedenle salt
okunur `GET /meetings/{public_id}/speaker-turns` eklenir. Yanıt, toplantı konuşmacısı
`public_id`, başlangıç ve bitiş zamanından oluşan sayfalı turlardır; ses, vektör veya
iç kimlik içermez. Bugün parça checkpoint'i modelin ham turlarını saklar, yerel
etiketin toplantı konuşmacısına eşlemesini ise yalnız bekleyen sınır turları için
tutar. Bu nedenle worker, her parçada kesinleşen ve önceki kesinleşme noktasından bu
parçanınkine kırpılmış turları checkpoint'e `speaker_turns` olarak ekler; şema
değişmez. Bu alanı taşımayan eski toplantılar için uç nokta tipli
`speaker_turns_unavailable` hatası döndürür.

Decision 6: Puanlama, kabul edilmiş `pyannote-audio` 4.0.7'nin bağımlılığı olarak
kök `diarization` ekinde ve meeting kilidinde zaten bulunan `pyannote-metrics` 4.1
ile yapılır. Başka bir puanlama paketi gerekirse `dependency-admission.json` ile
ayrıca kabul edilir.

Decision 7: Her koşum `results.md` içine `scripts/record-experiment.py` ile; çalışma
profili (`x86_64-cu126` veya `x86_64-cu128`), model kimlikleri, protokol sürümü ve
paydalar ile kaydedilir. Farklı profillerdeki sonuçlar tek seride birleştirilmez.

## Gereksinimler

Requirement 1: `scripts/prepare-ami-evaluation.py` yalnız dev/test toplantılarının iki
ses koşulunu ve RTTM/UEM dosyalarını sabit URL, boyut ve SHA-256 manifestiyle indirir,
doğrular ve 16 kHz mono WAV'a dönüştürür; ham veri Git dışında `data/` altında kalır.
Tekrar çalıştırma doğrulanmış dosyaları yeniden kullanır.

Requirement 2: `speaker-turns` uç noktası `meeting_analysis:read` ister, tenant
kapsamında `public_id` çözer, deterministik sıralama ve sayfalama metadatası döndürür;
silinmiş veya tamamlanmamış toplantıda tipli hata verir. OpenAPI ve frontend tipleri
yeniden üretilir; arayüz değişmez.

Requirement 3: `scripts/run-ami-evaluation.py` ayrılmış deney tenant'ında Decision 4
sırasını uygular, kesintiden devam eder, özel checkpoint tutar ve yalnız toplam
ölçütleri yayımlar.

Requirement 4: Taban çizgisi: AMI iki ses koşulu ve iki rotasyon; Türkçe FLEURS ve
MediaSpeech kohortlarının bu bilgisayarın çalışma profilinde yeniden koşumu.

## Güvenlik, veri ve katmanlar

Deney tenant'ı gerçek kullanıcı profilleriyle karışmaz. Ham ses, transkript, kişi
eşlemesi ve vektörler log, rapor veya Git'e girmez. Şema ve migration: N/A — yeni
tablo yok. Vektör sözleşmesi: N/A — model, boyut ve eşik değişmez. UI: N/A.
Worker/önbellek: N/A. Gözlemlenebilirlik: mevcut istek logları; yeni metrik yok.
Kubernetes: N/A — yerel değerlendirme.

## Kabul ölçütleri

- [ ] Hazırlayıcı manifest doğrulaması ve bozuk/eksik dosya reddi testleri geçer.
- [ ] `speaker-turns` API, RBAC, tenant yalıtımı, sayfalama ve hata testleri geçer; OpenAPI/tip sapması yok.
- [ ] AMI iki ses koşulu ve iki rotasyonla taban çizgisi `results.md` içinde güven aralıklarıyla kayıtlıdır.
- [ ] Türkçe kohortların bu çalışma profilindeki taban çizgisi kayıtlıdır.
- [ ] Tam profil kalite kapısı geçer.

Open Question 1 (kapandı, 29 Ekim 2026): `pyannote/AMI-diarization-setup` deposu
Apache-2.0 lisanslıdır; sabit commit `67c2d539286e89f68952d5dcf83912bd9f01dfae`.
RTTM konuşmacı etiketleri küresel AMI katılımcı kodlarıdır ve toplantılar arasında
sabittir. AMI ses dosyaları için yayıncı hash'i yoktur; boyut ve SHA-256 ilk edinimde
manifeste yazılır ve sonraki koşumlarda doğrulanır.
