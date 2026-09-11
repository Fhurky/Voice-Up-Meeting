# Koşum raporu — 2026-09-11 · Yerel toplantı başlatıcısının model hazırlığını beklemesi.

1. Sonuç: Hazır model doğrulanmadan uygulama bağlantısının yazılması düzeltildi — birim 20 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Başlatıcı L1, çalışan modelin özel HTTP kontrolü L2.
2. Koşulan: Windows PowerShell 5.1, gerçek inert `docker.exe` işlemleri ve yerel Docker Desktop RTX 4060; `kt-vibecoding-python-web-v2`.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `pytest tests/test_spark_startup.py -q -k 'local_meeting_startup or local_meeting_readiness'` — RED | 8 başarısız; başlangıçta sıfır model kontrolü ve eksik yardımcılar. İlk timeout assertion'ı yanlış nedenle geçiyordu, beklenen hata kodu/gerçek probe koşuluyla güçlendirildi. |
   | `pytest tests/test_spark_startup.py -q -k local_meeting_readiness_deadline` — RED | Güçlendirilen timeout regresyonu da başarısız; toplam 9 yeni davranış için RED gözlendi. |
   | `pytest tests/test_spark_startup.py -q -k 'local_meeting_startup or local_meeting_readiness or meeting_selection or local_refreshes or explicit_local or powershell_file or spark_intent'` — GREEN | 20 başarılı, 11.097 saniye; yeni davranışlar, Local/Spark seçimi, nginx yenilemesi ve gerçek PowerShell 5.1 `-File` Türkçe/BOM yüklemesi. |
   | `black tests/test_spark_startup.py`; `ruff check tests/test_spark_startup.py`; `git diff --check` | Başarılı; başlatıcının UTF-8 BOM işareti korundu. |
   | `pytest tests/test_spark_startup.py -q -k 'local_meeting_startup or local_meeting_readiness'` — biçim sonrası | Yeni 9 regresyon tekrar başarılı. |
   | Kaynaktan AST ile alınan üç başlatıcı yardımcısı, gerçek Compose `exec` ile `/meeting-ready` | 0.628 saniyede gerçek CUDA ve sabit Community-1 / Whisper / ECAPA kimlikleri doğrulandı; süreç 0 döndü. |

3. Maddeler:

   **KUSUR**
   M1 Compose `up` sonrası model yüklenmesi bitmeden bağlantı yazılıyordu; etkin Local meeting modunda `Wait-LocalMeetingReady` bağlantıdan önce çağrılır, 180 saniyelik bütçe biterse hazır sonucu verilmez.
   **TUZAK**
   M2 Kontrol yalnız konteyner içinde sabit loopback HTTP adresini kullanır; anahtar mevcut ortamdan okunur, proxy/redirect kullanılmaz, yanıt 4096 byte ile sınırlanır ve ham stderr gösterilmez. Yanlış cihaz, model, revision veya JSON türü kabul edilmez.
   **GÖZLEM**
   M3 Canlı kontrol zaten hazır ana model servisinde yürütüldü; yeni testler geçici modeller veya uygulama profilleri oluşturmadı. Bekleme sırasında ilk hatanın ardından gelen hazır yanıt native süreç testiyle gözlendi.
   **AÇIK**
   M4 Soğuk model yüklemesiyle baştan sona gerçek başlangıç tekrarı bu alt koşumda yapılmadı; çalışan model işleri kesilmedi. PowerShell 7, Spark ARM64 ve tam kalite kapısı ayrıca doğrulanmalıdır.
   **YAN-ETKİ**
   M5 Başlatıcı, startup testleri, çalışma rehberi ve plan/görevler güncellendi; test XML ve yalnız güvenli durum içeren canlı JSON kanıtı Git dışı `outputs/2026-09-10-meeting-delivery/local-meeting-readiness-*` altında saklandı.
