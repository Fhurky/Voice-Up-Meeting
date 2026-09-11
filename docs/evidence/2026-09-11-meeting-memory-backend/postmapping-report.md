# Koşum raporu — 2026-09-11 · Doğal hafıza adaylarının akustik eşlemeden sonra özgün kaynakta üretilmesi doğrulandı.

1. Sonuç: Son birleşik bileşen paketi başarılı — birim 88 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Dosya ve gözlenen sonuç |
   |---|---|
   | Windows Python 3.13, ilk sözleşme/domain kırmızı koşumları | Tarif alanı testi `AttributeError`; yeni domain modülü yokken toplama hatası; uygulamadan sonra 7 test başarılı |
   | Linux Python 3.13, HTTP uygulaması ve migrasyonlu benzersiz `_test` PostgreSQL, `pytest tests/integration/test_meeting_candidates.py::test_worker_builds_candidates_only_after_acoustic_mapping -q --tb=short` | Uygulamadan önce üç durum `candidate_version` eksikliğiyle başarısız; 5,47 saniye |
   | Aynı ortam, aday/domain/sözleşme dar paketi | Uygulamadan sonra 15 test başarılı; 11,27 saniye |
   | Aynı ortam, `pytest tests/integration/test_meeting_context_memory.py tests/integration/test_meeting_candidates.py tests/integration/test_meeting_memory.py tests/unit/test_meeting_memory_contract.py tests/unit/test_meeting_memory_adapter.py tests/unit/test_meeting_candidate_domain.py -q --tb=short` | Sırasıyla 21 + 11 + 35 + 10 + 7 + 4 = 88 başarılı; 52,14 saniye |
   | Windows Python 3.13, `mypy app`; değişen Python dosyalarında Ruff/Black | 77 kaynak dosyasında tip denetimi başarılı; lint/biçim başarılı |

3. Maddeler:

   **KUSUR**

   M1 Aynı akustik kişiye ait kısa iki native etiket eşleme öncesinde ayrı aday üretiminde kayboluyordu; yeni gerçek worker testi önce kırmızı oldu. `meeting_chunks.py` artık bütün eşlemelerden sonra domain yardımcısıyla aday üretir; 8/44,1 kHz testleri geçti.

   M2 Yeni VAD nesnesi boş olduğunda açık aday sürümü/listesi yazılmıyordu; kırmızı worker testiyle görüldü. Yeni yol açık boş aday alanı ve kaynak hash'i bırakır; eski kalite yoluna dönmeyen başarılı toplantı doğrulandı.

   **TUZAK**

   M3 Parça VAD aralıkları yerel saniye, hafıza doğrulama aralıkları gönderilen özgün WAV'ın tam sayı örnek indeksidir. İki özel uç noktanın koordinatları birbirinin yerine kullanılamaz.

   M4 Kaynak ana bölgesine kırpılınca üç saniyenin altına inen aday korunmaz; yeni bir parçalar arası bağlam biriktirme mekanizması eklenmedi. Bu korumalı kayıp doğruluk garantisi değildir.

   **GÖZLEM**

   M5 Farklı akustik kişiler birleştirilmez; ham native örtüşme/rakip konuşma engel olarak korunur. VAD dışı boşluklar ve bileşenin son 0,25 saniyesi ses kanıtına eklenmez; domain testleri bunu doğrular.

   M6 Sabit Silero model/sürüm/hash kimliği, sıralama, örtüşme, kaynak sınırı ve tarif zorunluluğu yedi olumsuz sözleşme durumuyla sınandı. Tarihsel tarif/VAD yokluğu ve eski hafıza davranışı regresyon paketinde korundu.

   **AÇIK**

   M7 Bu koşum imzası/sözleşmesi kısıtlı model fixture'larıyla gerçek veritabanı, HTTP uygulaması ve dosya sınırını sınar. Gerçek A/B/D/C, karışık ses reddi, native Spark, Türkçe/50 kişi ve tam profil kapısı bu bileşen raporundan çıkarılamaz.

   **YAN-ETKİ**

   M8 `meeting_ports.py`, `meeting_chunks.py`, saf domain yardımcısı ve testler eklendi/güncellendi; Decision 15, T14 bileşen kanıtı ve özel sözleşme kaydedildi. Her gerçek PostgreSQL koşumunun benzersiz geçici veritabanı sonunda kaldırıldı; ana veritabanına migrasyon uygulanmadı.
