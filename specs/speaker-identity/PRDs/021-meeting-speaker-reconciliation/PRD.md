# PRD — Toplantı sonunda konuşmacı birleştirme

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [021 — meeting-speaker-reconciliation](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (30 Ekim 2026): [015](../015-public-benchmark-evaluation/PRD.md) AMI taban çizgisi,
collar 0 konuşmacı ayırma hata oranını (DER) yanlış kişi olmadan ama modelin yayımlanmış
değerinin iki katından fazla ölçtü. Kabul edilirse [002](../002-long-recording-analysis/PRD.md)
parça eşleştirmesinin sonucu toplantı bitiminde yeniden hesaplanır; 015 protokolü, 016 katılımcı
listesi ve kimlik kararları korunur.
Kabul (30 Ekim 2026): Kullanıcı taslağı kabul etti ve Open Question 1'de parça izi kümelemeyi seçti.

## Amaç ve önceki durum

Uygulama sesi 5 dakikalık parçalarda işler. `meeting_chunks.py`, her parçadaki yerel konuşmacıyı
kayıtlı profil eşiğiyle (`speaker_match_threshold` 0,55, `speaker_match_margin` 0,10) önceki
toplantı konuşmacılarına bağlar; eşleşmezse yeni konuşmacı açar. Bir kişinin kopyası oluştuğunda
sonraki parçada iki aday birbirine yakın çıkar, fark şartı tutmaz ve yeni kopya açılır. Toplantı
sonunda bunları birleştiren adım yoktur.

Ölçülen sonuç: 4 kişilik AMI toplantılarında 7–95 konuşmacı. Aynı dönüşler 5 dakikalık pencereler
içinde ayrı puanlanınca kişi karışması array1'de %29,94'ten %13,28'e, headset'te %26,50'den
%9,14'e düşer. Hedef: aynı kişiyi toplantı boyunca tek konuşmacıda toplamak, kimlikte yanlış kişi
üretmemek.

Çevrimdışı tekrar oynatma kanıtı (saklı parça sonuçları, GPU yok, 34 toplantı; uygulamanın ölçülen
DER'ini yarım puan içinde yeniden üretir: array1 %44,09/ölçülen %44,57, headset %39,05/%39,49):

| Yöntem | array1 DER | headset DER | 30 sn+ konuşmacı (ortanca, array1/headset) | %80 altı saflık (array1/headset) |
|---|---|---|---|---|
| Bugünkü davranış | %44,09 | %39,05 | 7 / 8 | 29/281, 21/267 |
| Parça içinde fark şartı kalkar, eşik 0,65 | %35,53 | %29,32 | ölçülmedi | ölçülmedi |
| Toplantı sonunda satır birleştirme, eşik 0,5 | %33,19 | %27,33 | 6 / 5 | 37/220, 19/191 |
| Parça izi kümeleme, aynı parçadaki iz hiç birleşmez, eşik 0,4 | %29,12 | %22,89 | 6 / 4 | 47/214, 26/174 |
| Parça izi kümeleme, yalnız zamanda çakışan iz birleşmez, eşik 0,6 | %25,88 | %21,21 | 4 / 4 | 16/160, [görevlerde](tasks.md) |

Canlı kural aynı parçadaki benzer ve çakışmayan izleri zaten birleştirir; Community-1 5 dakikalık
parçada bir kişiyi bölebildiği için aynı parçadaki izleri tümden ayırmak kopya bırakır. Kısıtın
gevşetilmesi uygulama sırasında bulundu ve Decision 2'ye yazıldı. Eşik yükseldikçe DER biraz artar,
karışık küme azalır; bu yüzden eşik seçimi ve kimlik koruması Decision 3 ve 5'e bağlıdır. Bu tablo
tekrar oynatmadır, ürün ölçümü değildir.

## Kararlar

Decision 1: Birleştirme, son parça kaydedilip toplantı `finalizing` durumuna geçtikten sonra ve
kimlik hafızası çalışmadan önce bir kez yapılır. Çevrimiçi eşik değişikliği tek başına yetmez
(tablo). Çalışma süresindeki `provisional` sonuçlar aynı kalır.

Decision 2: Yöntem, parça izi düzeyinde kısıtlı aşağıdan yukarı kümelemedir: her parçanın yerel
izi 256 boyutlu izleme vektörüyle, kendi konuşma süresiyle ağırlıklı girer; en yüksek benzerlikli
çift birleşir. Aynı parçada zamanda çakışan veya bağımsız ECAPA kanıtı (`separation_score`) farklı
ses diyen iki iz asla aynı kümeye girmez. Önce 10 saniye ve üzeri izler, sonra kısa izler
kümelenir. Vektörü olmayan iz ayrı kalır. Yeni model, bağımlılık veya GPU işi yoktur.

Decision 3: Eşik `meeting_reconciliation_threshold` ayarıdır; değeri 0,6'dır. Yalnız 18 AMI dev
toplantısının DER'iyle, 0,40–0,70 arası seçilir: iki ses koşulunda da en iyi değerin 1,0 puan içinde
kalan en yüksek eşik (saflığı korur). Taslaktaki 0,5 puanlık tolerans 0,5 eşiğini seçiyordu; ızgara
görüldükten sonra 1,0 puana çıkarıldı, çünkü 0,6 dev DER'ini en çok 0,90 puan artırırken 34
toplantıdaki karışık küme payını array1'de 31/179'dan 16/160'a indirir ve yanlış kişi kabul
ölçütünün önceliği vardır. 16 test toplantısının DER'i seçimde kullanılmaz, yalnız raporlanır. Kişi sayısı girdisi
kümelemeyi zorlamaz: sayıyı tutturmak için farklı sesler birleştirilmez (mevcut kural ve
`test_different_tracking_voice_does_not_merge_to_meet_the_input_count`; kabulden sonra uygulama
sırasında bulunup taslaktaki sayı kuralının yerine yazıldı).

Decision 4: Sonuç, saklı parça sonuçlarından yeniden kurulur: mevcut `persist` mantığı parça
sırasıyla, kümelemenin verdiği kimlikle yeniden çalıştırılır. Böylece metin satırları,
`speaker_turns`, temiz aralıklar ve merkezler tek kod yolundan çıkar. Fiziksel silme yoktur:
konuşmacı satırları küme sırasıyla yeniden kullanılır (ekrandaki "Konuşmacı N" 1'den başlar),
artanlar ve eski metin satırları soft delete olur; `uq_meeting_speaker_ordinal` ve
`uq_meeting_transcript_ordinal` soft delete satırları da kapsadığı için metin sıra numaraları
devam eder. İşlem tek transaction ve çitlenmiş worker talebi altındadır, toplantı `props`
alanındaki sürüm işaretiyle bir kez uygulanır; kesilirse aynı sonucu yeniden üretir.

Decision 5: Kimlik koruması gevşemez. 10 saniye ve üzeri üyelerinden biri küme merkezine
`speaker_new_threshold` altında benzeyen küme `reconciliation_ambiguous` işaretlenir; işaretli küme
otomatik kaydedilmez ve profil eşleşmesi yapmaz. Eşikler, 016 listesi ve otomatik kayıt süresi değişmez. Bir konuşmacı 10 saniyeden az temiz konuşmayla
profile bağlanmaz (`MIN_RECOGNITION_SECONDS`): `eval-ami3-array1-r2`'deki 2 yanlış kişi 3 ve 5 saniyelik
konuşmacılardaydı; kural 30 Ekim 2026'da kullanıcı onayıyla eklendi.

Decision 6: Toplantı `succeeded` olmadan konuşmacı adlandırılamaz; `rename` 409
`meeting_not_ready` döner ve ön yüz düğmeyi gizler. Birleştirme adları kaybetmez, çünkü işlem
öncesinde ad yoktur. Eski tamamlanmış toplantılar değişmez; yeniden analiz yoktur.

Decision 7: Otomatik profil kaydı varsayılan olarak kapalıdır (`MeetingCreate.auto_enroll` ve form).
Kullanıcı isterse açar; kişi kaydının önerilen yolu 017 mikrofonla profil kaydıdır. Gerekçe:
`eval-ami4-array1-r2`'de kalan yanlış kişi, profilin başka kişinin baskın olduğu kümeden açılmasından
geliyor ve puan eşiğiyle çözülmüyor (30 Ekim 2026, kullanıcı kararı). Kabul ölçütündeki yanlış kişi
sınırı varsayılan akış için geçerlidir; seçenek açıldığında bu risk ekranda bildirilir.

## Gereksinimler

Requirement 1: Kümeleme `app/domain` içinde saf fonksiyondur; deterministiktir, aynı girdi aynı
sonucu verir, parça kısıtı her koşulda korunur (birim testleriyle). Requirement 1 için kırmızı
test önce yazılır: üç parçada aynı kişi tek konuşmacı olur.

Requirement 2: Worker adımı Decision 1 ve 4'e göre eklenir; gerçek PostgreSQL entegrasyon testi
yeniden kurulumu, tekrar denemeyi, kiracı yalıtımını, iptali ve kısmi hatada geri almayı kapsar.

Requirement 3: Ayar, tipli ayarlar, `.env.example`, Compose ve chart yüzeylerine eklenir;
`check-config-sync.py` geçer.

Requirement 4: Tekrar oynatma aracı testleriyle `scripts/` altına alınır; eşik seçimi görev
kanıtına, gerçek ölçümler `results.md`'ye işlenir.

Requirement 5: 015 protokolü yeni tenant'larda baştan koşulur: iki ses koşulu × iki rotasyon, ardından
016 listeli iki koşum. Önceki `eval-ami2-*` kayıtları karşılaştırma tabanı olarak kalır.

Requirement 6: `rename` kuralı için API testi, OpenAPI dışa aktarımı, ön yüz testi ve TR/EN metin
eklenir; toplantı sonuç senaryosu güncellenir.

## Katmanlar

Şema: N/A — mevcut `props` alanı kullanılır, göç yok. Vektör: N/A — yeni gömme veya sorgu yok;
mevcut izleme vektörleri kullanılır. Gözlemlenebilirlik: mevcut `meeting_chunk_attempt` kaydına
kişi verisi içermeyen `reconciliation` durumu ve süresi eklenir. Dağıtım: yalnız yeni ayar; sınırlı
CPU işi worker'da çalışır. Güvenlik: tenant ve yetki sınırları değişmez, ham vektör kaydedilmez.

## Kabul ölçütleri

- [ ] Birim, entegrasyon, ön yüz ve tam kalite kapısı geçer.
- [ ] Gerçek akışla 16 test toplantısında collar 0 DER array1 ≤ %30, headset ≤ %25 (bugün %43,52 ve %42,56).
- [ ] Dört taban koşumunda yanlış kişi 0 ve yanlış kabul 0 kalır; tanıma oranı iki ses koşulunda da düşmez.
- [ ] Toplantı başına 30 saniye ve üzeri konuşmacı sayısı raporlanır.
- [ ] Çalışan yığında uzun bir toplantı uçtan uca işlenir; sonuç ekranında birleşik konuşmacılar görülür.
- [ ] Kullanıcı gerçek bir Türkçe toplantıda sonucu kabul eder (L3).

Open Question 1 (kapandı, 30 Ekim 2026 — parça izi kümeleme): Decision 2 parça izi kümelemesini
(array1 %29,12, headset %22,89; `persist` yeniden çalışır) seçer. Daha küçük değişiklik olan satır
birleştirme (%33,19, %27,33; satırlar yeniden işaretlenir) kabul edilebilir mi?
