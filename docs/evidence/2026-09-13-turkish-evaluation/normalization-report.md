# Koşum raporu — 2026-09-13 · Sürümlü Türkçe metin normalizasyonu ve skor komutu

1. Sonuç: Türkçe normalizasyonu ve gerçek dosya üzerinden deney günlüğü bağlantısı geçti — birim 53 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2` deposu, Windows yerel araştırma Python 3.12; ürünün Python 3.13 tam profil kapısı ayrı yürütülür.

   | Komut / aşama | Gözlenen sonuç |
   | --- | --- |
   | `.venv/Scripts/python.exe -m pytest tests/test_meeting_metrics.py tests/test_score_meeting_transcript.py -q` — normalizasyon kırmızı | 35 başarılı, 15 başarısız; eksik normalizasyon parametresi ve CLI seçeneği |
   | Aynı komut — normalizasyon yeşil | 50 başarılı, 0 başarısız |
   | Aynı iki dosya, `--tb=short` — günlük bağlantısı kırmızı | 51 başarılı, 2 başarısız; eksik metadata/günlük CLI bağlantısı |
   | Aynı iki dosya, `--tb=short` — günlük bağlantısı yeşil | 53 başarılı, 0 başarısız |
   | `ruff check` / `ruff format --check` — dört etkilenen Python dosyası | Lint geçti; ilk biçim kontrolü iki test dosyasını reddetti, düzenleme sonrası dört dosya geçti |

3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: Genel Unicode harf eşlemesi Türkçe `I/İ` ayrımı için uygun değildi; açık `turkish-words-v1` seçeneği birleşik/ayrık Unicode ve farklı Türkçe sözcük regresyonlarıyla eklendi.
   **TUZAK**
   M2 `unicode-words-v1` varsayılanı ve eski JSON alanları korundu; farklı normalizasyonlu skorlar aynı ölçüm sürümü gibi karşılaştırılamaz. Sayı yazımı ve iç apostrof ayrımları silinmez.
   **GÖZLEM**
   M3 Bu değişiklik ölçümün harf eşlemesini düzeltir; akustik model, kimlik eşikleri, model ağırlığı veya gerçek Türkçe ses doğruluğu bu dar koşumda değiştirilmedi/ölçülmedi.
   **AÇIK**
   M4 Tam profil kapısı kök görevde ayrı yürütülür; bu dar koşum gerçek model veya Türkçe toplantı kabulü değildir.
   **YAN-ETKİ**
   M5 İki skor dosyası ve iki test dosyası değiştirildi; paylaşılan `scripts/experiment_ledger.py` gerçek dosya testlerinde çağrıldı. Test girdileri sistemin geçici dizininde üretildi; ses, kişi, kimlik veritabanı veya token değiştirilmedi.
