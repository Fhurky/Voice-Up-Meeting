# Koşum raporu — 2026-09-09 · Spark tünelinin iki PowerShell motorunda tarih ve süreç sahipliği uyumu

1. Sonuç: JSON tarih dönüşümü kusuru düzeltildi; iki motorda aynı hazır tünel salt okunur doğrulandı — birim 76 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kontrol | Ortam / komut | Gözlenen sonuç |
   | --- | --- | --- |
   | Önce başarısız regresyon | Windows; `app/backend/.venv/Scripts/python.exe -m pytest tests/test_spark_tunnel.py -k json_state_preserves -q` | PowerShell 5.1: 1 başarılı; PowerShell 7.6.5: 1 başarısız, `spark_tunnel_state_mismatch` |
   | Düzeltilmiş tünel paketi | `app/backend/.venv/Scripts/python.exe -m pytest tests/test_spark_tunnel.py -q -o addopts= --junitxml=outputs/spark-access/powershell-regression-tests.xml` | [76 başarılı](focused-tests.xml); motor başına 38; 98,63 saniye |
   | Gerçek kayıt / hazır durum | Windows PowerShell 5.1.26100.9444 ve PowerShell 7.6.5; `Read-SparkTunnelState` + `Get-SparkTunnelStatus` | [İkisi de hazır](live-status.json); aynı PID 19460, aynı zaman damgası, `System.String` |
   | Statik kontrol | `python -m ruff check tests/test_spark_tunnel.py`, `python -m ruff format --check tests/test_spark_tunnel.py` | Başarılı |

3. Maddeler:

   **KUSUR**
   M1 PowerShell 7.6.5 JSON zaman damgasını `DateTime` yaptığı için doğru sahipli tünel reddediliyordu; destekleyen motorda `DateKind=String` ile düzeltildi ([kod](../../../scripts/spark-tunnel.ps1), [regresyon](../../../tests/test_spark_tunnel.py)).

   **TUZAK**
   M2 PowerShell 5.1'de `DateKind` parametresi yoktur; komutun gerçek parametre yüzeyi kontrol edilir. Yalnız bu iki kurulu motorun çalıştırıldığı iddia edilir.

   **GÖZLEM**
   M3 Geçersiz biçim, olmayan tarih ve başka sürece ait zaman damgası reddi; komut, PID ve yürütülebilir dosya sahiplik kontrolleri her iki motorda geçti. Gerçek tünel yeniden başlatılmadı.

   **AÇIK**
   M4 Bu dar koşum web tarayıcısı, bütün uygulama kalite kapısı veya model doğruluğu kanıtı değildir; kapsam `kt-vibecoding-python-web-v2` profilinde kabul edilmiş 004 tünel sınırıdır.

   **YAN-ETKİ**
   M5 JSON okuma ve test paketi değişti; testler yalnız geçici dizinlerde kendi dosyalarını kullandı. Uygulama verisi, model, bağımlılık ve çalışan servisler değiştirilmedi.
