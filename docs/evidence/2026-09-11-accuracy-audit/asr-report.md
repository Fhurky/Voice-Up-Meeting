# Koşum raporu — 2026-09-11 · Mevcut metin doğruluğu, zaman hizası ve iki sınırlı ASR adayı

1. Sonuç: Başlangıç A/B/C konuşmacılı sözcük hatası %15,3034 ölçüldü; aynı modelle iki aday bütün kabul koşullarını geçemedi ve üretime alınmadı — birim 0 başarılı / bağımsız skor karşılaştırması 6 başarılı / aritmetik ve normalizasyon kontrolü 11 başarılı / gerçek GPU çağrısı 30 tamamlandı / aday kabulü 0/2 / tarayıcı 0 başarılı / atlanan 1 (D sözcük referansı); karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, başlangıç commit'i `a096cf8ce1dd6d056f29968439735dea1ea72828`; gerçek PostgreSQL `REPEATABLE READ, READ ONLY` anlık görüntüsü, yerel Python ve ağsız mevcut CUDA imajı.

   | A/B/C kaynak | Referans sözcük | Başlangıç S / D / I | Başlangıç cpWER | Kısa pencereler cpWER | Hedefli onarım cpWER |
   | --- | ---: | --- | ---: | ---: | ---: |
   | A | 494 | 27 / 17 / 22 | 66/494 · %13,3603 | 82/494 · %16,5992 | 66/494 · %13,3603 |
   | B | 263 | 16 / 16 / 15 | 47/263 · %17,8707 | 40/263 · %15,2091 | 47/263 · %17,8707 |
   | C | 380 | 12 / 41 / 8 | 61/380 · %16,0526 | 47/380 · %12,3684 | 48/380 · %12,6316 |
   | Toplam | 1137 | 55 / 74 / 45 | 174/1137 · %15,3034 | 169/1137 · %14,8637 | 161/1137 · %14,1601 |

   | Çalışma kanıtı | Ölçüm |
   | --- | --- |
   | İmaj | `sha256:09dbebcbdaff48b701260d8e837344aca6c5bb13cde762cf14781dc37bd08110` |
   | Model | `Systran/faster-whisper-large-v3`, `edaa852ec7e145841d8ffdb056a99866b5f0a478` |
   | Doğrulanan model manifest SHA-256 | `4b732a1ccb96003631bc799fcdfd9fb5f22705ac6c164e7d88c6b505ecf8b85f` |
   | Çalışma ortamı | Python 3.13.14, faster-whisper 1.2.1, CTranslate2 4.8.1; `int8_float16`, 5 beam, 4 CPU iş parçacığı, 1 worker |
   | Başlangıç CPU skor ölçümü | 2,422 saniye; 0 model çağrısı; NULL hipotezi korunmuş |
   | Üç yeni bütün-kayıt ASR süresi | A 13,079 / B 7,757 / C 9,139 saniye; toplam 29,975 saniye |
   | Kısa pencere adayı | A 11 / B 6 / C 9 klip; toplam ASR 45,196 saniye; başlangıcın 1,508 katı; kapsayıcı 131,515 saniye |
   | Hedefli onarım adayı | A 0 / B 0 / C 1 tetik; tek 22,66 saniyelik PCM girdi; ASR 2,127 saniye, kapsayıcı 49,938 saniye |
   | Başlangıç NULL sözcükleri | A 10 / B 4 / C 7; iki skorda da korunmuş |
   | Kaynak belgeleri | [Yayımlanan aggregate sonuç ve protokol hashleri](asr-results.json); özel ayrıntılar yerel `outputs/2026-09-11-accuracy-audit/` altında |

3. Maddeler:
   **KUSUR**
   M1 AÇIK: C'de bir başlangıç kelimesi 105,02–117,68 saniyeyi kapsıyor ve olasılığı 0,8535; yüksek sözcük olasılığı zaman doğruluğu kanıtı değil. Önceki sekiz gerçek VAD karşılaştırmasında sesin 0 saniyesi çıkarılmış, kelime/zaman kusuru değişmemişti.
   M2 REDDEDİLDİ: Tam kapsamalı kısa pencereler toplam hatayı 174→169 düşürse de A'yı 66→82 kötüleştirdi ve A'da yeni 10,92 saniyelik kelime üretti; C'nin değişmemiş referans eşleme kontrolü de geçmedi.
   M3 REDDEDİLDİ: İki yandan ankrajlı onarım A/B'yi aynen korudu ve C hatasını 61→48 azalttı; fakat C'de ls-6313 zaman baskınlığı %88,1424 kaldı ve önceden sabit en az %90 koşulunu geçmedi. Eşik değiştirilmedi.
   M4 AÇIK: Onarımın geri getirdiği 106,24–114,78 satırı ls-5895'e atanıyor; satır aslında ls-6313'ün 1,715 ve ls-6455'in 0,4799375 saniyelik kısa dönüşlerini de kapsıyor. Mevcut native ayrım bu iki kısa dönüşü başka kişi altında toplamış; eski belirsiz uzun kelime bu yanlış atamayı görünmez kılmıştı.
   M5 AÇIK: Mevcut sağlayıcı sıfır süreli kelimeyi düşürüyor. Üç başlangıçta böyle kelime 0; kısa pencerelerde A'da 3, C'de 6 gözlem var; hedefli onarımın 67 native kelimesinde geçersiz aralık 0. Bağlam tekrarları nedeniyle 9 gözlem, 9 tekil toplantı kelimesi anlamına gelmez.
   **TUZAK**
   M6 cpWER kişi akışlarını en düşük edit maliyetiyle eşler; kalıcı profil kimliğini doğrulamaz. NULL standart skorda ayrı akış olarak kalır; ayrıca NULL'ı yalnız boş referansa eşleyen `assigned_only` ölçüldü. Bu koşumda iki maliyet aynı çıktı.
   M7 Normalizasyon iki tarafa aynı uygulandı: NFKC, casefold, apostrof eşleme, Unicode L/N/M ve iç apostrofu koruma; sayı açılımı veya sözcük silme yok. Genel Unicode casefold Türkçe yerel harf eşlemesi değildir: `İZMİR` ile `izmir` aynı token olmaz; doğal Türkçe metin doğruluğu bu İngilizce ölçümden çıkarılamaz.
   M8 A/B/C daha önce incelenmiş kalibrasyon verisidir, kör doğrulama kümesi değildir. Kaynakların 8 saniyelik kesimleri sözcüğü bölebilir; kişi başına tüm özgün cümleler aynı sırayla tamamlandığı PCM düzeyinde doğrulandı.
   M9 Hedefli onarım seçimi native etiketleri kullanır; aynı kişinin gereksiz bölünmüş iki etiketi yanlış tetik üretebilir. İki taraflı ankraj veya geçerli değiştirme aralığı yoksa eski kelimeler korunur; referans metni seçim ve GPU aşamasına verilmedi.
   **GÖZLEM**
   M10 Seçili 24 kaynak clip'in 89 farklı cümlesi için 12 yerel resmî `.trans.txt` dosyası eksiksiz; her clip'in PCM'si özgün FLAC'ların sıralı birleşimiyle aynı. A/B/C referans ve hipotez sıraları, hash'leri ve normalizasyonu skor öncesi donduruldu.
   M11 Başlangıç A/B/C'de sağlayıcı kelimeleri ile veritabanındaki arayüz metninin boşluksuz dizisi birebir aynı. Bu üç kayıttaki kayıp metin son satır birleştirme filtresinde oluşmuyor; yeni bütün-kayıt ASR tekrarı da eski S/D/I sayılarıyla aynı çıktı.
   M12 C'nin cpWER hizalamasında eşleşen referans sözcükleri hedefli onarımla 327→351, substitution+insertion 20→33 oldu. Değişen 3 eski kelime gözlemi yerine 41 gözlem geldi: 29 baskın kaynakla uyumlu, 9 başka kişiye atanmış, 2 atanmamış, 1 kaynak desteksiz; bu son sınıflama elle kelime zamanı değil, yapay kaynak zaman çizelgesi vekilidir.
   M13 Başlangıçta kişi/sıra gözetmeyen sözcük çoklu-küme hata alt sınırı A %5,2632 / B %7,6046 / C %10,7895; bu WER değildir. Yeniden sıralama veya kişi ataması giderilse bile aynı sözcük envanteriyle kalan leksik hata için alt sınırdır.
   M14 Bağımsız tam permütasyon oracle'ı ile yeni Hungarian skorlayıcısı A/B/C standard ve assigned-only altı durumda hata, S/D/I ve oranı aynı üretti. Sabit referans toplamı 1137; hiçbir başarısız/atanmamış kelime paydadan çıkarılmadı.
   M15 Resmî [faster-whisper v1.2.1 kaynağı](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py), kelime zamanlarının cross-attention/DTW ile üretildiğini ve decoder ilerlemesinin son kelime zamanından etkilenebildiğini gösteriyor; genel bir gerçek zaman garantisi vermiyor. Bu mekanizma yeniden çözümleme adaylarının gerekçesiydi, başarı iddiası değildi.
   M16 [MeetEval](https://github.com/fgnt/meeteval) ve [birincil cpWER açıklaması](https://www.isca-archive.org/interspeech_2024/boeddeker24_interspeech.pdf), konuşmacı başına metin birleştirme ve en düşük permütasyon WER yaklaşımını destekliyor. Bu araştırmada yeni paket kurulmadı; küçük akış sayısında bağımsız tam sayım kullanıldı.
   M17 [OpenSLR SLR12](https://www.openslr.org/12/) İngilizce okuma corpus'u ve CC BY 4.0 lisansını doğruluyor; sonuçlar Türkçe doğal toplantı, farklı mikrofon veya elli konuşmacı başarısı değildir.
   **AÇIK**
   M18 D'deki ls-700 yalnız ilk 3 saniyesiyle kullanıldığı için tam resmî cümle metni doğru kısmi referans değildir; D bu sözcük ölçümünde açıkça puanlanmadı. Elle doğrulanmış kelime zamanları olmadığından gerçek word-timestamp error, DER/JER veya konuşma süresi recall iddia edilmedi.
   M19 Onarımın leksik kazancını güvenle kullanmak için kısa konuşmacı dönüşlerinin ayrımı ayrıca düzeltilmeli; yalnız zaman baskınlığı ölçüsü eksik metinle yapay biçimde iyileşebilir. Başlangıç ASR'si korunarak daha geniş kişi sayısı incelemesi ayrı yürütülür.
   **YAN-ETKİ**
   M20 Ignore kapsamındaki `outputs/2026-09-11-accuracy-audit/` dizinine protokoller, özel metin/zaman anlık görüntüleri, helper'lar ve sonuçlar; bu kalıcı dizine yalnız sadeleştirilmiş rapor ve aggregate JSON yazıldı. Üretim kodu, model ağırlığı, bağımlılık, veritabanı içeriği ve uygulama çalışma ayarı bu alt görevde değiştirilmedi; GPU kapsayıcıları tamamlandı ve kaldırıldı.
