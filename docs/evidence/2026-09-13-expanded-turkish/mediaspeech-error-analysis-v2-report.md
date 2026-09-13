# Koşum raporu — 2026-09-13 · Türkçe sabit sözcük aktarımı düzeltilmiş tam MediaSpeech hata analizi

1. Sonuç: 2.433 klip için 12.167 kaynak/hizalama kontrolü, ortak Unicode aktarımında 10 ve son belge kontrolünde 7 kontrol başarılı; modelin kelime hata toplamları aynı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python CPU, tamamlanmış özel rapor üzerinde sürüm `voiceup-turkish-orthography-boundary-diagnostics-v2`. Geçici Python kodu yalnız ASCII içerdi; Türkçe sabit sözcükler açık Unicode kaçışlarıyla oluşturuldu, JSON UTF-8 okundu. Ürün profili `kt-vibecoding-python-web-v2` değişmedi.

   | Gözlem | Doğrulanmış v2 sayısı |
   | --- | ---: |
   | Klip / referans kelimesi / toplam kelime hatası | 2.433 / 71.767 / 10.137 |
   | Değiştirme / silme / ekleme | 5.303 / 3.224 / 1.610 |
   | Rakam içeren referans / hipotez klibi | 0 / 656 |
   | Rakam–yazıyla sayı temsili adayı | 617 klip, 1.014 hata bloğu |
   | Birleşik–ayrı yazım eşdeğer harf dizisi | 242 klip, 267 blok, 546 hata işlemi |
   | Yalnız kesme işareti farklı değiştirme | 241 klip, 265 değiştirme |
   | Harf işareti/kesme farkı adayı, önceki satır hariç | 36 klip, 38 değiştirme |
   | Başta / sonda silinen referans kelimesi | 675 / 712 |
   | En az bir / iki sınırında silme bulunan klip | 564 / 52 |
   | Söylem belirteci adayını içeren hata | 167 klipte 182 işlem |

   [Toplu v2 JSON](mediaspeech-error-analysis-v2.json), SHA-256
   `eb7d1a0131fef0ebd25d84c4d413155be2734b26cd6cada0f81fbbfb344ef524`;
   [10 aktarım kontrolü](diagnostic-unicode-probes.json), SHA-256
   `0d70b4d2d891ea1bdc0aef9e628077be7fce77efd070d7b4841ad34ceb315bf6`.
   Kaynak özel rapor SHA-256
   `3deda87a9a14d0e6c5744c8c26fb0309e091f910eba21300078bdaea43b2776f`.
   JSON, önceki analizin hash'ini ve değişen aday sayılarının eski/yeni
   değerlerini de tutar; önceki kanıt üzerine yazılmadı.

   Son salt okunur belge kontrolü, iki v2 rapordaki beş içerik hash'i
   atfını gerçek dosya baytlarıyla ve iki yayımlanmış Unicode listesini
   karşılaştırdı: 7 başarılı, 0 başarısız. Bu ortak kontrol kaynak başına
   ayrı tekrar sayılmaz.

3. Maddeler:

   **KUSUR**

   M1 İlk geçici analizde PowerShell, Türkçe sabit sözcük listesindeki harfleri `?` ile aktardı; sayı/söylem/harf işareti aday sayıları eksik veya yanlıştı. ASCII kod ve açık Unicode kaçışlarıyla düzeltildi; gerçek UTF-8 JSON listeleri, aktarım ve eski kusur 10 kontrolle doğrulandı (DÜZELTİLDİ, `diagnostic-unicode-probes.json`).

   **TUZAK**

   M2 1.014 sayı temsili aday bloğundaki 2.359 hata işlemi anlamsal eşdeğerliği kanıtlamaz. Kategoriler kesişir; puandan çıkarılamaz veya birbirini dışlayan nedenler gibi toplanamaz.

   M3 Sınır silmeleri aynı maliyetteki hizalama tercihlerinden etkilenebilir. Ses dinlenmeden kırpma, hatalı referans veya model kaybı nedeni atanamaz; bu analiz yeni bir model deneyi değildir.

   **GÖZLEM**

   M4 Rakam içeren 656 hipoteze karşı referanslarda rakam yok; 617 klipteki sayı yazımı adayları ve 267 birleşik/ayrı yazım bloğu, ses–referans yazım sözleşmesinin insan tarafından incelenmesi için somut kapsam sağlıyor.

   M5 Sınırdaki 1.387 silme, toplam 3.224 silmenin yaklaşık %43,0'ı; 564 farklı klibi etkiliyor. Bu sayılar ilk sürümle aynı, öncelikli dinleme alanı olmaya devam ediyor.

   M6 Sabit söylem adayları 626 referansta var; 182 hata işlemi 167 klipte görüldü. Önceki 392/97/92 sayıları aktarım kusuru nedeniyle kullanılmamalı; model çıktısı veya gerçek kelime hata oranı değişmedi.

   **AÇIK**

   M7 İnsan ses dinleme, sayıların anlamsal eşdeğerliği, doğru özel ad ve bağımsız kişi/oturum değerlendirmesi yapılmadı. Önerilen inceleme, mevcut metrikten hataları silme yetkisi veya yeni bir başarı puanı oluşturmaz.

   **YAN-ETKİ**

   M8 Yeni sürümlü toplu JSON/rapor ve ortak aktarım kanıtı yazıldı; eski kısmi/tam raporlara düzeltme notu eklendi. Model, kaynaklar, özel sonuçlar, kod, GPU koşumu ve `results.md` korunuyor.
