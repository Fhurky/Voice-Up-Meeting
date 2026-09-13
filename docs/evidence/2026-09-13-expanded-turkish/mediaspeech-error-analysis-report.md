# Koşum raporu — 2026-09-13 · Tamamlanan 2.433 MediaSpeech klibinde betimleyici hata örüntüleri

> Düzeltme kaydı: Geçici analiz kodunun PowerShell aktarımı Türkçe sabit sözcük
> listelerini bozdu; bu sürümdeki sayı/söylem belirteci/harf işareti aday
> sayıları geçersizdir. Özgün JSON ve rapor tarihçe olarak korundu;
> [Unicode doğrulamalı v2 raporu](mediaspeech-error-analysis-v2-report.md) güncel
> kanıttır. Modelin kelime hata toplamları ve sınır silmesi, birleşik/ayrı
> yazım, kesme işareti sayıları değişmedi.

1. Sonuç: Tamamlanmış bütün 2.433 klip incelendi, 12.167 kaynak/hizalama kontrolü başarılı; mevcut skorlar değişmedi — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows/Python üzerinde yalnız CPU; mevcut özel rapor ve sabit veri manifesti bir kez okundu. Önceki [100 kliplik incelemenin](partial-diagnostic-report.md) aynı Türkçe sözcük, hata bloğu ve sınır silmesi ölçütleri bütün koşuma uygulandı. Ayrı model veya ses çıkarımı yapılmadı. Sabit profil `kt-vibecoding-python-web-v2` korunuyor.

   | Gözlem | Tam koşumdaki sayı |
   | --- | ---: |
   | Klip / ses süresi | 2.433 / 34.852,10 saniye |
   | Referans / hipotez kelimesi | 71.767 / 70.153 |
   | Değiştirme / silme / ekleme | 5.303 / 3.224 / 1.610 |
   | Toplam kelime hatası | 10.137 |
   | Sıfır kelime hatalı / boş hipotezli klip | 148 / 0 |
   | Rakam içeren referans / hipotez klibi | 0 / 656 |
   | Rakam–yazıyla sayı temsili adayı | 514 klip, 753 hata bloğu |
   | Birleşik–ayrı yazım eşdeğer harf dizisi | 242 klip, 267 hata bloğu, 546 hata işlemi |
   | Yalnız kesme işareti farklı değiştirme | 241 klip, 265 değiştirme |
   | Başta silinen referans kelimesi | 285 klipte 675 kelime |
   | Sonda silinen referans kelimesi | 331 klipte 712 kelime |
   | En az bir sınırda / iki sınırda silme | 564 / 52 klip |
   | Söylem belirteci adayını içeren hata | 92 klipte 97 işlem |

   Her klipte ses hash'i ve referans metin eşleşmesi ile üç hizalama hata
   sayısı kontrol edildi: 5 × 2.433 = 12.165. Tamamlanma/kapsam ve manifest
   bağının doğrulanmasıyla toplam 12.167 kontrol başarılı. Hizalama en düşük
   kelime düzenleme maliyetini kullanır; eşit maliyette çapraz eşleme, silme,
   ekleme sırası mevcut puanlayıcıyla aynıdır. Bağımsız nihai puan/günlük
   denetimi bu raporun konusu değildir.

   Toplu kanıt [mediaspeech-error-analysis.json](mediaspeech-error-analysis.json);
   SHA-256 `de6e8014deb98998a34cbd4619f6d556cef8f3efc4e689fdd71d85264b2fc820`.
   Okunan özel rapor SHA-256
   `3deda87a9a14d0e6c5744c8c26fb0309e091f910eba21300078bdaea43b2776f`;
   veri manifest SHA-256
   `e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef`.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Bu kategoriler betimleyici ve kesişen adaylardır; bağımsız hata nedenleri gibi toplanamaz. Rakam/yazıyla sayı adayında iki biçimin aynı anlamı taşıdığı kanıtlanmadı; 753 blok içindeki 1.926 işlem puandan çıkarılmadı.

   M2 Kısa klip sınırındaki silme, kaydın kırpıldığı veya referansın yanlış olduğu anlamına gelmez. Ses dinlenmedi; aynı maliyetli farklı hizalamalar silmenin konumunu değiştirebilir.

   M3 Model, ayar, sözlük ve `turkish-words-v1` normalizasyonu değişmedi. Bu çalışma aynı koşumun hata açıklamasıdır; model iyileşmesi veya yeni bağımsız test değildir.

   **GÖZLEM**

   M4 656 hipotezde rakam bulunurken referanslarda hiç rakam yok. İnsan denetimi için ilk somut alan, 514 klipteki sayı temsili adaylarının sesle karşılaştırılması ve referans yazım sözleşmesinin açıklığa kavuşturulmasıdır.

   M5 267 blokta farklı sayıda sözcük aynı birleşik harf dizisine karşılık geliyor; 265 değiştirme yalnız kesme işareti farkı. Bunlar ölçümde yazım biçiminin katkısını gösteren doğrudan adaylar; genel ses tanıma başarısı diye yeniden puanlanmadı.

   M6 Baş/son silmeleri toplam 1.387 kelime, yani 3.224 silmenin yaklaşık %43,0'ı. İnsan incelemesinde 564 klibin başlangıç/bitiş sesiyle referans kapsamını karşılaştırmak, bu kayıpları model veya kaynak nedeni olarak ayırmaya yardımcı olabilir.

   M7 Sabit söylem belirteci aday listesi 392 referansta görünüyor; 97 hata işleminde yer alıyor. Bu sınırlı tarama özel ad/yabancı kelime sınıflandırması yapmaz; sıfır büyük harfli aday özel ad yokluğunu göstermez.

   M8 207 klipte eklemeler, silme ve değiştirmelerin toplamını aşıyor; 15 klipte kelime hata oranı %50'nin üzerinde. Bu özellikler dinleme önceliği oluşturabilir, tek başına halüsinasyon tanısı değildir.

   **AÇIK**

   M9 İnsan ses dinleme, referans düzeltme, anlamsal sayı eşdeğerliği, kişi/oturum bağımsızlığı ve özel ad hata etiketleri bu koşumda ölçülmedi. İleride kurallar değiştirilirse yeni sürümle ve ayrı değerlendirme kaydıyla sınanmalıdır.

   **YAN-ETKİ**

   M10 Yalnız toplu hata analizi JSON'u ve bu rapor eklendi. Ham metin/kimlik yayımlanmadı; sesler, özel rapor, model, kod, çalışan GPU denemesi ve `results.md` değiştirilmedi.
