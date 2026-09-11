# Koşum raporu — 2026-09-11 · Gerçek model başarısızlığındaki sayısal ölçülerin korunması ve arayüz gözlemi.

1. Sonuç: Hata raporlama regresyonu ve gerçek sonucun arayüzde gösterimi geçti; model kabulü başarısız kalır — birim 35 başarılı / tarayıcı 1 başarılı / atlanan 0; karar bekleyen: yok. Raporlama L1, mevcut sonucu salt okunur arayüzde gözleme L2; başarılı hafıza kabulü yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; yerel Python test ortamında gerçek loopback HTTP fixture, Windows Node 22.23.2 / Playwright 1.62.1 / Chromium Headless Shell rev1234 ile gerçek 8081 uygulaması.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `pytest tests/test_run_meeting_evaluation.py -k 'terminal_mismatch or gallery_observation or invalid_observed' -q` | Düzeltmeden önce 4/4 başarısız: terminal durum ve observed ölçüleri kayboluyordu. |
   | `pytest tests/test_run_meeting_evaluation.py -q` | Düzeltme sonrası 35/35 başarılı; mismatch, profil sayısı okuma hatası, geçersiz sayı ve gizli alan reddi dahil. |
   | `ruff check` ve `ruff format --check` ile runner ve test dosyaları | Başarılı. |
   | `node e2e/speaker-identity/06-meeting-observation.mjs` | Gerçek sıradan hesapla Türkçe/İngilizce 1/1 başarılı; mevcut A sonucu ve profiller değişmeden kaldı. |

3. Maddeler:

   **KUSUR**
   M1 Runner `source_or_speaker_count_mismatch` hatasından önce yalnız önceki `finalizing` durumunu tutuyordu; `record_terminal_observation` terminal durumu ve seçilmiş sayısal alanları önce state/report'a kaydeder.
   **TUZAK**
   M2 Uygulamadaki `succeeded` işleme tamamlanmasıdır; beş gerçek kişi için 11 etiket ve sıfır kalıcı profil doğru kimlik/hafıza kabulü değildir. Sayı ipucu verilmediğinden UI'daki `count_mismatch=false` bu bağımsız kalite RED sonucuyla çelişmez.
   M3 Profil toplamını okuma başarısız olursa gözlem `gallery_total=null` ve `gallery_observation_error=unavailable` tutar; ilk kaynak/konuşmacı sayısı hatasını başka hatayla değiştirmez.
   **GÖZLEM**
   M4 Mevcut `6e4a16d8-6ab0-4893-803d-7b0f5ea26e57` kaydı: 182.0250625 saniye, `succeeded`, 11 gözlenen konuşmacı, 11 `profile_pending`, 0 kalıcı profil. İki dilde ekrandaki sayılar gerçek HTTP sonucuyla eşleşti.
   M5 Yeni rapor projeksiyonu yalnız sabit durum, geçerli sayılar ve kaynak hash eşitliği içerir; transcript, kullanıcı adı, token, embedding veya keyfi DTO alanını kopyalamaz. Eşikler ve donmuş protokol değiştirilmedi.
   **AÇIK**
   M6 Eski `real-meeting-evaluation-v3.json` ve state dosyası tarihsel başarısızlık olarak korundu; başarılı A/B/D/C ve 5→5→5→6 hafıza kabulü bu koşumda elde edilmedi. Tam kalite kapısı güncel bütünleşik kaynaklarda ayrıca koşulmalıdır.
   **YAN-ETKİ**
   M7 Runner, testleri ve kayıtlı `06-meeting-observation.mjs` ile kalite manifesti/README güncellendi. Tarayıcı yalnız oturum açtı, GET ile okudu ve çıktı; toplantı/profil mutasyonu yapmadı.
   M8 RED/GREEN XML, `06-meeting-observation-browser.txt` ve yalnız sayısal `meeting-ui-observation.json`, Git dışı `outputs/2026-09-10-meeting-delivery/` altında saklandı; ham metin veya kimlik doğrulama bilgisi rapora eklenmedi.
