# Türkçe kişi hafızası için ek kaynak incelemesi

Tarih: 2026-09-13. Bu araştırma, [ana taramayı](TURKISH_DATASET_RESEARCH.md)
tamamlar; [010 PRD](../specs/speaker-identity/PRDs/010-expanded-turkish-benchmark/PRD.md)
ve mevcut model koşumlarını değiştirmez. Altı adayın birincil kartı, makalesi,
lisansı veya dosya metadatası salt okunur incelendi; ses indirilmedi.

Bu altı kaynak arasında, hemen çalıştırılabilecek ve farklı oturumlarda en az
50 Türkçe kişiyi doğrulanmış etiketlerle içeren açık bir paket doğrulanmadı.
Yeni ve ölçek bakımından anlamlı araştırma adayı **VoxBlink2**; fakat doğrudan
ses dağıtmıyor ve Türkçe etiketleri kesin değil. Satın alınabilir kaynaklar
arasında **TUR_ASR001**, aynı kişiden iki ayrı aramayı açıkça belgeleyen en
uygun aday olarak kalıyor; dosya eşleme şeması henüz görülmedi.

| Aday | Doğrulanan kimlik/kayıt kapsamı | Lisans ve erişim | Hafıza deneyi açısından karar |
| --- | --- | --- | --- |
| [VoxBlink2](https://voxblink2.github.io/) | Yayıncı 1.150 Türkçe etiketli konuşmacı bildiriyor; kişi kimliği, kaynak video ve zaman etiketleri var. Dil etiketi video etiketlerinden tahmin edilmiş; gerçek konuşma dili garanti değil. | Kaynaklar CC BY-NC-SA 4.0; yalnız metadata yayımlanıyor, sesler ayrıca kaynak videolardan edinilmeli. Video erişilebilirliği garanti değil. | Elli Türkçe kişi için araştırma adayı; kişi/dil doğrulaması, farklı video/oturum ayrımı ve kullanım kapsamı çözülmeden hazır test sayılmaz. |
| [CSVD kartı](https://github.com/bunyaminergen/Callytics/blob/2bc20b8a3762a5619c1b79381fe73c8c224dcb36/.data/groundtruth/speakerverification/DatasetCard.md) | Türkçe ağırlıklı telefon görüşmeleri, çağrı–ses izi arasında `csr_id` eşlemesi. Kart 10 çağrı söylüyor; sabit gerçek dosya ağacında yalnız 2 çağrı ve 1 ses izi WAV var. | Veri klasörünün [lisansı GPL-3.0](https://github.com/bunyaminergen/Callytics/blob/2bc20b8a3762a5619c1b79381fe73c8c224dcb36/.data/groundtruth/speakerverification/LICENSE); dosyalar açık. | Çok küçük akış örneği; 50 kişi verisi değil. Dosya/metadata eksikliği nedeniyle ana referans yapılmadı. |
| [TURTEL araştırması](https://dergipark.org.tr/en/download/article-file/298313) | 93 kişi, kişi başına 15 Türkçe cümle; 5 kayıtla profil ve 10 kayıtla doğrulama. Makale oturum değişkenliği olmadığını açıkça belirtiyor. | İncelenen yayında açık ses paketi ve veri kullanım lisansı doğrulanmadı. | Kişi sayısı yeterli görünse de farklı oturum hafızası kanıtı sağlamaz; erişimi hazır değil. |
| [Appen TUR_ASR001](https://www.appen.com/data-catalog/audio-catalogue/tur-asr001) | 100 kişi ikişer arama yapıyor: biri sabit, biri mobil telefon; 200 görüşme, 41,5 saat. | Ticari katalog; açık tam indirme ve ayrıntılı lisans metni görülmedi. | Gerçek tekrar ve cihaz farkı açısından güçlü aday. Aynı kişinin iki dosyasını bağlayan şema ve en az 50 geçerli eşleme örnek veride doğrulanmalı. |
| [METU Microphone v1.0](https://catalog.ldc.upenn.edu/LDC2006S33) | 120 kişi (60 kadın/60 erkek), kişi başına 40 cümle; 5,6 saat. | LDC kullanıcı sözleşmesi, hesap ve ücretli erişim. | Kontrollü 50 kişi karşılaştırmasına uygun aday; gün/oturum değişimi katalogda doğrulanmıyor. |
| [TSC filtered 94h](https://huggingface.co/datasets/ulaspolat/tsc-tr-filtered-94h) | 72.245 kayıt; kart kimliklerin WeSpeaker gömmeleri ve HDBSCAN ile üretilmiş yaklaşık kümeler olduğunu açıkça söylüyor. Küme saflığı ölçülmemiş; tüm kayıtların tek kişili olması garanti değil. | Açık dosyalar; incelenen kart/API'de türevin açık lisans alanı yok. | Otomatik `speaker_id` alanı insan doğrulanmış kişi gerçeği yerine kullanılamaz; ana hafıza testi olarak kabul edilmedi. |

CSVD dosya incelemesinde kullanılan revizyon
`2bc20b8a3762a5619c1b79381fe73c8c224dcb36` idi. İki çağrı metadata satırı aynı
tek temsilci kimliğine ve aynı kayıt tarihine işaret ediyor. Ses izi metadata'sı
iki satır içeriyor, ancak bunlardan birinin ses dosyası yayımlanan ağaçta yok.
Müşteri rollerinin kayıtlar arasında kalıcı kimliği belgelenmiyor; sesleri
dinlemediğimiz için konuşma dili ve kayıt kalitesi doğrulanmış sayılmaz.
[Dosya ağacı](https://github.com/bunyaminergen/Callytics/tree/2bc20b8a3762a5619c1b79381fe73c8c224dcb36/.data/groundtruth/speakerverification),
[çağrı metadata'sı](https://github.com/bunyaminergen/Callytics/blob/2bc20b8a3762a5619c1b79381fe73c8c224dcb36/.data/groundtruth/speakerverification/call/v1/metadata.json),
[ses izi metadata'sı](https://github.com/bunyaminergen/Callytics/blob/2bc20b8a3762a5619c1b79381fe73c8c224dcb36/.data/groundtruth/speakerverification/voiceprint/v1/metadata.json).

Öneri: mevcut Türkçe metin testlerini tamamlayıp gerçek kişi hafızası açığını
ayrı tutmak; bir sonraki kişi veri ediniminde TUR_ASR001 örnek eşlemesini veya
izinli 50 kişilik, farklı gün/cihaz kayıt koleksiyonunu esas almak. VoxBlink2
ancak doğrulanmış Türkçe/kişi/video alt kümesi oluşturulabilirse araştırma
karşılaştırmasına dönüşebilir. Aynı kaydı parçalamak, yaklaşık kümeleri yeniden
numaralamak veya dil etiketini kişi kimliği sanmak bu açığı kapatmaz. Bu not
satın alma, iletişim gönderme, ses indirme veya yeni eğitim başlatma kararı değildir.
