# Koşum raporu — 2026-09-11 · Doğrulanmış konuşma aralıklarını kaynak örneklerine içten dönüştürme.

1. Sonuç: Kaynak örnekleme hızına dönüşümde kanıt aralığının dışına taşma düzeltildi — birim 9 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Sayılar gerçek PostgreSQL entegrasyon testleridir; model doğruluğu ölçümü değildir.
2. Koşulan: `kt-vibecoding-python-web-v2`; Python 3.13 backend konteyneri ve PostgreSQL 17. `scripts/stack.sh` ile rastgele adlandırılmış ayrı `_test` veritabanları, `scripts/db.sh apply` ile güncel Alembic başlığı ve `RUN_POSTGRES_INTEGRATION=1` kullanıldı.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `pytest -q tests/integration/test_meeting_worker.py -k validated_evidence_never_expands` | RED: üç gerçek 30 saniyelik WAV vakası da beklenen kaynak sınırları dışa genişlediği için başarısız; altı mevcut test seçilmedi. |
   | `pytest -q tests/integration/test_meeting_worker.py --junitxml=/tmp/meeting-source-bounds.xml` | GREEN: 9/9 başarılı, 10,19 saniye; migration başlığı `f43fd9e32042`. |
   | Ruff, Black `--check`, isort `--check-only` | `meeting_chunks.py` ve `test_meeting_worker.py` üzerinde başarılı; dosyalara otomatik düzeltme uygulanmadı. |

3. Maddeler:

   **KUSUR**
   M1 En yakın tam sayıya yuvarlama, doğrulanmış konuşma aralığına ait olmayan kaynak örneğini hafıza kanıtına katabiliyordu. Yalnız `validated_ranges` dönüşümü başlangıçta `ceil`, bitişte `floor` ve pozitif genişlik filtresi kullanır.
   M2 Regresyonlar 8.000 / 24.000 / 44.100 Hz gerçek WAV yükleyip kalıcı `clean_ranges` değerlerini sırasıyla `[801,200001]`, `[2405,600001]`, `[4419,1102502]` olarak doğrular; 8 kHz vakası hiçbir tam örnek içermeyen ek aralığın dışlandığını da korur.
   **TUZAK**
   M3 İlk RED koşumunun XML yolu Git Bash argüman dönüşümü yüzünden kopyalanamadı; gerçek üç assertion hatası TXT çıktısında korunur. Son GREEN koşumunda yol dönüşümü engellendi ve XML kopyalandı.
   M4 XML tekrar denemesi ana ajanın kontrollü migrasyon penceresinde `service "backend" is not running` aldı; test başlamadı ve o denemeye ait veritabanı kaldırıldı. Backend yeniden açıldıktan sonra GREEN yeni ayrı veritabanında çalıştı.
   M5 Doğrudan bind mount üzerinde Ruff dosyaları çalıştırılabilir gördü. Kalite kapısının kullandığı geçici kaynak kopyası ve `0644` izinleriyle son kontroller geçti; yalnız kısmi paket ağacıyla yapılan ara denemelerin import sınıflaması tam kaynak kopyasıyla giderildi.
   **GÖZLEM**
   M6 HTTP yükleme, gerçek dosya kabulü, worker lease’i ve kalıcı PostgreSQL konuşmacı satırı test kapsamındadır. Sağlayıcı çıktısı mevcut sıkı `MeetingChunkResult` sözleşmesiyle doğrulanan kontrollü fixture’dır; gerçek model çalıştırıldığı iddia edilmez.
   M7 Diarization konuşma aralıkları, pencere sınırları, eşik değerleri, profil kararı ve mevcut worker davranışları değiştirilmedi; kalan altı worker regresyonu da geçti.
   **AÇIK**
   M8 Tam kalite kapısı ve güvenlik taraması bu dar koşumda çalıştırılmadı. Ana ajanın eş zamanlı tracking değişiklikleri birleştirildikten sonra güncel bütün kaynak için son kapı gerekir.
   **YAN-ETKİ**
   M9 İki kaynak dosyası değiştirildi; üç parametrik test yeni WAV fixture’larını testin geçici alanına yazar. Denemelerin yalnız kendi oluşturduğu `_test` veritabanları başarı/hata sonrasında kaldırıldı; uygulama veritabanına bu koşumdan yazılmadı.
   M10 `source-bounds-red.txt`, `source-bounds-green.txt`, `source-bounds-green.xml` ve `source-bounds-static.txt` Git dışı `outputs/2026-09-10-meeting-delivery/` dizininde korundu; kimlik bilgisi, ham toplantı metni veya embedding rapora eklenmedi.
