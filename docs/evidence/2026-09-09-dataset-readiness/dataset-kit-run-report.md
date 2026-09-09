# Koşum raporu — 2026-09-09 · T09 veri hazırlığı doğrulayıcısı

1. Sonuç: Veri hazırlama aracı ve regresyonları başarılı — birim 256 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kapsam | Ortam ve komut | Sonuç |
   | --- | --- | --- |
   | İlk eksik davranış | Yerel araştırma Python ortamı; `pytest tests/test_speaker_dataset.py -q -o addopts= --maxfail=1` | Doğrulayıcı henüz bulunmadığından 1 hata; uygulama sonrası ilk 17 test başarılı. |
   | Çıktı koruması | Aynı dosyada `-k 'invalid_recordings_shape or cannot_overwrite_source_inputs'` | Önce 2 başarısız, 2 başarılı, 20 seçim dışı; düzeltme sonrası dosyanın 24 testi başarılı. |
   | Kaynak kimliği sızıntısı | Aynı dosyada `-k original_source_cannot_cross_roles` | Önce 1 başarısız, 24 seçim dışı; düzeltme sonrası bütün araştırma paketinde 244 başarılı. Önceki çıktı `reference-tests.txt`, XML `reference.xml`. |
   | Bağımsız inceleme regresyonları | Statik ses uyumu, kayıt sırasından bağımsız tekrar denetimi ve kaynak sınırları | Önce 12 başarısız, 25 seçim dışı; düzeltme sonrası `pytest tests/test_speaker_dataset.py -q -o addopts=` ile 37 başarılı. |
   | Son araştırma regresyonu | `pytest tests -q -o addopts= --junitxml=.../reference-final.xml` | 256 başarılı, 0 atlanan; [ham çıktı](reference-final-tests.txt), [JUnit](reference-final.xml). |
   | Biçim ve lint | Backend Python 3.13 Black ve mevcut araştırma Ruff; değişen iki Python dosyası | Başarılı. `kt-vibecoding-python-web-v2` uygulama katmanları değişmedi; ana çalışmanın tam uygulama kapısı ayrı kanıttır. |
   | Gerçek CLI, boş şablon | Backend Python 3.13; `validate-speaker-dataset.py --manifest examples/speaker-dataset.example.json --audio-root data/speaker-pilot --output outputs/speaker-dataset-readiness.json` | Exit 1, `not_ready`, iki aşama false, beklenen 32 kayıt / doğrulanan 0 dosya. Ses oluşturulmadı. |
   | Bağımsız son inceleme | Başka ajanın yalnız kaynak okuması | Bildirilen üç sorun giderilmiş bulundu; bu inceleme test veya model çalıştırması değildir. |

3. Maddeler:

   **KUSUR**

   M1 Eksik JSON alanı hata raporunu engelleyebiliyor, hardlink çıktı yolu kaynak sesi ezebiliyordu; tip denetimi ve dosya kimliği kontrolüyle düzeltildi.

   M2 Aynı orijinal kayıt farklı kişi etiketiyle roller arasında taşınabiliyordu; kaynak kimliği denetimi kişi adından bağımsızlaştırıldı.

   M3 Statik denetim bazı çıkarım servisi tarafından reddedilecek sesleri kabul ediyordu; örnekleme, kanal, çözülmüş örnek, PCM aralığı ve clipping sınırları eşlendi.

   M4 Önce gelen dönüş aşaması kaydı ilk aşamadaki tekrarları gizleyebiliyordu; bütün tekrar indekslerinde ilk aşama temsilcisi korunuyor ve yol çakışması diğer hash kontrollerini atlamıyor.

   **TUZAK**

   M5 Manifest en fazla 1 MiB ve 500 kayıt; rapor en fazla 1.000 ayrıntı içerir. `errors_total`, `errors_truncated` ve bağımsız `invalid_phases` alanları, kesilen ayrıntıların hazır durumunu değiştirmesini önler.

   **GÖZLEM**

   M6 32 girdilik şablon 5 kayıtlı kişi, 15 bilinen sorgu, 2 kişiden 10 bilinmeyen sorgu ve U01 için yeni kayıt/geri dönüş içerir. İnsan denetimi yapılmadan `natural_single_speaker` true değildir.

   **AÇIK**

   M7 Gerçek kullanıcı sesleri yoktur. Süre, metadata ve birebir PCM hash denetimi konuşma miktarını, konuşmacı saflığını, bağımsız oturumları veya kimlik doğruluğunu kanıtlamaz; T09 kalite deneyi eksiktir.

   **YAN-ETKİ**

   M8 Bir doğrulayıcı, JSON şablonu, 37 test ve bu kanıt dosyaları eklendi. Test sesleri yalnız geçici test klasörlerinde üretildi; doğrulayıcı yalnız istenen JSON raporunu UTF-8/LF yazar. API, model, GPU, sunucu profilleri ve kullanıcı sesleri değiştirilmedi.
