# Koşum raporu — 2026-09-11 · Bağımsız 50 kişilik kaynak hazırlığı ve tam kaynak doğrulaması

1. Sonuç: 50 tanınacak ve 20 hiç kaydedilmeyecek kişi için 190 kayıt ile üç 50 kişilik toplantı hazırlandı; kaynak ve referans doğrulaması geçti — birim 57 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok. Bu koşu model doğruluğunu ölçmez.
2. Koşulan: Yerel Windows hazırlama ortamı, Python 3.12.10, mevcut NumPy/SoundFile; uygulamanın sabit profili `kt-vibecoding-python-web-v2` değişmedi. Model, GPU, ağ, uygulama HTTP uçları ve veritabanı kullanılmadı.

   | Koşu | Komut / kanıt | Gözlenen sonuç |
   |---|---|---|
   | Yeni hazırlayıcı RED | `pytest tests/test_prepare_meeting_identity_evaluation.py` | İlk 10 testte olmayan modül nedeniyle 10 hata; toplantı türetmesi eklenmeden 10 başarılı / 2 başarısız; terminal kanıtı |
   | GREEN ve komşu regresyonlar | `.venv/Scripts/python.exe -X utf8 -m pytest tests/test_prepare_meeting_identity_evaluation.py tests/test_public_speaker_dataset.py tests/test_prepare_meeting_evaluation.py -q --tb=short --junitxml=outputs/meeting-identity-independent-v1/preparation-tests.xml` | 15 yeni + 42 mevcut = 57 başarılı, 0 atlanan; 15,196 saniye |
   | Biçim / lint | `ruff format` ve `ruff check`, yeni hazırlayıcı ve test dosyası | 2 dosya biçimlendirildi; lint başarılı; ardından 57 test tekrar geçti |
   | Gerçek corpus hazırlığı | `.venv/Scripts/python.exe -X utf8 scripts/prepare-meeting-identity-evaluation.py --meeting-sizes 50` | 190 / 190 kayıt, 0 hazırlama hatası; 613 tekil kaynak utterance; 21.845 referans kelime |
   | Bağımsız PCM / referans denetimi | `.venv/Scripts/python.exe -X utf8 outputs/meeting-identity-independent-v1/audit.py` | 190 kayıt + 3 toplantı geçti; FLAC → PCM → WAV tam bayt eşitliği, kaynak kapsamı ve resmî metin hashleri doğrulandı |
   | Geçmiş corpus envanteri | Beş yerel split, üç eski manifest, 133 seçili protokol/sonuç/durum JSON dosyası | 39.665 / 39.665 ses dosyasının tekil metin referansı mevcut; eksik/fazla/tekrar ID 0; yeni seçimin eski kişi/kaynak/kayıt hash çakışması 0 |

   | Hazırlanan toplantı | Kişi | Süre | Tam kaynak utterance | Referans kelime |
   |---|---:|---:|---:|---:|
   | A — ilk kayıt | 50 | 2.129,659875 sn | 161 | 5.724 |
   | B — geri dönüş 1 | 50 | 2.150,430125 sn | 160 | 5.716 |
   | C — geri dönüş 2 | 50 | 2.152,875 sn | 164 | 5.741 |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 `public-speaker-holdout-v2/test.json`, 2026-09-09 12:56:16–13:01:21 UTC arasında 302 gerçek işte kullanılmıştır; A/B/D/C ve guard48 de eski calibration içindeki aynı altı kişiden gelir. Bu kaynaklar yeni kör holdout sayılmaz.
   M2 35,01–52,40 saniyelik hazırlanan kayıt süreleri kullanılabilir konuşma süresi değildir; modelin ses etkinliği ve hafızaya kabul kuralları uygulanmadı. Hazırlanan 50 kişi, uygulamanın 50 kişiyi başarıyla kaydettiği anlamına gelmez.
   M3 5/10/20/50 galeri tanımları aynı 140 sorguyu paylaşır; galeri dışında kalan seçilmiş kişiler ile 20 hiç kaydedilmeyecek kişi ayrı sayılır. Bu tanımların hazırlanması, 560 sorgunun çalıştırıldığı iddiası değildir.

   **GÖZLEM**

   M4 Üç tarihsel manifest toplam 210 ayrı kişi içerir ve kendi aralarında kişi/utterance/kayıt SHA çakışması yoktur. Yeni corpus, kalan 181 kişinin 78 üç-bölümlü adayından 50 kişi ve kalan en az iki-bölümlü adaylardan 20 kişi seçer; model sonucu seçimde kullanılmaz.
   M5 Yeni 190 kayıt; 50 enrollment, 100 known-query ve 40 never-enrolled-query içerir. Bilinen kişiler üç ayrı bölüm, diğer kişiler iki ayrı bölüm kullanır; 613 tekil FLAC hashinin PCM içeriği ve resmî referansları bağımsız denetimde eşleşti.
   M6 Toplantılar tam utterance sınırlarında sırayla konuşma ve aralarda 0,25 saniye sessizlik kullanır; her seçili klip frame'i tam bir kez taşınır. Kaynak içi sessizlikler insan etiketli konuşma sınırı sayılmaz.

   **AÇIK**

   M7 Gerçek uygulama kimlik precision/recall/F1, yeni kişi yanlış kabulü, çekinme, konuşmacı ayrımı ve kelime hata oranı bu hazırlık koşusunda ölçülmedi. Sonuçlar yalnız kaynak hazırlığı için L1 kanıtıdır.
   M8 Tüm 28.539 ham FLAC başlığının süre taraması tamamlanmadan durduruldu; kalan corpus için 72,167 saat yalnız yayımlanmış `CHAPTERS.TXT` toplamıdır. Seçilen 613 FLAC tamamen çözüldü; tam arşiv hashinin bu koşuda yeniden okunduğu iddia edilmez.
   M9 Türkçe doğal toplantı, farklı mikrofon/gün ve modelin eğitim kişileriyle bağımsızlık kanıtı yoktur. Yerel Türkçe pilot manifestinin 32 ses yolu mevcut değildir; gerçek Türkçe gözlemde insan referansı bulunmaz.
   M10 Tam kalite kapısı bu dar hazırlık adımında çalıştırılmadı; ana teslim kapısı koordinatörün kapsamındadır. Konuşma sınırları için RTTM/CTM/UEM referansı bulunmadığından gerçek DER/JER bu corpus hazırlığından türetilemez.

   **YAN-ETKİ**

   M11 [Dondurulmuş protokol](../../../specs/speaker-identity/PRDs/002-long-recording-analysis/corpus-protocol.md), yeniden kullanılabilir hazırlayıcı ve 15 test eklendi; yeni ses/metin, manifest ve JUnit kanıtı yalnız ignored `outputs/meeting-identity-independent-v1/` altında üretildi. Eski corpus ve uygulama verileri değiştirilmedi.
   M12 [Sanitize edilmiş sonuç](independent-corpus-preparation-results.json) tam kaynak/araç hashlerini taşır. Klip protokol SHA-256: `6279e3babb2147139dc65bc5b56730b9cf7a41b62b07b01eedff51b223cb39a9`; toplantı protokol SHA-256: `b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50`.
