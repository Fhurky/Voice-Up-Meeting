# Koşum raporu — 2026-09-13 · Üç kurulu modelde aynı dört Türkçe düzeltme regresyonu

1. Sonuç: Üç modelin toplam 12 çağrısı yanıt verdi; 27B bir satırın toplam kelime hatasını azalttı fakat ayrıca zararlı bir kelime değişikliği üretti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows RTX 4060 Laptop 8 GB, 32 GB RAM, yerel Ollama 0.33.3; Docker arka ucunun gerçek seçili-model adaptörü ve özel nginx köprüsü. `scripts/evaluate-transcript-review.py run --visible-model <kurulu-model>` ile modeller sırayla çağrıldı; her model aynı dört önceden yazılmış Türkçe regresyonu gördü.

   | Model / toplu kanıt | Ulaşan yanıt | Ham → öneri kelime hata oranı (WER) | Yararlı / zararlı düzenleme | Durum: değişmedi / öneri / eşlenemedi / geçersiz | Kayda uygun satır | Medyan / en uzun süre |
   |---|---|---|---|---|---|---|
   | [qwen3.5:9b](qwen3.5-9b-aggregate.json) | 4/4 | 2/16 (%12,50) → 2/16 (%12,50) | 0 / 0 | 4 / 0 / 0 / 0 | 0 | 6,93 / 43,47 saniye |
   | [qwen3.6:12B](qwen3.6-12B-aggregate.json) | 4/4 | 2/16 (%12,50) → 2/16 (%12,50) | 0 / 0 | 0 / 0 / 4 / 0 | 0 | 11,45 / 22,69 saniye |
   | [qwen3.5:27b](qwen3.5-27b-aggregate.json) | 4/4 | 2/16 (%12,50) → 1/16 (%6,25) | 2 / 1 | 2 / 2 / 0 / 0 | 2 | 34,21 / 51,95 saniye |

   Model başına iki temiz ve iki hatalı kaynak satırı, 16 referans kelime vardır; toplam 12 çağrı dört benzersiz örneğin tekrar ölçümüdür. 27B'nin düzenleme isabeti 2/3 (%66,67); diğerlerinde uygulanabilir düzenleme olmadığı için isabet tanımsızdır. Her modelde temiz satırı bozma 0/2 gözlendi. Toplam süreler sırasıyla 64,09, 56,88 ve 151,05 saniyedir; bu küçük koşum kapasite veya eşzamanlılık ölçümü değildir.

   Mevcut üç toplu JSON, ilgili özel metadata dosyasıyla `scripts/record-experiment.py --input <toplu-json> --experiment-metadata <metadata> --kind transcript_review --evidence <toplu-json>` üzerinden deftere işlendi: üç yeni snapshot eklendi. Her deneyin son sürümü 3; eski dosya öneki byte düzeyinde korundu ve üç sayaç grubunun kaynakla eşitliği doğrulandı.

   Model, HTTP ve değerlendirme raporları için üç belge doğrulaması başarılı: yerel bağlantılar çözüldü; özel HTTP kaynağındaki token, kaynak/öneri metni ve kayıt/tenant/toplantı/satır kimlikleri raporlarda bulunmadı.

3. Maddeler:

   **KUSUR**

   M1 27B, gerekli düzeltmelerin yanında `rolden` → `rolde` değişikliğiyle fazladan kelime hatası oluşturdu; bu model hatası görünür bırakıldı. Aynı satırdaki yararlı değişiklik hatayı dengelediği için satır bazında kötüleşme 0 iken zararlı düzenleme 1'dir.

   M2 12B'nin dört yanıtındaki öneriler kaynak metne eşlenemedi; ham cevaplar özel kanıtta korundu ve dört satır özgün metinle puanlandı. Yanıt alınması doğru veya kaydedilebilir düzeltme anlamına gelmedi.

   **TUZAK**

   M3 Bu küme önceden yazılmış dört regresyondur; kör test, yeni ses tanıma deneyi veya gerçek Türkçe toplantıları temsil eden doğruluk ölçümü değildir. 012'nin filtreli politikasıyla aynı deney veya kullanıcı tarafından onaylanmış sonuç sayılmaz.

   M4 Kayda uygun satır sayısı kullanıcı onayı/kaydı değildir. Sıfır temiz metin bozma yalnız iki temiz örnekte gözlendi; geniş bir hata oranı güvencesi sağlamaz.

   **GÖZLEM**

   M5 Politika `tr-context-words-v2`, veri SHA-256 `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` ve üç üretim kaynak dosyasının birleşik SHA-256 değeri `d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af` bütün modellerde aynıydı; tam model digest'leri bağlı toplu kanıtlarda kayıtlıdır.

   M6 Eşlenemeyen/geçersiz kısmi çıktıyı ham metinle puanlama düzeltmesi sonrasında mevcut özel satırlar yeniden hesaplandı; bu dört örneğin model skorları değişmedi. Yeni model çağrısı yapılmadı; [97 testlik puanlama/sayaç kanıtı](evaluation-review-report.md) ayrı kayıtlıdır.

   **AÇIK**

   M7 Temsilî, insan doğrulanmış ve kör ayrılmış Türkçe toplantı kümesinde fayda/zarar oranı bu koşumda ölçülmedi; konuşmacı kimliği, ses çözümleme başarısı ve 50 kişi performansı hakkında yeni iddia yoktur.

   **YAN-ETKİ**

   M8 Üç kamu toplu kanıtı mevcut özel satırlara bağlandı ve `results.md` yeni sürümlerle güncellendi; eski deneyler değiştirilmedi. Model kurulmadı veya tekrar çağrılmadı; ham cevap, referans ve özel satırlar Git dışı `outputs/` altında kaldı.
