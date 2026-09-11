# Koşum raporu — 2026-09-11 · Kabul edilmiş 310 saniyelik pencerenin veritabanı kabul ve ret sınırı doğrulandı.

1. Sonuç: Tarihsel test düzeltmesinin dar paketi başarılı — birim 9 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Linux Python 3.13, güncel migrasyonlu benzersiz PostgreSQL `_test` veritabanı; `pytest tests/integration/test_meeting_repository.py::test_meeting_child_bounds_and_embedding_provenance tests/integration/test_meeting_repository.py::test_meeting_chunk_accepts_current_maximum_context -q --tb=short` | Sekiz mevcut ret durumu ve yeni 310 saniye kabulü: 9 başarılı; 2,72 saniye |
   | Aynı koşumun temizliği | Geçici veritabanı kaldırıldı |

3. Maddeler:

   **KUSUR**

   M1 [İkinci tam kapıdaki](second-gate-report.md) eski 71 saniye ret beklentisi yeni geçersiz 311 sınırına taşındı; tam 310 kabulü ayrıca doğrulandı. Üretim modeli/migrasyonu değiştirilmedi.

   **TUZAK**

   M2 Bu dar yeşil sonuç önceki tam kapıdaki başarısızlığı silmez; donmuş son kaynaklarla tam kapı yine çalıştırılmalıdır.

   **GÖZLEM** — yok

   **AÇIK**

   M3 Son tam kapı, uygulama yeniden başlatması ve kaynak sınırı kararlarının ardından yürütülecektir; bu dar test güvenlik, tarayıcı veya model doğruluğu kanıtı değildir.

   **YAN-ETKİ**

   M4 Geçici veritabanına güncel migrasyonlar uygulandı ve veritabanı sonunda kaldırıldı; ana veritabanı korunarak yalnız repository test fixture'ı/sınır testi güncellendi.
