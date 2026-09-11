# Koşum raporu — 2026-09-11 · Başlatıcı test yardımcısı kurulu PowerShell motoruyla doğrulandı.

1. Sonuç: Dar yerel paket tamamen başarılı — birim 109 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows PowerShell, Python 3.12, `pytest tests/test_spark_startup.py -k default_runs_installed_native_engine -q --tb=short` | Düzeltmeden önce 1 başarısız; kurulu `powershell` bulunmasına rağmen eksik `pwsh` için `subprocess` TypeError |
   | Aynı yerel ortam, mevcut Helm dizini PATH'te; `pytest tests/test_spark_startup.py tests/test_spark_tunnel.py tests/test_local_configuration.py -q --tb=short --junitxml=...` | 109 başarılı, 0 başarısız, 0 atlanan |
   | Değişen test dosyasında Ruff lint/format | Başarılı |

3. Maddeler:

   **KUSUR**

   M1 `run_startup` varsayılanı sabit `pwsh` olduğu için on eski test gerçek program başlamadan hata veriyordu; yardımcının varsayılanı mevcut `SHELLS` listesinden seçildi ve bir gerçek süreç regresyonu eklendi.

   **TUZAK**

   M2 `powershell`/`pwsh` için açık parametreli testler korunur; yeni test de mevcut bütün motorlara parametrized edilir. Kurulu motor yoksa açıklayıcı hata verilir; yeni atlama veya test kapsamı daraltması yoktur.

   **GÖZLEM**

   M3 [Ham çıktı](../../../outputs/2026-09-11-meeting-native-tests-094937/native-tests-latest.txt) ve [XML](../../../outputs/2026-09-11-meeting-native-tests-094937/native-tests.xml) korunur; önceki [başarısız teşhis](root-tests-investigation-report.md) silinmedi.

   **AÇIK**

   M4 Bu makinede PowerShell 7 `pwsh` yoktur; bu koşumun gerçek motoru Windows PowerShell'dir. Tüm kök paket ve yardımcı düzeltmeler sonrası son uygulama kapısı ayrıca çalıştırılır.

   **YAN-ETKİ**

   M5 Yalnız test yardımcısı, regresyon ve Accepted 004 plan/T12 kaydı değişti; üretim başlatıcısı, kullanıcı PowerShell kurulumu, GPU, Spark ve çalışan uygulama değiştirilmedi.
