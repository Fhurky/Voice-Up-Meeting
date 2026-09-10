# Koşum raporu — 2026-09-09 · Kabul edilmiş kalibrasyon kararının pilot eşiklerine uygulanması

1. Sonuç: Decision 7'nin 0.55 kabul eşiği domain, typed ayar ve yerel ortam yüzeylerinde tutarlı; ret sınırları korundu — birim 54 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kontrol | Ortam / komut | Sonuç |
   | --- | --- | --- |
   | Değişiklik öncesi regresyon | Mevcut Linux Python 3.13 backend; `scripts/stack.sh --mode spark exec -T backend pytest tests/unit/test_speaker_identity.py -q` | 6 beklenen hata / 13 başarılı; [çıktı](calibrated-policy-red.txt), [JUnit](calibrated-policy-red.xml) |
   | Değişiklik sonrası tüm backend birim paketi | Aynı stack wrapper; `pytest tests/unit -q` | 54 başarılı / 0 atlanan; 2,51 saniye; [çıktı](calibrated-policy-unit.txt), [JUnit](calibrated-policy-unit.xml) |
   | Konfigürasyon eşleme | Windows Python 3.13; `scripts/check-config-sync.py` | Başarılı; [çıktı](calibrated-policy-config.txt) |
   | Statik kontrol | Kalite kapısıyla aynı tam backend kaynak kopyasında Ruff, Black, isort ve mypy | 66 dosya biçimi, 54 uygulama kaynak dosyası tip kontrolü geçti; [çıktı](calibrated-policy-static.txt) |
   | Çözülmüş Compose | `scripts/stack.sh --mode spark config --format json`; yalnız üç eşik alanı çıkarıldı | Backend ve worker: 0.55 / 0.45 / 0.10; [kanıt](calibrated-policy-compose.json) |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Git Bash, `--junitxml=/tmp/…` değerini Windows yoluna çevirdi; iki rapor kanıt klasörüne kopyalandı ve yalnız oluşan geçici artifakt temizlendi. Yeniden koşumda bu argümanın otomatik yol dönüşümü engellenmelidir.
   M2 Dar kaynak kopyası Ruff'ın import sınıflandırmasını bozduğu için statik kontrol tam kaynak kopyasında yapıldı. Yerel konsol Black'in Unicode simgelerini yazamadı; UTF-8 dosyasındaki tam başarılı araç çıktısı ayrıca doğrulandı.

   **GÖZLEM**
   M3 0.5499 reddi, 0.55 kabulü, kalibrasyon skorları 0.58304 ve 0.51501, yakın adaylarda 0.10 fark gereksinimi ve 0.45 bilinmeyen sınırı test edildi. Açıkça verilen eski 0.75 politikası korunur.

   **AÇIK**
   M4 Tam uygulama kalite kapısı, değişen ortamla servislerin yeniden oluşturulması ve yeni gerçek kalibrasyon/kör test ölçümü ana görevdedir; bu dar koşum bunları tamamlanmış saymaz.

   **YAN-ETKİ**
   M5 `app/backend/app/core/config.py`, `app/backend/app/domain/speaker_identity.py`, backend `.env.example`, yerel Compose ve `test_speaker_identity.py` değişti. Model, kalite kuralları, şema, bağımlılık ve araştırma referansı değişmedi; bu koşum servisleri yeniden başlatmadı.
