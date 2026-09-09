# Koşum raporu — 2026-09-09 · yerel başlangıç ve runtime rolü incelemesi

1. Sonuç: Yerel hazırlık düzeltmeleri ve araştırma regresyonları başarılı — birim 219 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kapsam | Ortam | Sonuç |
   | --- | --- | --- |
   | İlk araştırma regresyonu `pytest tests -q` | Mevcut Python araştırma venv'i | 215 başarılı; sessiz çıktının toplamı ayrı collection komutuyla 215 olarak doğrulandı. |
   | Yeni hazırlık testleri | Geçici dosyalar, sahte subprocess ve gerçek PowerShell yorumlayıcısında Docker işlevi ikamesi | Önce 3 başarısız eksik davranış, düzeltme sonrası 4 başarılı; gerçek Docker başlangıcı veya rol değişikliği yok. |
   | Son araştırma regresyonu `pytest tests -o addopts= -q --junitxml=...` | Aynı araştırma venv'i | 219 başarılı, 0 atlanan; ham çıktı `reference-tests-after-setup-review.txt`, JUnit `reference-after-setup-review.xml`. |
   | Compose config ve `bash -n scripts/db.sh` | Yerel CLI, yalnız okuma | İkisi de exit 0. |
   | Runtime rolü sorgusu | Yalnız VoiceUp PostgreSQL, yalnız SELECT | Superuser, DB/rol oluşturma, replication, RLS bypass, schema CREATE, rol üyeliği ve schema/relation sahipliği false. |
   | Black | Dört değişen Python hazırlık/test dosyası | Biçimlendirildi; uygulama kalite kapısı değişmediği için tekrar çalıştırılmadı. |

3. Maddeler:

   **KUSUR**

   M1 `.env` anahtarında BOM, boşluk veya `export` varsa hazırlayıcı mevcut sırrı kaçırıp ikinci anahtar ekleyebiliyordu; ortak tek satır okuyucusu ve koruma testiyle düzeltildi.

   M2 Rol hazırlama, geçerli tırnaklı dotenv parolasını reddediyordu; aynı okuyucu kullanıldı. SQL/parola stdout veya komut argümanına çıkarılmıyor.

   M3 İki yerel girişte proje adı ortam tarafından değiştirilebiliyordu; açık `-p voiceup` eklendi. Rol işlemleri transaction içine alındı ve mevcut sahiplik/rol üyeliği varsa değişiklikten önce reddediliyor.

   M4 `start-local.ps1` yerel image eksikken registry erişimi deneyebilir ve farklı port ayarında yanlış adres gösterebilirdi; `--pull never` ve Compose'tan çözümlenen port eklendi.

   **TUZAK**

   M5 Hazırlayıcı mevcut boş veya örnek sırları sessizce değiştirmez; anahtar adını belirten hata ile çıkar. Geçerli mevcut değerler korunur.

   **GÖZLEM**

   M6 `db.sh` uygulama bağlantısından ayrı migrasyon sürecini kullanıyor; `_test` override yalnız uygun sonekle kabul ediliyor. Bu incelemede migrasyon yürütülmedi.

   **AÇIK** — yok

   **YAN-ETKİ**

   M7 Dört hazırlık/test dosyası ve ortak dotenv okuyucusu değişti; uygulama `.env` dosyası, hesap parolaları, veritabanı verisi ve çalışan servisler değiştirilmedi.
