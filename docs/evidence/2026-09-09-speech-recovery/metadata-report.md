# Koşum raporu — 2026-09-09 · Ön işleme sürümünün tipli iş sonucunda izlenmesi

1. Sonuç: `kt-vibecoding-python-web-v2` profilinde izin verilen ön işleme bilgisi korunuyor ve eski sonuçlar okunabiliyor — birim 66 başarılı / PostgreSQL entegrasyonu 18 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kontrol | Ortam / komut | Sonuç |
   | --- | --- | --- |
   | Birim kırmızı | Mevcut Linux Python 3.13 backend; `scripts/stack.sh --mode spark exec -T backend pytest tests/unit/test_speaker_preprocessing.py -q` | 12 beklenen hata; [çıktı](metadata-red.txt), [JUnit](metadata-red.xml) |
   | Worker kırmızı | Aynı wrapper; ayrı `_test` PostgreSQL veritabanı, `RUN_POSTGRES_INTEGRATION=1`; `pytest tests/integration/test_speaker_pilot.py -k worker_persists_preprocessing -q` | 4 beklenen hata / 14 seçilmeyen; [çıktı](metadata-integration-red.txt), [JUnit](metadata-integration-red.xml) |
   | Son birim paketi | Aynı backend; `pytest tests/unit -q` | 66 başarılı; [çıktı](metadata-unit.txt), [JUnit](metadata-unit.xml) |
   | Son pilot entegrasyonu | Yeni ayrı `_test` veritabanı; gerçek HTTP uygulaması, worker ve PostgreSQL; `pytest tests/integration/test_speaker_pilot.py -q` | 18 başarılı; [çıktı](metadata-integration.txt), [JUnit](metadata-integration.xml) |
   | Statik kontrol | Kalite kapısının tam backend kaynak kopyası yaklaşımı; Ruff, Black, isort, mypy | 67 dosyanın biçimi ve 54 uygulama dosyasının tip kontrolü geçti; [çıktı](metadata-static.txt) |
   | Sözleşmeler | `scripts/export-openapi.sh`, `scripts/generate-types.sh`, ikisinin `--check` koşumu; frontend `npm run typecheck` | Üretim, drift ve tip kontrolü başarılı; [çıktı](metadata-contracts.txt) |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 `preprocessing_version` mevcut yedi günlük iş sonucu saklamasına tabidir; kalıcı profil/örnek provenansı değildir. Eski veya sürüm bildirmeyen sağlayıcı sonuçlarına `null` atanır; geçmiş sürüm uydurulmaz.
   M2 İlk statik kontrolde import satırı Ruff düzenine uymadı; çok satırlı biçimle düzeltildi ve tüm statik kontroller tekrar geçti. [İlk çıktı](metadata-static-initial.txt).

   **GÖZLEM**
   M3 İki izinli değer, eksik/eski quality, altı bilinmeyen/bozuk sürüm, ilgisiz quality verisinin dışarı taşınmaması ve eski kayıt okuma test edildi. PostgreSQL testleri fixture vektörleri kullanır; model doğruluğu kanıtı değildir.
   M4 Benzersiz toplam 84 otomatik vaka; bu değişiklik 12 birim ve 4 integration olmak üzere 16 yeni vaka ekledi. Kırmızı/tekrar koşumları toplamı artırmaz.

   **AÇIK**
   M5 Gerçek Spark sağlayıcısının yeni ön işleme alanını üretmesi, gerçek uygulama doğrulaması ve son tam kalite kapısı ana görevde sürüyor; bu dar koşum L1 otomatik kanıttır.

   **YAN-ETKİ**
   M6 Domain tip tanımı, HTTP adaptörü, uygulama portu, sonuç şeması, worker, iki test dosyası ve üretilen OpenAPI/frontend tipleri değişti. Kullanıcı arayüzü, SQL şeması, ayarlar, model revision'ı ve readiness sözleşmesi değişmedi.
   M7 İki benzersiz test veritabanı yalnız test migrasyonlarıyla oluşturulup kaldırıldı; [kırmızı](metadata-integration-red-db.txt), [yeşil](metadata-integration-db.txt). Uygulama veritabanı, Spark servisleri ve mevcut profiller değiştirilmedi; yeniden başlatma yapılmadı.
