# Koşum raporu — 2026-09-11 · Hazırlanmış Spark şablonunun sabit hash denetiminin eşitlenmesi

1. Sonuç: Kabul edilmiş özel toplantı uçlarını içeren güncel şablon güvenli hazırlık denetimini geçti — birim 42 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: Yerel Windows PowerShell üzerinden `.venv/Scripts/python.exe -m pytest tests/test_spark_runtime_start.py --junitxml=outputs/2026-09-10-meeting-delivery/spark-template-green.xml`; gerçek geçici dosyalar ve Docker Compose'un ürettiği yapılandırma, süreç sınırında imza kısıtlı test doubles; gerçek Spark başlatılmadı.

   | Koşum | Sonuç |
   | --- | --- |
   | Yeni güncel-şablon RED | `spark_runtime_template_changed`: 1 başarısız, 42 seçilmeyen |
   | Hazırlanmış runtime GREEN | 42 başarılı, 1 atlanan; 6,32 saniye |
   | Ruff lint / biçim kontrolü | Yardımcı ve test dosyasında başarılı |
   | Korunan Compose SHA-256 | `d11d08cd927da330bdfe63a7ed15776da4d428ee4c9bc5504b9e8e32b7b9ce60` |
   | İncelenmiş güncel Nginx SHA-256 | `c9ba6d08fe8804e9fa1e818d97b34e60e4e3bdb3cc063ef842170fc005fc6ea8` |

3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: Yardımcı eski `8eea1b3b3e560e1f286c3418832ea074a89fd74677e276cf0fa2790c936e3c93` şablon hash'ini bekliyordu; gerçek güncel dosyaları kopyalayan testler Docker adımından önce reddediliyordu. Yalnız incelenmiş Nginx sabiti güncellendi.
   **TUZAK**
   M2 Şablon farkı yalnız GET `/meeting-ready`, POST `/v1/meeting-chunks` için 120 MiB/600 saniye ve POST `/v1/meeting-memory` için 36 MiB/600 saniye sınırlarını ekler; tam uç allowlist'i ve diğer yolların reddi korunur.
   M3 Çalışma anında yeni hash hesaplayıp kabul etme yoktur. Eski hazırlanmış uzak dosya hâlâ reddedilir ve ayrı yetkili hazırlama gerektirir; yardımcı uzaktaki şablonu kendiliğinden değiştirmez.
   **GÖZLEM**
   M4 Her iki şablonun değiştirilmesi Docker çağrısından önce reddedilmeye devam etti; gizli ayar, yetki, runtime kimliği, süre sınırı, yönlendirme ve güvenli hata çıktı testleri korundu.
   M5 RED/GREEN metin ve JUnit çıktıları `outputs/2026-09-10-meeting-delivery/spark-template-*` altında korundu. Bu L1 hazırlık kanıtıdır; `kt-vibecoding-python-web-v2` sabit yığını değişmedi.
   **AÇIK**
   M6 Bir model sembolik bağlantısı testi Windows hesabı sembolik bağlantı oluşturamadığı için atlandı; test kaldırılmadı veya zayıflatılmadı. Gerçek bağlantısı kesilmiş Spark üzerinde yeniden hazırlama/çalıştırma yapılmadı.
   **YAN-ETKİ**
   M7 004 Requirement 7, plan/görev ve 002 plan bağlantısı güncellendi; bir Nginx hash sabiti ve güncel gerçek hazırlığı doğrulayan regresyon eklendi. Bağımlılık/imaj hash'i, allowlist, uzaktaki dosya veya model değiştirilmedi.
