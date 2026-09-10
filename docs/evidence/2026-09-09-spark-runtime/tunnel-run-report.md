# Koşum raporu — 2026-09-09 · Windows–Spark SSH tüneli

1. Sonuç: `kt-vibecoding-python-web-v2` profili altında son tünel paketi geçti — birim 31 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Ana ajanın ayrı gerçek HTTP kanıtında üç iş başarılı, bir kesinti işi beklenen terminal hatayla tamamlandı.
2. Koşulan: Windows PowerShell 5.1, yerel Python 3.12 test ortamı; gerçek geçici yapılandırma/durum dosyaları ve imzası sınırlanmış süreç/HTTP taklitleri kullanıldı.

   | Komut veya kanıt | Gözlenen sonuç |
   | --- | --- |
   | İlk `pytest tests/test_spark_tunnel.py -x -q -o addopts=` | Betik yokken 1 başarısız test; uygulama eklendikten sonra Türkçe yerel ayara bağlı anahtar kontrolü hatası gözlendi. |
   | İlk tamamlanan `pytest tests/test_spark_tunnel.py -q -o addopts=` | 29 başarılı, 0 atlanan; 42,19 saniye. |
   | `pytest tests/test_spark_tunnel.py -q -o addopts= -k initial_inspection` | Erken süreç denetimi için 2 başarısız test; düzeltmeden sonra 2 başarılı, 29 seçilmeyen test. |
   | Son `.venv/Scripts/python.exe -m pytest tests/test_spark_tunnel.py -q -o addopts=` | 31 başarılı, 0 atlanan; 44,69 saniye. |
   | `app/backend/.venv/Scripts/python.exe -m ruff check tests/test_spark_tunnel.py` ve `ruff format --check tests/test_spark_tunnel.py` | İkisi de başarılı. |
   | PowerShell `Parser.ParseFile` ile `scripts/spark-tunnel.ps1` | Sözdizimi hatası yok. |
   | Ana ajanın [application-live.json](application-live.json) kaydı | İlk iş, tünel dönüşü ve Spark yeniden başlatması sonrasında üç başarılı iş; tünel kapalıyken iki denemeden sonra `failed / inference_unavailable`. |

3. Maddeler:
   **KUSUR**
   M1 İlk süreç denetimi başarısızlığında yeni SSH sürecinin açık kalması düzeltildi; tutulan süreç tanıtıcısıyla temizleme iki kırmızı/yeşil regresyon testiyle korundu (`test_initial_inspection_failure_closes_only_the_new_process_handle`).
   M2 Windows PowerShell 5.1'in Türkçe yerel ayarında Base64 harf aralığı eşleşmesi düzeltildi; büyük/küçük harfe duyarlı kontrol gerçek dosya kullanan olumlu testlerle korundu.
   **TUZAK**
   M3 Açık `ConfigPath` mutlak olmalıdır; varsayılan dosya yolu otomatik çözülür. Kayıtlı süreç yalnız PID, başlangıç zamanı, çalıştırılabilir dosya, komut satırı ve yapılandırma özeti eşleşirse yeniden kullanılır veya durdurulur.
   M4 Hazır olma beklemesi 30 saniyeyle sınırlıdır; önceden var olan sahipli süreç hazır değilse başlangıç denemesi onu öldürmez. İş başına iki deneme ve deneme başına 300 saniye sınırı mevcut worker sözleşmesidir.
   **GÖZLEM**
   M5 Ana ajanın gerçek HTTP kaydı aynı model revision'ı ve `cuda:0` ile üç başarıyı, kesintide yerel inference'ın kapalı kaldığını ve bütün akışlarda profillerin değişmediğini gösterir; birim testler gerçek SSH veya model çalıştırmadı.
   M6 İncelenen betik SHA256: `bdd22139ee9ee22a2019cc52fc6f5e70b79481879ae193830d3b5b7c8e1db775`. Kaynaklar: `scripts/spark-tunnel.ps1` ve `tests/test_spark_tunnel.py`.
   **AÇIK**
   M7 Tam uygulama kalite kapısı ana ajanın ayrı raporundadır; bu 31 test onun yerine geçmez. Yapay olarak tekrarlanan açık ses örneği Türkçe kişi tanıma doğruluğu veya kullanıcı kabulü kanıtı değildir.
   **YAN-ETKİ**
   M8 İki tünel kaynak/test dosyası ve bu rapor eklendi. Birim testler yalnız geçici test dizinlerinde dosya oluşturdu; gerçek anahtar, profil, ses veya uygulama verisini değiştirmedi. Gerçek tünel/servis işlemleri ana ajanın ayrı canlı koşumuna aittir.
