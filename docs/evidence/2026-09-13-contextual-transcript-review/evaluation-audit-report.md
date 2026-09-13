# Koşum raporu — 2026-09-13 · Metin inceleme deney kanıtının doğrulama sınırları

1. Sonuç: Hesaplama ve denetleyici regresyonları düzeltildi — birim 64 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows Python 3.12 araştırma ortamı; profil uygulama sınırı `kt-vibecoding-python-web-v2`, üretim Python/FastAPI katmanı ve modeli bu koşumda çalıştırılmadı.

   | Komut / geçiş | Gözlenen sonuç |
   |---|---|
   | `.venv/Scripts/python.exe -m pytest tests/test_transcript_review_evaluation.py tests/test_transcript_review_controller.py` | Kırmızı: 6 başarılı / 12 başarısız; [rapor](evaluation-audit-red.md) |
   | Aynı iki dosya ve `tests/test_experiment_ledger.py` | İlk yeşil: 62 başarılı |
   | Aynı üç dosya, yol geçişi regresyonu sonrası | 63 başarılı |
   | Aynı üç dosya, toplam öneri bütçesi kontrolü sonrası | Son koşum: 64 başarılı; çıkış 0 |
   | `ruff check scripts/evaluate-transcript-review.py scripts/transcript_review_evaluation.py tests/test_transcript_review_controller.py tests/test_transcript_review_evaluation.py` | Başarılı; çıkış 0 |
   | Aynı dört dosyada `ruff format --check` | 4 dosya uygun; çıkış 0 |

3. Maddeler:

   **KUSUR**
   M1 Çift örnek sayısında medyan düzeltildi; iki orta sürenin ortalaması alınır (`test_even_latency_uses_the_two_middle_observations`).
   M2 Unicode kod noktalarıyla değişikliklerden öneri tam kurulur; örtüşme, bilinmeyen edit alanı, açıklanamayan metin ve üç öneri bütçesi aşımı reddedilir (`test_transcript_review_evaluation.py`).
   M3 Özel dosyalar yalnız kanonik repo `outputs/` altında yazılır; `..` kaçışı ve public çıktı reddi model çağrısından önce sınanır (`test_transcript_review_controller.py`).
   M4 Input ve metadata tek okumada dondurulur; manifest hash'i metadata ile bağlanır, kayıt sabit metadata'dan yazılır, worker kaynak/model/politika kimliği tekrar denetlenir (`test_transcript_review_controller.py`).

   **TUZAK**
   M5 Önceki çift sayılı deneylerin medyanı bu düzeltmeden etkilenir; eski günlük blokları yerinde değiştirilemez, gerçek satırlardan yeniden hesaplanan aggregate ayrı sürüm olmalıdır.
   M6 Başarısız worker yanıtı ham metin, sıfır kabul edilen öneri ve ölçülen süreyle paydada kalır; başarılı model çağrısı gibi sayılmaz.

   **GÖZLEM**
   M7 Public toplama özel metin taşınmaz; bilinmeyen manifest/worker alanları reddedilir. Punctuation-only örnek gerçek bir edit çifti taşır ve lexical iyileşme sayılmaz.
   M8 Subprocess çağrısı `bash`/mevcut stack wrapper üzerinden argüman listesi, UTF-8 ve 115 saniye sınırıyla test edildi; yeni model veya uygulama çağrısı yapılmadı.

   **AÇIK**
   M9 Bu testler gerçek Apple/Spark host çalışması, zorla süreç kesilmesinden devam veya gerçek model kalitesi kanıtı değildir.
   M10 İki üretim kaynak dosyasının mevcut pin formülü korundu; deney denetleyicisi, metrik hesaplayıcı ve normalizasyon kodu hashleri final kanıtında ayrıca bulunmalıdır.

   **YAN-ETKİ**
   M11 İki deney scripti ve iki test dosyası değişti. Testler yalnız geçici dosyalarda çalıştı; çalışan model işleri, mevcut özel sonuçlar ve `results.md` değiştirilmedi.
