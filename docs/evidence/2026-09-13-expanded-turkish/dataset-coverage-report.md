# Koşum raporu — 2026-09-13 · Türkçe test havuzunun dosya ve çözümlenmiş ses bakımından bağımsız kapsam denetimi

1. Sonuç: 3.256 dosyada 19.544 doğrulama başarılı, 0 başarısız; bayt ve tam çözümlenmiş örnek düzeyinde tekrar bulunmadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows, yerel Python 3.12, SoundFile 0.13.1 / libsndfile 1.2.2; yalnız CPU ve mevcut dosyalar. Sabit ürün profili `kt-vibecoding-python-web-v2` korunuyor. `.venv/Scripts/python.exe -` üzerinden mevcut manifest okuyucuları ve SoundFile ile tek denetim; çıktı [dataset-coverage.json](dataset-coverage.json).

   | Grup | Klip | Süre (saniye) | Ses biçimi | Aynı bayt / aynı çözümlenmiş ses grubu |
   | --- | ---: | ---: | --- | ---: |
   | FLEURS Türkçe resmî test | 743 | 9.380,22 | WAV / float32 | 0 / 0 |
   | Yeni MediaSpeech Türkçe | 2.433 | 34.852,10 | FLAC / PCM16 | 0 / 0 |
   | Önceki MediaSpeech Türkçe | 80 | 1.157,20 | FLAC / PCM16 | 0 / 0 |
   | Toplam | 3.256 | 45.389,52 | Mono 16 kHz | 0 / 0 |

   Her klipte ses hash'i, referans dosyası hash'i, manifest/referans metin
   eşleşmesi, ses başlığı, sonlu çözümlenmiş örnekler ve tekil klip kimliği
   doğrulandı: 6 × 3.256 = 19.536 kontrol. Üç beklenen grup büyüklüğü, üç
   sabit arşiv/TSV boyut-hash denetimi ve iki FLEURS metadata kapsam koşulu
   ile toplam 19.544 kontrol tamamlandı. Çözümlenmiş örnekler üzerinde
   743 + 2.433 + 80 = 3.256 farklı hash bulundu; üç grup çiftinde de
   ortak dosya hash'i ve ortak çözümlenmiş ses hash'i sıfırdı.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Denetim tam örnek eşitliğini ölçer; yakın kopya, aynı kaydın farklı kesiti, ses düzeyi değişimi veya yeniden kodlama etkisine dayanıklı benzerlik taraması değildir. Farklı dosya, farklı kişi veya oturum anlamına gelmez.

   M2 FLEURS test TSV hash'i yeniden doğrulandı: 743 `MALE` satırı ve 329 farklı cümle kimliği var. Cümle kimliği kişi kimliği değildir; kadın sesi kapsamı iddia edilmez.

   **GÖZLEM**

   M3 Bu genişlemede 3.176 farklı yeni klip / 44.232,32 saniye (yaklaşık 12,29 saat) hazır. Önceki 80 klip ayrıca korunuyor; genişletilmiş MediaSpeech ile ne dosya ne çözümlenmiş örnek hash'i kesişiyor.

   M4 Sesler SoundFile ile mono 16 kHz sonlu float32 olarak çözüldü; küçük uçlu örnek baytlarında işaretli sıfır pozitif sıfıra eşitlendi. SHA-256, `voiceup-decoded-mono-f32le-v1` öneki, örnek hızı/kanal/örnek sayısı ve bu örnek baytlarını kapsar.

   M5 Toplu JSON SHA-256: `f93948e1af897216fa0cad028e7adf1fbebb21563686d219ee1b1f2dfb0735a2`; kaynak manifest hashleri, süreler ve grup çiftlerinin sıfır tekrar sonuçları aynı dosyada.

   **AÇIK**

   M6 Bağımsız Türkçe kişi/oturum kapsamı, model eğitim verisiyle kesişme ve yakın kopya denetimi ölçülmedi. Bu denetim model çıkarımı veya doğruluk puanı üretmez; bunlar ayrı gerçek deney kanıtlarıdır.

   **YAN-ETKİ**

   M7 Yalnız bu rapor ve izinli toplu `dataset-coverage.json` eklendi. Kaynak ses/metin, uygulama/veritabanı, GPU, model ve `results.md` değiştirilmedi; ham metin/kişi kimliği yayımlanmadı.
