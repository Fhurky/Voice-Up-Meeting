# Koşum raporu — 2026-09-13 · İki yeni Türkçe toplantı zincirinin bağımsız canlı doğrulaması

1. Sonuç: 274/274 doğrulama başarılı; iki zincirde de altı yeni kişi görünümü ve altı bilinen geri dönüş doğru, 12 toplantı başarıyla tamamlanmış — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel RTX 4060 üzerinde tamamlanan uygulamanın gerçek HTTP sonuçları; profil `kt-vibecoding-python-web-v2`. Bu denetim model çalıştırmadı; iki sıradan hesapla girişten sonra yalnız GET yaptı. Kanıt seviyesi L2, insan tarafından kabul edilmiş 50 kişilik başarı değil.

   | Denetim | Gözlenen sonuç |
   | --- | --- |
   | Kaynak ve özel durum doğrulaması | İki sabit protokol, 12 WAV ve iki tamamlanmış durum kabul edildi; kaynak protokolü, seçim ve bilinen sayı seçeneği bağlı |
   | Gerçek sıradan kullanıcı girişi | 2/2 başarılı; `super_admin` yok, gerekli sıradan izinler ve önceki tenant/hesap bağları doğrulandı |
   | Toplantı GET | 12/12 `succeeded`; ses hashleri, dil `tr`, `expected_speakers=2` ve `participant_count=2` aynı |
   | Konuşmacı ve metin koleksiyonlarını GET ile okuma | 12 konuşmacı koleksiyonu ve 12 metin koleksiyonu sayfaları tamamlandı; her toplantıda iki ayrı profil, metnin kalıcı alanları özel kayıtla aynı |
   | Son galeri GET | 2 ayrı tenant/hesapta altışar profil; profillerin tamamı özel hafıza eşlemesiyle aynı |
   | Referans eşleme ve kişi bölümlerini yeniden hesaplama | 12/12 eşleme başarılı; her zincirde 6 yeni ve 6 bilinen görünümün sonucu canlı profil kararlarıyla doğrulandı |
   | Metin ve toplu sonucu yeniden hesaplama | Bütün 12 metin skoru, iki kimlik/toplu sonuç ve ilgili iki günlük kaydı aynı çıktı |
   | Yan etki denetimi | 26 girdi/kod dosyasının SHA-256 değeri ve günlük içeriği denetim boyunca değişmedi |

   Ayrıntılı toplu kanıt: [meeting-comparison.json](meeting-comparison.json).
   Bu denetim yeni bir test paketi koşumu değildir; önceki 103 otomatik regresyonun kanıtı
   [hazırlama raporundadır](meeting-preparation-report.md).

   | Ölçüm | `[300,600)` | `[600,900)` |
   | --- | ---: | ---: |
   | Yeni ses süresi | 30 dakika | 30 dakika |
   | Yeni kişiyi doğru kaydetme | 6/6 | 6/6 |
   | Bilinen geri dönüşü doğru tanıma | 6/6 | 6/6 |
   | Precision / recall / mikro F1 / makro F1 | %100 / %100 / %100 / %100 | %100 / %100 / %100 / %100 |
   | Bilinmeyen kişi F1 | %100 | %100 |
   | VoiceUp Score | 100 | 100 |
   | İlk görünümde kayıt kapsamı | %100 | %100 |
   | Galeri ilerleyişi | 2→3→4→5→6→6 | 2→3→4→5→6→6 |
   | Türkçe normalizasyon sonrası referans sözcük | 4.032 | 4.143 |
   | Hipotez sözcük | 3.668 | 3.818 |
   | Kişiye atanmamış sözcük | 23 | 33 |
   | Yerine koyma / silme / ekleme | 512 / 530 / 166 | 544 / 521 / 196 |
   | Toplam sözcük hatası | 1.208 | 1.261 |
   | Konuşmacı etiket eşlemesi sonrası sözcük hata oranı, cpWER | %29,9603 | %30,4369 |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 İki zincir aynı altı kişi ve aynı altı kaynak görüşmeye dayanır. Toplam 12 kesit ve 60 dakika yeni içerik, 12 bağımsız görüşme veya 12 farklı kişi demek değildir; iki tenant'ın altışar profili de 12 farklı insan sayılmaz.

   M2 Her toplantının gerçekten konuşan kişi sayısı iki olarak verilmiştir. Sonuç otomatik kişi sayısı bulmanın veya yaklaşık 50 kişilik galerinin doğruluğunu kanıtlamaz.

   M3 Kaynak etkinliği otomatik, metin ve zaman hizası doğrulanmamıştır; bu nedenle kişi/metin sonuçları tanısaldır. En düşük baskın eşleme payları sırasıyla %96,5806 ve %90,4989 olup mevcut %90 eşiği değiştirilmedi.

   M4 Hazırlamadaki boşlukla ayrılmış 4.030/4.140 sözcük, ölçümde kullanılan `turkish-words-v1` sonrasındaki 4.032/4.143 ile aynı değildir. cpWER paydaları yalnız normalizasyon sonrası sayılardır.

   **GÖZLEM**

   M5 İki gerçek zincirde de doğru kişi hafızası gözlendi; metin hatası yaklaşık %30 kaldı. Kimlik F1=%100, metnin kusursuz olduğu veya sözcük zamanlarının doğru olduğu anlamına gelmez.

   M6 İki günlük kaydının toplu sonuç hashleri, izinli alan izdüşümleri ve metadata değerleri orijinal deney artefaktlarından yeniden doğrulandı. Günlük değiştirilmedi; ikinci bir deney kaydı eklenmedi.

   **AÇIK**

   M7 İnsan tarafından denetlenmiş zaman/metin referansı, yeni Türkçe kişiler/oturumlar, 50 kişi, Apple/Spark ve tarayıcı mikrofonu bu denetimde ölçülmedi. ASR kaynaklarının daha geniş ölçümleri ayrı deneylerdir.

   **YAN-ETKİ**

   M8 Yalnız bu rapor ve kişisel içerik taşımayan `meeting-comparison.json` oluşturuldu. Uygulama verisi, profil, model, özel durum dosyası ve `results.md` değiştirilmedi; ham metin, parola, token veya kişi/profil kimliği yayımlanmadı.
