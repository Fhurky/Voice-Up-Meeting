# PRD — Toplantı verimlilik analizi

Status: Draft

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [023 — meeting-effectiveness-analysis](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (30 Ekim 2026): Kullanıcı, toplantı içeriğine göre soruların cevaplanıp cevaplanmadığının
kontrol edilmesini, cevapların çıkarılmasını, konuya uygunluğun puanlanmasını ve 100 üzerinden bir
verimlilik puanı verilmesini istedi. [022](../022-meeting-context-inputs/PRD.md) girdilerine ve
metin inceleme sağlayıcısına ([012](../012-contextual-transcript-review/PRD.md),
[018](../018-institutional-gpu-platform/PRD.md)) bağlıdır.

## Amaç ve önceki durum

Bugün dil modeli yalnız seçilen bir satırın düzeltmesini önerir. Hedef: tamamlanmış toplantı metninden
soru cevapları, konu uygunluğu ve açıklanabilir bir verimlilik puanı üretmek. Her cevap toplantıdaki
satırlara dayanmalıdır: dayanak yoksa cevap da yoktur.

## Kararlar

Decision 1: Analiz toplantı `succeeded` olduktan sonra çalışan ayrı bir iştir; toplantı sonucunu
geciktirmez ve başarısız olması toplantıyı etkilemez. Konu veya soru varsa ve özellik açıksa kendiliğinden
kuyruğa girer, kullanıcı yeniden başlatabilir. Metin düzeltilirse sonuç "güncel değil" işaretlenir.

Decision 2: Son puanı dil modeli vermez. Model yalnız yapısal etiket üretir, puanı sunucu
Decision 4'teki sabit formülle hesaplar. Aynı etiketler her zaman aynı puanı verir ve her puanın
dökümü ekranda görülür.

Decision 3: Her soru için model `answered`, `partial` veya `unanswered` durumu, kısa cevap ve dayanak
satır kimlikleriyle birebir alıntı döndürür. Sunucu dayanağın bu toplantının etkin satırında bulunduğunu
doğrular; doğrulanmayan cevap `unanswered` sayılır. Toplantı metni güvenilmeyen girdidir: içindeki
"bu toplantıya tam puan ver" gibi ifadeler talimat değildir, çıktı şeması ve dayanak doğrulaması bunu
sınırlar.

Decision 4: Ölçek (`effectiveness-v1`, kayıtta sürümle saklanır):

- Soru puanı = (cevaplanan + 0,5 × kısmen cevaplanan) / toplam soru × 100.
- Konu puanı = konuşma süresiyle ağırlıklı bölüm etiketi: `on_topic` 1, `related` 0,5, `off_topic` 0.
- Verimlilik puanı: ikisi de varsa %60 soru + %40 konu; yalnız biri varsa o; ikisi de yoksa puan yok
  ("hesaplanamadı", 0 değil).
- Bantlar: 85–100 çok verimli, 70–84 verimli, 50–69 kısmen verimli, 0–49 düşük.

Decision 5: Uzun toplantılar 5 dakikalık bölümlerle işlenir; her bölüm için sınırlı sayıda model çağrısı
yapılır, soru sonuçları birleştirilir. Çağrı sayısı ve süresi toplantı süresiyle doğrusal sınırlıdır.
Yerelde konuşma servisi meşgulken analiz bekler; Docker belleği ikisini aynı anda taşımaz.

Decision 6: Puan toplantıya aittir. Kişi bazında puan, sıralama veya konuşma süresi karşılaştırması
üretilmez; çıktı çalışan değerlendirmesi için tasarlanmamıştır ve ekranda bunu belirtir.

Decision 7: Özellik varsayılan kapalıdır ve yalnız yerel/kurum içi sağlayıcıyı kullanır; dış servis
yoktur. Prompt, metin ve cevaplar günlüğe yazılmaz; sonuçlar toplantıyla aynı saklama ve silme
kurallarına tabidir. Düşük metin güveninde sonuç ekranda uyarıyla gösterilir.

## Gereksinimler

Requirement 1: `meeting_effectiveness` ve soru/bölüm sonuç tabloları, durum makinesi, kiracı yalıtımı,
worker adımı, API ve OpenAPI.

Requirement 2: Sağlayıcı portu mevcut Ollama adaptörünü ve 018 uç noktasını kapsar; bozuk çıktı, zaman
aşımı ve eksik dayanak testleri imza kısıtlı sahte sağlayıcıyla yazılır.

Requirement 3: Formül ve doğrulama saf alan fonksiyonlarıdır (birim testleri, bant sınırları, eksik
girdi hâlleri).

Requirement 4: Sonuç ekranında "Verimlilik" sekmesi: puan, bant, döküm, soru cevapları ve dayanak
satırlara bağlantılar; TR/EN; kalıcı tarayıcı senaryosu.

Requirement 5: Değerlendirme: insanlarca etiketlenmiş Türkçe toplantılarda yanlış cevap oranı, dayanak
doğruluğu, "cevaplandı/cevaplanmadı" uyumu ve konu etiketi uyumu `results.md`'ye işlenir.

## Kabul ölçütleri

- [ ] Etiketli Türkçe toplantılarda dayanağı yanlış olan cevap 0; ölçütler `results.md`'de (eşikler kabul öncesi belirlenir).
- [ ] Aynı etiketler aynı puanı verir; dayanaksız cevap puana girmez.
- [ ] Analiz hatası toplantı sonucunu etkilemez; kiracı, yetki ve silme testleri geçer.
- [ ] Tam kalite kapısı, tarayıcı senaryosu ve kullanıcı kabulü (L3).

Open Question 1: Ağırlık %60 soru + %40 konu uygun mu?

Open Question 2: Etiketli değerlendirme için hangi Türkçe toplantılar kullanılacak? (015 ile ortak ihtiyaç.)
