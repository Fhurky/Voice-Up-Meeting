# Kısa konuşma bölümlerinin reddi için tanı deneyi

Tarih: 10 Eylül 2026. Durum: karar öncesi araştırma; ürün değişikliği değildir.
Sabit profil `kt-vibecoding-python-web-v2` korunur. Bu çalışma
[50 kişilik kalite araştırmasının](SPEAKER_QUALITY_50.md) tutarlılık filtresi incelemesine
bağlıdır; [001 Decision 8](../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md)
altındaki üretim davranışını veya kabul edilmiş kalite korumalarını değiştirmez.

## Soru ve sınır

Kullanıcının sağladığı 52,63 saniyelik dosyada model 39,25 saniye konuşma buldu;
mevcut kısa parça kurtarması 0,4275 en düşük benzerlikle reddedildi. Daha uzun
doğal konuşma bölgeleri aynı modelin kısa parça belirsizliğini azaltabilir mi?
Bu dosyanın konuşmacı gerçeği bağımsız etiketlenmedi; kabul sonucu kimlik doğruluğu
veya tek konuşmacı kanıtı sayılamaz.

## Sonuçlardan önce sabitlenen deney

1. Aynı sabit ECAPA/Silero ağırlıkları ve güncel yerel CUDA kaynakları kullanılır.
   Tek değişken Silero `min_silence_duration_ms`: mevcut 100 ve tanı adayları 300/500.
   Pencere, RMS/kırpılma, 1,5 saniyelik özgün parça, 10 saniye/iki pencere ve
   0,55 tutarlılık sınırları değiştirilmez. Yeni parametre çalışma zamanına yazılmaz.
2. Kullanıcının dosyası yalnız yerelde belleğe alınır. Önceki kalibrasyonda
   kaydı başarılı ilk dört kişi, önceki galeri sırasıyla iki sabit çift oluşturur.
   Her birinin kendi enrollment kaydı tek kişi kontrolüdür; kaynaklar ve özetleri
   sonuç görülmeden Git dışındaki özel protokole kaydedilir. Kör test verisi açılmaz.
3. Her çift için iki negatif üretilir: ilk 16 saniyeden tekrar kullanılmayan
   ikişer saniyelik A/B parçalarıyla 32 saniye dönüşümlü ses; ilk 8 saniyelerden
   ikişer saniyelik A/B parçaları arasına 0,4 saniye sessizlik konmuş 18,8 saniye ses.
   Bu, mevcut negatif protokolünü tekrarlar. Sessizlik yalnız negatif girdidedir;
   algoritma ses örneği eklemez veya çoğaltmaz. Ayrıca 40 saniye sessizlik kontrolü vardır.
4. Önce bütün sesler/adaylar/protokol özetlenir, sonra aynı girdiler üç ayarda ölçülür.
   Her ayarda toplam bölge süresi, pencere sayısı, en düşük tutarlılık, son ret nedeni
   ve kayıt kabulü raporlanır. Uzatılan bölgeler gerçek kısa sessizlikleri de kapsayabilir;
   bu süre ayrıca mevcut 100 ms VAD aralıklarıyla karşılaştırılır, yeni konuşma gibi sunulmaz.
5. İki kişili karışımın kalite kapısından geçmesi kimlik kararından bağımsız başarısız
   negatiftir; toplam yanlış kabuller ve mevcut ayara göre yenileri ayrı gösterilir.
   Bir aday kullanıcı dosyasını kabul etse bile negatifleri kötüleştiriyorsa seçilmez.
   Baseline'ın zaten kabul ettiği karışımlar da saklanmaz veya başarılı sayılmaz.
6. Sonuç yalnız hipotezi elemek veya daha büyük kalibrasyon önermek içindir.
   Dört kişi ve iki çift, yaklaşık 50 kişilik kabul için yeterli değildir.
   Ürün değişikliğinden önce kendi kabul edilmiş planında tüm kalibrasyon galerisi,
   ayrı oturumlar, yanlış profile ekleme ve bağımsız test ile sürümlü ön işleme kanıtı gerekir.

## Kanıt ve dokunulmayan katmanlar

Model çağrıları ayrı tanı işleminde, ağdan indirme olmadan çalışır; hiçbir API,
profil/veritabanı, uygulama ayarı, servis imajı veya model dosyası değiştirilmez.
Ham ses ve vektörler rapora/Git'e konmaz. Özel protokol, yürütülen kodun özeti ve
ölçümler `outputs/2026-09-10-segmentation-diagnostic/` altında tutulur. Son rapor
Türkçe sabit koşum biçimini kullanır; araştırma sonucu tamamlanmış ürün kabulü sayılmaz.

Parametrenin konuşma sonundaki sessizlik beklemesini yönettiği resmî
[Silero kaynak kodunda](https://github.com/snakers4/silero-vad/blob/master/src/silero_vad/utils_vad.py)
açıklanır. Deneyde internet üzerindeki son kod değil, kurulu sabit 6.2.1 paketin
gerçek imzası ve yerel kaynak özeti kullanılır.
