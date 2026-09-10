# Koşum raporu — 2026-09-09 · Değerlendirme raporunun bağımsız sayısal ve gizlilik incelemesi

1. Sonuç: Rapor hesapları doğrulandı ve geri dönüş sonuçlarındaki ayrım eksikliği düzeltildi — birim 54 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kontrol | Ortam ve kanıt | Sonuç |
   | --- | --- | --- |
   | Değerlendirici ve raporlayıcı regresyonları | Windows Python 3.13; `pytest tests/test_public_speaker_report.py tests/test_public_speaker_evaluation.py -q`; [son birleşik JUnit](evaluation-tool-tests-final.xml) | 11 raporlayıcı + 43 değerlendirici = 54 başarılı; ana görevin son 77 testlik paketinin altkümesidir, toplama yeniden eklenmez. |
   | Bağımsız sayısal karşılaştırma | Tamamlanmış 142 ve 302 işlemli iki özel kalibrasyon çıktısı; manifestten yeniden hesaplanan paydalar | 22 doğrulama geçti: politika, planlanan sorgular, doğru/yanlış kabul oranları, hata sınırları, konuşmacı kümesi aralıkları ve p95. Bu sayı ek birim test sayısı değildir. |
   | Son kör testin bağımsız denetimi | Tamamlanmış 707 işlem ve 302 tekil kayıt; [anonim denetim çıktısı](final-metrics-audit.json), [yayımlanan sonuç](test-summary.json) | 98 doğrulama geçti: manifest paydaları, gerçek galeri, kimlik kararları, hata sınırları, bootstrap noktaları, gecikme yüzdelikleri, geri dönüş ve kaynak özeti eşleşti. Bu doğrulamalar [819 tekil otomatik test](test-inventory.json) sayısına eklenmez. |
   | Gizlilik incelemesi | [Tarihli ve dosya özetlerine bağlı inceleme](privacy-review.json) | İlk 36 dosyada ve sonraki 46 dosyalık görüntüde eşleşme yok; ikinci kontrolde 9 sır, 57 özel kimlik, 53 profil adı ve 100 veri kümesi konuşmacı kodu karşılaştırıldı. |
   | Statik kontrol | Değişen dört kaynak/test dosyasında Ruff ve `git diff --check` | Başarılı. |

3. Maddeler:

   **KUSUR**
   M1 Geri dönüş özeti yanlış kişiye kabulü belirsiz/bilinmeyen reddinden ayırmıyordu; ayrı sonuç, kalite hatası, bekleyen ve hiç başlatılmamış planlı sorgu sayaçları eklendi. Altı yeni raporlayıcı kontrolü önce başarısız, düzeltmeden sonra başarılı oldu.

   **TUZAK**
   M2 Eski raporların planlanmış geri dönüş toplamı yoktur; yeni raporlayıcı bu alanları `null` bırakır. Eski yayımlanmış kalibrasyon özeti değiştirilmedi.
   M3 Gecikme, ilk başlama ile terminal sonuç arasındaki iş süresidir; kalite hataları ve varsa yeniden denemeler dahildir. Saf GPU hesaplama süresi değildir; [protokolde](../../PUBLIC_DATASET_PROTOCOL.md) açıklandı.

   **GÖZLEM**
   M4 Bilinen sorguların kalite hataları paydada kaldı; bilinmeyenlerde gözlenen yanlış kabul ile çözümlenmemiş durumların üst sınırı ayrıldı. Konuşmacı bazında bootstrap, aynı kişinin sorgularını birlikte örnekliyor; sıfıra çöken aralık üretim güvencesi sayılmıyor.
   M5 Kör testte 5/10/20/50 planlanan kişi için 2/4/10/29 profil oluştu; doğru tanıma 6/15, 11/30, 28/60 ve 77/150. Yanlış kimlik sıfır; her aşamadaki aynı 100 bilinmeyen sorgunun 80'i bilinmeyen, 20'si kalite hatasıdır; dört bağımsız deney sayılmaz.
   M6 Elli kişilik aşamada 26 bilinen sorgu kalite hatasıyla tamamlandı; geri dönen kişinin kaydı ve sorgusu da başarısızdır. Tüm 707 işlem ilk denemede terminal duruma geldi; işin tamamlanması doğru kimlik üretildiği anlamına gelmez.

   **AÇIK**
   M7 Gizlilik kaydı yalnız listelenen dosya özetleri içindir; kör test sonucu ve son rapor gibi sonradan eklenen/değişen dosyalar ayrıca incelenmelidir. Bu kontrol eksik onaylı güvenlik tarama ortamının yerine geçmez.
   M8 Elli planlanan kişide yüzde 51,33 doğru tanıma ve başarısız geri dönüş, yüksek doğruluk hedefinin sağlandığına kanıt değildir. İngilizce okuma verisi Türkçe toplantı kabulünün yerine geçmez; kör sonuçlara bakılarak bu incelemede politika değiştirilmedi.

   **YAN-ETKİ**
   M9 Raporlayıcı/değerlendirici ile iki test dosyası güncellendi; bu rapor, gizlilik kaydı, son sayısal denetim JSON'u ve kısa gecikme açıklaması eklendi. Canlı günlükler, model politikası, uygulama verisi ve geçmiş deney sonuçları bu incelemede değiştirilmedi.
