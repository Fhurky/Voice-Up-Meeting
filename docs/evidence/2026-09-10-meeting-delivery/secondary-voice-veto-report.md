# Koşum raporu — 2026-09-11 · Son seçilen PCM üzerinde ikinci ses vetosu.

1. Sonuç: Üretim vetosu CPU üzerinde 48/48, RTX 4060 üzerinde 19/19 gerçek model kontrolünde beklenen kararı ve donmuş araştırma sonucunu korudu — birim 194 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Sabit profil `kt-vibecoding-python-web-v2`, Python 3.13, çevrimdışı yerel Docker; kaynak ve model kimlikleri, bütün vaka sonuçları ve ham kanıt hashleri [secondary-voice-veto-results.json](secondary-voice-veto-results.json) içinde.

   | Koşu | Gözlenen sonuç | Süre / ortam |
   |---|---|---|
   | İlk `.45` araştırma vetosu | 17 kontrolün 14'ü doğru; 3 karışım kaçtı, 11 referansta yanlış ret yok | CPU 2 iş parçacığı, 60.949 sn |
   | Ayrı donmuş `.55` araştırması | 48/48 doğru; 40 referansta yanlış ret yok, ham karışım 6/6 ve hatalı seçilmiş PCM 2/2 ret | CPU, 126.531 sn |
   | Yeni guard testleri, RED | 10 başarısız / 1 başarılı; gerçek HTTP yolu karışık adayı yanlışlıkla `usable` döndürdü | `test_meeting_coherence.py`, 4.74 sn |
   | İlk GREEN | 11/11 başarılı | Aynı test dosyası, 3.11 sn |
   | Ek süre sınırı fikstürü | 14 başarılı / 1 başarısız; fikstürün seçilen sesi varsayılan 3 sn yerine 2.5 sn idi | Algoritma değiştirilmeden fikstür düzeltildi |
   | Son dar testler | 15/15 başarılı; tam 3 sn / bir kare eksik ve `.5499` / `.5501` sınırları dahil | 3.25 sn |
   | Tam özel çıkarım paketi | 194/194 başarılı, 0 atlanan; son 15 guard testi dahil | `coherence-provider-all.xml`, 12.481 sn |
   | Black / Ruff | 3 dosya uygun | Guard, entegrasyon ve test dosyası |
   | Üretim guard CPU | 48/48 doğru ve araştırmayla eşdeğer; ağ girişimi 0 | 123.757 sn hesaplama, 135.625 sn konteyner, tepe RSS 1,064,726,528 bayt |
   | Üretim guard GPU | 19/19 doğru ve araştırmayla eşdeğer; ağ girişimi 0 | RTX 4060 Laptop / CUDA 0, 49.055 sn hesaplama, 62.078 sn konteyner |

3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: Bütün bağlam ve 3 saniyelik ana kontroller geçse bile son örnekte ikinci ses bulunabiliyordu; `meeting_memory.py` artık son PCM'de vetoyu kalıcı 192/256 vektörlerinden önce çalıştırıyor, ret gövdesinde çıktı hash'i/vektör yok ve süre/aralıklar sıfır.
   **TUZAK**
   M2 İlk `.45` deneyi başarısız olarak korundu; `.55` seçimi ayrı protokolle ve 29 ek referans ile iki gerçek hatalı son örnek eklenerek sonuçlardan önce donduruldu. Tek bir koşu sırasında eşik ayarlanmadı.
   M3 B/C ve `same32` kaynakları diğer kontrollerle örtüşür; 12 `known_query2/3` kaydı önceki 17 guard örneğinin konuşma parçalarından ayrıdır, fakat yeni kişiler, farklı mikrofonlar veya bütün araştırmalardan bağımsız veriler değildir.
   M4 Kronolojik örtüşmesiz pencere seçimi toplam olası sesi ençoklamaz; ek testteki iki aralığın seçilen toplamı 2.5 sn idi. Tam 3 sn ve bir kare eksik kontrolleri gerçek seçilen süreye göre kuruldu; üretim algoritması değiştirilmedi.
   **GÖZLEM**
   M5 FA.15 hatalı son örneği `7551545e…`: 22.5734375 sn içinde 6.53275 sn yabancı ses; merkez cosine CPU `.5475091564`, GPU `.5474947829`, ikisi de ret. Eşiğe yaklaşık `.0025` uzaklık geniş bir genelleme payı sayılmadı.
   M6 Eski FA.07 hatalı son örneği `d6f95bdf…`: 21.7975625 sn içinde 5.53 sn yabancı ses; CPU `.3480653794`, GPU `.3479361281`, ikisi de ret. GPU grubunda A'nın beş örneği ve yeni 12 saf kayıt yanlış reddedilmedi.
   M7 Gerçek `LocalMeetingModels.voice_embedding` yönteminin cihaz taşıma/işlem ayarları ve cihazdaki `OfflineSilero.speech_spans` kullanıldı; ham vektör kaydı yok. GPU tepe ayrılmış bellek 55,118,336, rezerve bellek 79,691,776 bayt; süreç RSS 1,826,107,392 bayt.
   **AÇIK**
   M8 Bu rapor bileşenin L1 ve gerçek model eşdeğerlik kanıtıdır; çalışan uygulamada değişmeyen A/B/D/C yükleme, profil hafızası, en az %99 saflık, Spark ARM64 ve temsil edici Türkçe/50 kişilik kalite ayrıca doğrulanmalıdır.
   **YAN-ETKİ**
   M9 Yeni `meeting_coherence.py`, `test_meeting_coherence.py` ve mevcut `meeting_memory.py` entegrasyonu yazıldı; arındırılmış bu rapor/JSON dışındaki betikler, kaynak sesler ve ayrıntılı sonuçlar yok sayılan `outputs/secondary-two-means-research/` altında kaldı. Profil/veritabanı yazımı, commit veya push yapılmadı.
