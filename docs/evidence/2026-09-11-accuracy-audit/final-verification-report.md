# Koşum raporu — 2026-09-11 · Son belgelerin, kayıtlı sonuçların ve kaynak sabitlemesinin bağımsız denetimi

1. Sonuç: Son belge paketi, yerel dosya bağlantıları, sabit rapor yapıları ve kayıtlı sonuçların kaynakları tutarlı bulundu — belge doğrulama paketi 1 başarılı / yeni birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Bu salt okunur denetim ana 2.035 test toplamına eklenmez.
2. Koşulan: `kt-vibecoding-python-web-v2`; yerel Windows/Python 3.13 ve Git. `outputs/2026-09-11-accuracy-audit/final-document-verification.py --output outputs/2026-09-11-accuracy-audit/final-document-verification-results.json` mevcut dosyaları ve önceki sonuç kayıtlarını okudu; uygulama, model, GPU, veritabanı veya kalite kapısı yeniden çalıştırılmadı.

   | Denetim | Gözlenen kapsam |
   |---|---|
   | Yeni/değişmiş Markdown | 38 dosya; ilgisiz `plans/SPEECH_SEGMENT_DIAGNOSIS.md` inceleme kapsamından çıkarıldı ve korundu |
   | Yerel dosya bağlantıları | 160 hedef mevcut; özel kimlik bilgisi veya `.private` belgesine Markdown bağlantısı bulunmadı |
   | Sabit rapor yapısı | 29 raporda 1–3 bölüm sırası, beş grup, kesintisiz M numaraları ve sonuçtaki başarı/atlama/karar alanları doğrulandı |
   | Çalışma ağacı | `git diff --check` çıkış 0; mevcut CRLF→LF bilgi uyarıları ayrıca kaydedildi; stage/commit/push yapılmadı |
   | Kaynak sabitlemesi | Final 190-klip protokolündeki 22 backend dosyasının gerçek byte hashleri ve tamamlanma kaydı eşleşti; aynı `d14a4e65159a…` model imajı korundu |
   | Test sayısı | XML test kimlikleri ve gerçek `KT_GATE_TESTS` kayıtları: 1.130 farklı kök + 595 backend + 89 ön yüz + 221 çıkarım = 2.035; bir Windows atlaması ve ayrı tamamlanamayan güvenlik taraması görünür kaldı |
   | Gerçek toplantılar | Eski/yeni A: 803→658/5.724; B: 462/5.716; C: 713/5.741. Aynı sekiz sağlayıcı çıktısı ve 343 metin satırı kanıtı, 37 örneğin en az %99,789 kaynak sahipliği ve B/C değişmezliği eşleşti |
   | Kontrollü galeri | [Bağımsız son yeniden sayım](nested-protocol-review-report.md): 190 klip, aynı 140 sorgu × 4 aşama; 48 sayaç/oran özeti eşleşti. Son hedef 50 / kabul edilen 49, doğru 95/100, yanlış pozitif 0; başarısız kabulün iki sorgusu paydada kaldı |
   | Bütün C deneyi | Bütün 52/55 grup korundu; kaynak azınlık süresi azalsa da bölünme 1→4 ve cpWER 713→774/5.741 arttı. Altı sabit koşuldan üçü başarısız; aday üretime alınmadı |
   | Ortamın geri açılması | Kayıtlı özel model ve genel veritabanı hazır olma istekleri HTTP 200; aynı imaj, profil yazısı 0. Bu denetim yeni HTTP isteği göndermedi |

   Ham tekrar üretilebilir kayıt, kullanılan dosyaların SHA-256 özetleri ve yerel bağlantı/rapor listeleri `outputs/2026-09-11-accuracy-audit/final-document-verification-results.json` içinde bulunur. Dosya kendisine hash üretmez; bu rapor dahil girdilerin gerçek hashlerini kaydeder. İlk tamamlanmış ön kontrol `final-document-verification-initial.json`, iki yardımcı okuyucu düzeltmesinin kaydı `final-document-verification-observer-note.json` olarak aynı ignored dizinde korunur.

3. Maddeler:

   **KUSUR**

   M1 Denetim yardımcısı ilk iki denemede renkli insan çıktısını ve iki taraflı metin-satırı sayısını yanlış biçimde bekledi; sabit kapı kayıtları ve gerçek `[343,343]` sözleşmesi okunarak düzeltildi. Bunlar uygulama veya önceki kalite kapısı hatası değildi; başarısız yardımcı çıkışları observer notunda korunur.

   **TUZAK**

   M2 Belge denetimi yeni doğruluk deneyi değildir. 14 ek CPU kontrolü, 48 sonuç karşılaştırması, ilişkili 560 galeri kararı ve bu dosya denetimi ana 2.035 farklı otomatik test sayısına eklenmez.
   M3 Kaynak aralığı sahipliği insan etiketli konuşmacı ayrım hatası değildir; temiz profil örnekleri C'deki yanlış kişiye atanmış 22,33 saniyelik sahne hatasını kapatmaz. Kontrollü galeri skorları tam toplantı veya otomatik kayıt başarısı sayılmaz.

   **GÖZLEM**

   M4 İncelenen belgelerde belirli token/özel anahtar biçimleri, ham UUID, 192/256 uzunluğunda sayısal vektör dizileri veya özel belge bağlantısı bulunmadı; içerik, kimlik bilgisi ve vektörler çıktıya kopyalanmadı. Bu sınırlı kontrol onaylı güvenlik tarayıcısının yerine geçmez.
   M5 Son genel rapor, kontrollü galeri başarısız kabulünü, elli kişilik toplantı eksiklerini ve reddedilen bütün-kayıt adayını açıkça korur; kullanılmayan kaynaklar veya doğrulanamayan satırlar başarı paydasından çıkarılmadı.

   **AÇIK**

   M6 `gitleaks` bulunamadığı için önceki güvenlik kapısı çıkış 2 ile tamamlanamamıştır; bir Windows sembolik bağ testi hâlâ atlanmıştır. Dış web siteleri ve Markdown bölüm çapaları bu yerel dosya-bağlantısı kontrolünde denenmedi.
   M7 Doğal Türkçe toplantı ve temsilî kullanıcı kabulü için yeni kanıt yoktur; elli kişinin tamamını güvenilir kaydetme/tanıma hedefi karşılanmış sayılmaz. Model ve tam kapı tekrarları, kaynaklar değişmediği için bu son belge denetiminde çalıştırılmadı.

   **YAN-ETKİ**

   M8 Yalnız ignored denetim yardımcısı/çıktıları, bağımsız galeri raporunun son sonuç eki, bu rapor ve ana kanıt indeksindeki bağlantı yazıldı. Üretim kaynağı, model, ses, iş verisi ve ilgisiz kullanıcı planı değiştirilmedi.
