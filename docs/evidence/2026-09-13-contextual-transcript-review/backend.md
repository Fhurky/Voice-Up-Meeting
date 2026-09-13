# Koşum raporu — 2026-09-13 · Bağlama göre sözcük incelemesinin arka uç sınırları

1. Sonuç: Son birleşik koşumda 20 gerçek PostgreSQL testi ve 52 birim testi başarılı; son statik düzeltmenin ardından aynı 52 birim testi yeniden başarılı — birim 52 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows çalışma alanı, mevcut `scripts/stack.sh` üzerinden Python 3.13 FastAPI konteyneri; profil `kt-vibecoding-python-web-v2`.

   | Koşum | Komut / dosya | Gözlenen sonuç |
   | --- | --- | --- |
   | Başlangıç | [Üç başlangıç testi](backend-red.md) | Eksik modül/DI bağımlılığı nedeniyle 3 ayrı toplama hatası; başarılı sayılmadı |
   | Domain ilk yeşil | `pytest -q tests/unit/test_transcript_correction.py` | 24 başarılı |
   | Sağlayıcı ilk yeşil | `pytest -q tests/unit/test_ollama_correction.py` | 16 başarılı |
   | İlk birleşik PostgreSQL koşumu | `pytest -q tests/integration/test_transcript_correction.py tests/unit/test_transcript_correction.py tests/unit/test_ollama_correction.py` | 55 başarılı; yeni geçici veritabanı uygulandı ve düşürüldü |
   | Koruma genişletmesi | Aynı iki birim dosyası | 45 başarılı |
   | İkinci birleşik PostgreSQL koşumu | Aynı üç dosya | 64 başarılı; yeni geçici veritabanı uygulandı ve düşürüldü |
   | Sınırlı akış/iptal testleri | Aynı iki birim dosyası | 52 başarılı |
   | Son birleşik PostgreSQL koşumu | Aynı üç dosya, `RUN_POSTGRES_INTEGRATION=1` | 72 başarılı; 10,22 saniye; `DROP DATABASE` başarılı |
   | Son statik kontrol | `ruff check app tests`, `black --check app tests`, `isort --check-only app tests`, `mypy app` | Dördü başarılı; 137 Python dosyası biçimi, 85 uygulama dosyası tipi |
   | Son sabit liste düzeltmesi sonrası regresyon | Aynı iki birim dosyası | 52 başarılı; 1,85 saniye |

   Her PostgreSQL koşumu `voiceup_review_<benzersiz>_test` adlı yeni veritabanını oluşturdu; `scripts/db.sh apply` yalnız bu veritabanına yönlendirildi. Her koşum sonunda yalnız kendisinin oluşturduğu veritabanı düşürüldü. Yapılandırılmış uygulama veritabanına migration uygulanmadı. Statik kontrol, mevcut kalite kapısındaki yöntemle `/tmp/voiceup-review-static.*` altında kopyada yürütüldü; Windows bağlama noktası izinleri veya kaynak dosya kipleri değiştirilmedi.

3. Maddeler:

   **KUSUR**

   M1 İlk tür kontrolündeki beş hata düzeltildi: Unicode dönüşüm sözlüğü türü, repository dönüş türü, iki seçili satır listesi ve politika sabitinin `Literal` türü; son `mypy app` başarılı.

   M2 Ana kalite kapısının saptadığı iki `SIM905` hatası, aynı sözcüklerin açık sabit listeleriyle düzeltildi; son tam Ruff/biçim/tür kontrolü ve 52 birim regresyonu başarılı.

   **TUZAK**

   M3 Sayı sözcükleri, rakamlar, ay adları, büyük harfle başlayan adlar ve belirli Türkçe olumsuzluk ekleri korumalıdır; bu sezgiler küçük harfli bütün özel adları veya bütün anlamsal değişiklikleri çözmez.

   M4 Tarayıcı iptali paneli ve yanıt yaşam döngüsünü sonlandırır; sunucudaki hesaplamanın o anda durduğuna kanıt değildir. Hizmet toplam 100 saniyeyle sınırlıdır; Ollama isteği `keep_alive: 0` kullanır.

   **GÖZLEM**

   M5 Gerçek PostgreSQL/ASGI testlerinde normal roller, ikinci normal hesabın tenant izolasyonu, silinmiş/değişmiş kaynak, yetki iptali, kullanıcı/tenant kapanması ve model çağrısı sırasında açık DB işlemi bulunmaması gözlendi.

   M6 Öneri yalnız sunucunun değişmemiş metnine uygulanır; kaynak metin/zaman/konuşmacı/profil satırlarının öncesi-sonrası eşitliği, ses kaynağı süresi dolmuşken inceleme ve tekrarın yazma üretmemesi doğrulandı.

   M7 Sağlayıcı sınırında tam model digest kontrolü, çağrı öncesi/sonrası model değişimi, uzak model işaretleri, yönlendirme, bozuk/çift anahtarlı/sonlu olmayan JSON, araç çağrısı, eksik tamamlama, bildirimsiz taşan cevap ve duran akışın kapatılması test edildi.

   **AÇIK**

   M8 Buradaki model sınırı testleri denetimli HTTP taşıyıcısıyla çalışır; gerçek Qwen düzeltme isabeti, gerçek tarayıcı, nihai tam kapı ve güvenlik kanıtları bu rapordan çıkarılamaz; ana teslim raporunda ayrı gösterilir.

   **YAN-ETKİ**

   M9 Domain/port/servis/Ollama adaptörü, tenant bağlam sorguları, tipli yanıt/API ve üç test dosyası eklendi; schema/migration, ASR/kimlik worker'ı veya kalıcı kullanıcı metni değiştirilmedi.

   M10 Son kaynak SHA-256: domain `9d26d67172afe04821f88d4e5861b9c8e9bdd208ef173d7d418236f889099d1f`; Ollama adaptörü `7119d5011f206796a7a5a462b9fdd5d9ce3b2606ab87f0d99b0d1347b453e84a`; politika `tr-context-words-v1`, üretim bütçesi 512 token, bağlam 8.192 token, sıcaklık 0, seed 42.
