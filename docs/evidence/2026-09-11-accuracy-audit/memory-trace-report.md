# Koşum raporu — 2026-09-11 · Model başına özel hafıza karar izi

1. Sonuç: Decision 21 karar izi mevcut tanıma çıktısını koruyarak geçti — birim 44 başarılı / PostgreSQL 72 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; yerel Windows/Python 3.13 birim/statik denetimleri ve Linux arka uç üzerinden gerçek PostgreSQL/HTTP/dosya sınırları kullanıldı.

   | Koşum | Kapsam | Sonuç |
   |---|---|---|
   | İlk birim | Yeni yardımcı bulunmadan `test_meeting_memory_trace.py` | 1 toplama hatası |
   | İlk PostgreSQL | Üretim bağlaması bulunmadan yeni iz sözleşmeleri | 5 başarısız / 3 başarılı |
   | Son birim | `tests/unit/test_meeting_memory_trace.py`, `test_speaker_identity.py` | 44 başarılı / 0 atlanan |
   | Son PostgreSQL | `test_meeting_memory_trace.py`, `test_meeting_memory.py`, `test_meeting_context_memory.py`, `test_meeting_cleanup.py` | 9 yeni + 63 mevcut = 72 başarılı / 0 atlanan |
   | Statikler | Değişen dört dosyada Ruff/Black/isort; Mypy bütün arka uç | Başarılı; 79 kaynak |

   Testler `pytest <yukarıdaki dosyalar> -q` ile çalıştırıldı; PostgreSQL koşumunda mevcut `scripts/stack.sh`/`scripts/db.sh` kullanıldı, ayrı `_test` veritabanına migrasyon uygulandı ve `RUN_POSTGRES_INTEGRATION=1` verildi. Ham XML/metin kanıtları `outputs/2026-09-11-resultant-correctness/memory-trace-*` altında; karma ve sözleşme özeti [makine kaydındadır](memory-trace-results.json).
3. Maddeler:
   **KUSUR**
   M1 `below_match_threshold` gibi model nedenleri birleşme sırasında genel `insufficient_margin` altında kayboluyordu; özel `memory_match_trace` iki modelin gerçek skor/karar/sebebini korur (DÜZELTİLDİ, `meeting_memory_trace.py`, `meeting_memory.py`).
   **TUZAK**
   M2 İz tarihi karşılaştırmanın kanıtıdır; sonraki galeri veya değişmiş temiz aralıklarla geçmiş iz oluşturulmaz. Tamamlanmış iz değişmez, geçmişte izi olmayan tamamlanmış kayıt boş kalır.
   M3 Kalite reddinde karşılaştırma yapılmadığından iz yoktur; boş skor listesi yalnız gerçekten sorgulanmış boş galeriyi, `community256=null` yalnız sorgulanmamış eski yolu belirtir.
   **GÖZLEM**
   M4 Sentetik `.51/.31` ECAPA ve `.20/.10` Community örneği nedenleri ayrı kaydeder; final karar eskisi gibi `ambiguous/insufficient_margin` kalır. Gerçek PostgreSQL sıralaması ve farklı kazananlar boolean değeri doğrulandı.
   M5 İz, mevcut kanıt fingerprint'i, kullanılan politika ve model/işleme sürümlerine bağlıdır; en fazla iki skor içerir. Profil kimliği, ad, vektör, ses veya metin almaz ve genel HTTP sonucuna girmez.
   **AÇIK**
   M6 Elli kişi A kaydı bu izden önce tamamlandı; mevcut 8 genel belirsizliğin hangi model eşiğinden çıktığı tarihsel olarak geri getirilemez. Yeni canlı iz ve tam kalite kapısı bu dar koşumun kanıtı değildir.
   M7 Elli kişi A verisinde iki kişiyi içeren kalıcı örnek ayrıca saptandı; karar izi bu doğruluk kusurunu düzeltmez ve hiçbir kalite/eşleşme eşiğini gevşetmez.
   **YAN-ETKİ**
   M8 Bir saf alan yardımcısı, hafıza transaction'ına özel iz bağlaması ve iki test dosyası eklendi; şema/API/bağımlılık değişmedi. Asıl `fuse_populations` gövdesi aynen korundu.
   M9 Geçici veritabanları koşum sonunda kaldırıldı; ana uygulama veya işçi yeniden başlatılmadı. Gerçek sonuç temizliği izi kaldırırken bağımsız profil örneğini korudu.
