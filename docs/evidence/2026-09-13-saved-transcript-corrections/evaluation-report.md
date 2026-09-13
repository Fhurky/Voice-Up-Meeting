# Koşum raporu — 2026-09-13 · Ayrı görünür öneri deney yolu

1. Sonuç: Eski filtreli deney ve yeni görünür öneri yolu ayrı kimliklerle çalışıyor; son puanlama/sayaç regresyonları da geçti — birim 97 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows araştırma Python 3.12; `pytest tests/test_visible_correction_evaluation.py tests/test_experiment_ledger.py tests/test_transcript_review_evaluation.py tests/test_transcript_review_controller.py -q -o addopts=`.

   | Koşum | Sonuç |
   |---|---|
   | Yeni protokol desteği, controller eklenmeden önce | 69 başarılı, 1,48 saniye |
   | Seçili model ve görünür çıktı modu | 72 başarılı, 1,55 saniye |
   | İlk sıralama/günlük açıklaması sonrası | 72 başarılı, 1,78 saniye; Ruff lint ve format başarılı |
   | Kısmi yanıt puanlaması ve görünür durum sayaçları sonrası son koşum | [97 başarılı, 1,72 saniye; kırmızı/yeşil ve Ruff kanıtı](evaluation-review-report.md) |

3. Maddeler:

   **KUSUR**
   M1 Yeni protokol yalnız `tr-context-words-v2` ile kabul edildi; eski sonuç JSON şekli korunuyor.
   M2 Farklı model kimliği başarısız satır olarak ham metinle paydada kalıyor; eşlenemeyen ham model çıktısı yalnız özel kanıtta tutuluyor.

   **TUZAK**
   M3 Kayda uygun yanıttaki eşlenen düzenleme kullanıcı tarafından onaylanmış demek değildir; anlamsal işaretler gizlenmez. Eşlenemeyen/geçersiz yanıt ham metinle puanlanır; ayrı durum sayaçları korunur.

   **GÖZLEM**
   M4 Hatalı kelime ekleyen önerinin temiz metni bozma sayacı 1 oldu; başarı sonuçlarını seçmek için filtrelenmedi.

   **AÇIK**
   M5 Bu otomatik koşum temsilî toplantı doğruluğu veya tarayıcı kabulü iddia etmez; gerçek model ve HTTP kayıt akışı [model raporunda](model-report.md) ve [HTTP raporunda](live-http-report.md) ayrı kanıtlanır.

   **YAN-ETKİ**
   M6 Deney yürütücüsüne açık model seçimi eklendi; eski sonuç blokları ve mevcut kullanıcı verileri değiştirilmedi.
