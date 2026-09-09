# Koşum raporu — 2026-09-09 · çıkarım yanıtı ve işleyici sözleşmesi regresyonları

1. Sonuç: İki sözleşme kusuru düzeltildi ve tam kalite kapısı geçti — birim 65 başarılı / PostgreSQL 15 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kapsam | Ortam ve komut | Gözlenen sonuç |
   | --- | --- | --- |
   | İlk dar kırmızı test | Yerel Python 3.13; `pytest tests/unit/test_speaker_boundaries.py -k 'producer_minimum_tolerance or rejects_cpu_success_response' -q` | 3 başarısız, 10 kapsam dışı bırakılan; iki süre ve bir cihaz kusuru doğrulandı. |
   | Tam kırmızı kapı | Kilitli Linux Python 3.13, tek kullanımlık PostgreSQL 17/pgvector; `scripts/quality-gate.sh all` | 54 başarılı, 5 başarısız, 0 atlanan; beklenen regresyonlarda durdu, test veritabanı kaldırıldı. [Ham çıktı](contract-regression-red.txt). |
   | Dar yeşil test | Yerel Python 3.13; `pytest tests/unit/test_speaker_boundaries.py -q` | 13 başarılı, 0 atlanan. |
   | Son tam kapı | Aynı kilitli ortam; `scripts/quality-gate.sh all` | Arka uç 59 (44 birim + 15 PostgreSQL), ön yüz 21 başarılı; 0 başarısız, 0 atlanan. [Ham çıktı](contract-regression-green.txt), [pytest XML](contract-regression-backend.xml), [Vitest JSON](contract-regression-frontend.json). |
   | Diğer kapı adımları | `kt-vibecoding-python-web-v2` | Biçim/lint/tip, migrasyon ve şema drift, config, bağımlılık kabulü, OpenAPI/tip drift, ön yüz build, governance ve chart 46 kaynak × 2 fixture başarılı. |

3. Maddeler:

   **KUSUR**

   M1 Üretici kabul ettiği sınır süresini HTTP adaptörü ve işleyici reddediyordu; iki tüketiciye aynı `1e-6` saniye toleransı eklendi, enroll/identify için dört regresyon testiyle korundu.

   M2 HTTP adaptörü `device: cpu` içeren başarılı yanıtı kabul ediyordu; üreticiyle aynı `^cuda:[0-9]+$` doğrulaması ve `model_mismatch` regresyon testi eklendi.

   **TUZAK**

   M3 HTTP sözleşme testindeki `cuda:0` değeri seri hale getirilmiş üretici fixture'ıdır; GPU çalıştırma kanıtı değildir.

   **GÖZLEM**

   M4 Bu düzeltmeler için L1 gözlendi. Genel API şeması değişmedi; mevcut OpenAPI ve istemci tipi drift kontrolleri geçti.

   **AÇIK**

   M5 Bu koşum gerçek model/CUDA veya tarayıcı akışını çalıştırmadı; canlı GPU doğrulaması ana entegrasyon çalışmasında ayrı yürütülür.

   **YAN-ETKİ**

   M6 İki backend modülü, iki test dosyası ve iç sözleşme belgesi güncellendi; iki kapının oluşturduğu yalnız kendisine ait `_test` veritabanı kaldırıldı. Çalışan servis, uygulama verisi veya sır değişikliği yapılmadı.
