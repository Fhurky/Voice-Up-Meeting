# PRD — Canlı konuşmacı analizi

Status: Draft

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [003 — live-speaker-analysis](../../roadmap.md)
Tarih: 9 Eylül 2026. Bağımlılık: 002 uzun kayıt ve toplantı boyunca kimlik sürekliliği.
Mimari gerekçe: [karar belgesi](../../../../docs/LONG_RECORDING_STRATEGY.md).
Bu yetenek henüz uygulanmadı; öncelik 001 doğruluk deneyi ve ardından 002'dir.

## Amaç, aktör ve kapsam

Yetkili kullanıcı gelen ses sürerken geçici konuşmacı bilgisini görür; yeni kanıtla
sonuç düzelir, oturum sonunda son zaman çizelgesi üretilir. Toplantı platformu
bağlantısının hangi API/izinle yapılacağı bu ses motorundan ayrı kapsamdır.

Decision 1: Uzun kayıt hattının kişi deposu, zaman çizelgesi ve sürümlü sonuçları
kullanılır. Batch modelin hızlı çalışması tek başına canlı doğruluk kanıtı değildir.

Decision 2: İlk deney 10–30 saniye kayan bağlam, 2–5 saniyede ara güncelleme,
3–8 saniye temiz konuşma kanıtıdır. Ön kimlik için 5–15 saniye ölçüm hedefi vardır;
kesin gecikme veya her söze kimlik verme garantisi değildir. Dört kişiyle sınırlı
bir akış checkpoint'i onlarca kişilik ana çözüm sayılmaz.

Requirement 1: Ses parçaları oturum/sıra/kaynak zamanı ve hash ile alınır; yinelenen,
geç gelen ve kaybolan parçalar belirgin davranışa sahip olur. Ağdan yeniden bağlanma
kişileri sıfırlamaz; bellekteki tamponun üst sınırı vardır.

Requirement 2: Geçici/son sonuç, düzeltme sürümü ve belirsizlik görünür olur. İki
kişinin aynı anda konuşması tek isme zorlanmaz; ara yanlış karar profil güncellemez.

Requirement 3: HTTP aktarım ve Server-Sent Events (SSE) ilk web tasarımıdır. Son
kaynak/codec/protokol, kuyruk doluluğu ve backpressure kuralları uygulama öncesi
kesinleşir. JWT/tenant/izin, kaynak saklama ve silme kuralları her oturumda sürer.

Requirement 4: Model/cihaz kaydı, sonuca kadar gecikme, düzeltme oranı, RAM/VRAM ve
ses kaybı ölçülür. Compose/Helm ağ ve uzun bağlantı ayarları birlikte güncellenir;
ses/embedding/sırlar loglanmaz. ASR N/A — bu yetenek yalnız konuşmacı kimliğidir.

- [ ] Kopma/tekrar/geç gelme/oturum kapatma testleri ve sınırlı bellek kanıtı vardır.
- [ ] Gerçek 4060 akışında gecikme ve kalite birlikte ölçülür; Spark ayrıca doğrulanır.
- [ ] Kayıtlı kişi sayısı, oturumdaki kişi sayısı ve örtüşme ayrı sonuçlandırılır.
- [ ] Aynı sesin çevrimdışı son geçişiyle canlı/son karar farkları raporlanır.
- [ ] Gerçek browser/API ve tenant/izin/migrasyon/deployment kontrolleri geçer.

Open Question 1: Türkçe çok konuşmacılı testten sonra model ve sayısal gecikme/kalite eşiği.
Open Question 2: Ses kaynağı, parçaların teslim garantileri ve tampon dolduğundaki kullanıcı akışı.
