# Koşum raporu — 2026-09-11 · Konuşmacı numaraları ve gerçek başarısız model sonucunun görünümü.

1. Sonuç: Konuşmacı etiketleri Türkçe ve İngilizcede 1’den başlıyor — birim 89 başarılı / tarayıcı 1 başarılı / atlanan 1; karar bekleyen: yok. Etiket gösterimi L2; başarılı konuşmacı hafızası kabulü değildir.
2. Koşulan: `kt-vibecoding-python-web-v2`; Docker Compose ön yüzü, gerçek üretilmiş API tipleri ve yerel 8081 uygulaması.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `scripts/stack.sh exec -T frontend sh -lc 'npm test -- src/components/MeetingResults.test.tsx'` | Önce 4 başarılı / 2 başarısız; düzeltmeden sonra 6/6 başarılı. |
   | `scripts/quality-gate.sh frontend` | Son koşumda lint, tip kontrolü, üretim derlemesi, 20 dosyada 89/89 test ve üretilmiş API tipi drift kontrolü başarılı; çıkış 0. |
   | Sabit yerel Node ile `node e2e/speaker-identity/06-meeting-observation.mjs` | Node 22.23.2, Playwright 1.62.1, Chromium Headless Shell rev1234; gerçek HTTP yanıtları ve normal kullanıcı oturumuyla 1/1 başarılı. |
   | `05-meeting-memory.mjs` | Başarılı gerçek model/hafıza ön koşulu sağlanmadığı için bu koşumda çalıştırılmadı. |

3. Maddeler:

   **KUSUR**
   M1 API sıfır tabanlı `ordinal` değerinin doğrudan gösterilmesi “Konuşmacı 0” üretiyordu; `MeetingResults.tsx` kart, metin ve ad düzenleyici etiketlerini bir artırır. İki dilde 0→1 ve 49→50 regresyonları API değerinin değişmediğini korur.
   M2 İlk kalite kapısında test sorgusunun desteklenmeyen `exact` özelliği tip hatası verdi; Testing Library sorgusundan kaldırıldı ve tam ön yüz kapısı yeniden geçti.
   **TUZAK**
   M3 İlk canlı etiket kontrolü Docker Desktop/Vite dosya izleme önbelleğindeki eski modülü gördü; gerçek HTTP modül kaynağıyla doğrulandı. Yalnız ön yüz yeniden başlatıldıktan sonra aynı kalıcı senaryo geçti.
   M4 Dil React oturum durumundadır; uygulama içi gezinmede korunur, tam sayfa açılışında varsayılana döner. 05 senaryosunun yükleme yardımcısı Türkçe alan sorgularından önce dili açıkça Türkçeye geçirir.
   **GÖZLEM**
   M5 Gerçek A sonucunda işlem `succeeded`, 11 konuşmacı ve 11 `profile_pending`, galeri toplamı 0 olarak gözlendi. Beklenen beş kişiye karşı bu sonuç model kalite başarısızlığıdır; arayüzün sonucu doğru göstermesi tanıma başarısı sayılmaz.
   M6 Salt okunur 06 senaryosu API ilk `ordinal=0` iken iki dilde 1 ve 11 etiketlerini, 0 etiketinin yokluğunu ve hafızaya kaydedilmeme durumunu doğrular; öncesi/sonrası toplantı, konuşmacı ve galeri durumları eşittir.
   **AÇIK**
   M7 05 senaryosundaki gerçek 5→5→6 hafıza, elle ad verme ve yeni kişi kabulü açık kalır. 50 kişilik doğal Türkçe toplantı doğruluğu bu koşumda ölçülmedi.
   M8 Bu dar koşum tam `scripts/quality-gate.sh all` veya güvenlik taraması yerine geçmez; bütünleştirilmiş son kaynak için ana ajan ayrı kapı çalıştıracaktır.
   **YAN-ETKİ**
   M9 Sonuç bileşeni, sıfır tabanlı test fixture’ları ve iki senaryo güncellendi; API şeması ve üretilmiş tipler değiştirilmedi. Kalıcı kullanıcı verisi yazılmadı.
   M10 Son 89-test JSON kanıtı ve tarayıcı çıktısı Git dışı `outputs/2026-09-10-meeting-delivery/frontend-tests.json` ve `06-meeting-observation-browser.txt` dosyalarındadır. Alternatif sabit tarayıcı kurulumu önceki raporda kayıtlıdır; kabul edilmiş çevrimdışı bundle kanıtı olarak sunulmaz.
