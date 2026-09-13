# Koşum raporu — 2026-09-13 · Kurulu model seçimi, görünür ham öneri ve iki önizleme yolunun süre sınırı

1. Sonuç: Yeni adaptör/port sınırları ve önceki politika regresyonları geçti; iki model inceleme yolu yavaş HTTP yanıtını korudu — birim 81 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Docker Python 3.13 arka uç, Windows Python 3.12 test yürütücüsü, gerçek nginx ve Helm.

   | Komut / kapsam | Gözlenen sonuç |
   |---|---|
   | `scripts/stack.sh exec -T backend python -m pytest tests/unit/test_ollama_selected_models.py -q` kırmızı | Eksik liste/seçim davranışı için 30 başarısız. |
   | `scripts/stack.sh exec -T backend python -m pytest tests/unit/test_ollama_selected_models.py tests/unit/test_ollama_correction.py -q` | Önce 53 başarılı; ek sınır testleri sonrasında 65 başarılı: 42 yeni, 23 eski davranış. Son koşum 2,01 saniye. |
   | `pytest tests/test_text_review_public_timeout.py -q -o addopts= --junitxml outputs/2026-09-13-saved-transcript-corrections/adapter-timeout-red.xml` | Yeni suggestion yolu 60,2 saniyede HTTP 504; 1 başarısız, 66,99 saniye. |
   | Aynı test, `adapter-timeout-green.xml` | 1 başarılı, 66,76 saniye; preview/suggestion × yerel/Spark yolları 65 saniyelik HTTP 200'ü iletti. Sıradan API yolları 60 saniyede HTTP 504. |
   | `pytest tests/test_text_review_proxy.py tests/test_text_review_chart.py tests/test_text_review_startup.py -q -o addopts= --junitxml outputs/2026-09-13-saved-transcript-corrections/adapter-runtime-regression.xml` | 15 başarılı, 0 atlanan; 6,45 saniye. |
   | Adaptör/port/yeni test dosyasında Ruff, Black, isort; iki kaynak dosyasında mypy | Başarılı; mypy iki kaynak dosyasında hata bulmadı. |
   | `scripts/stack.sh exec -T nginx sh -s` ile etkin yapılandırmada `nginx -t` ve `nginx -s reload` | 17:54:52 UTC: sözdizimi doğrulandı ve graceful reload sinyali başarılı; model veya arka uç yeniden başlatılmadı. |

3. Maddeler:

   **KUSUR**

   M1 Yeni `correction-suggestion` yolu varsayılan 60 saniyede kesiliyordu; yerel nginx'in 110 saniyelik açık yol deseni iki uç noktasını kapsayacak şekilde düzeltildi (`test_text_review_public_timeout.py`).

   **TUZAK**

   M2 Varsayılan model adı aynı kalıp digest değişirse katalog `default_changed` döndürür ve kullanımı kapatır; başka modele sessiz geçiş veya ortak Settings değişikliği yoktur.

   M3 Model gövdesindeki bozuk JSON artık ham metin olarak gösterilebilir; geçersiz HTTP/JSON zarfı, yanlış model/rol, araç çağrısı veya tamamlanmamış istek hâlâ güvenli hata üretir.

   M4 8.192 kod noktasından uzun metin veya `done_reason:length` açık kesilme işareti taşır; kaydedilebilirlik adaptörün değil sonraki domain/hizmet katmanının sorumluluğudur.

   **GÖZLEM**

   M5 Liste en çok 100 kayıt, 10 saniye toplam sınır ve en çok dört paralel metadata çağrısı kullanır; seçilmiş model çağrıdan önce/sonra `/tags` ve `/show` ile doğrulanır.

   M6 Yeni adapter yalnız sınırlı metin/dil bağlamını ve açık seçilen model adını gönderir; katalog template, model_info, dosya yolu veya sağlayıcının gelişigüzel hata metnini döndürmez.

   M7 Eski `review(context)` sözleşmesi, prompt, JSON şema ve üretim ayarları korundu; 23 eski test geçti. Yeni sözleşme ayrı `TranscriptSuggestionPort` üzerinden çalışır.

   M8 Dondurulan adaptör SHA-256 `dec65bce43ee71307cb96a4081909ee89ff1c8a15ec018bd74824b02fe77e61f`; prompt SHA-256 `b25a3da235e46271b257a15c53b7493e8bf04dcc04831b4a89023dc46bdddc87`; port SHA-256 `bc0957ee271584433d013b5334900da5f23559e727a440581b6ab70473a45f32`.

   M9 Ana model deneyi tamamlandıktan sonra canlı yerel nginx 17:54:52 UTC'de graceful reload aldı; iki correction yolu için 110 saniye etkinleşti, özel 9081 köprüsü korundu.

   **AÇIK**

   M10 Bu alt koşum gerçek dil modeli üretimi, yetkili uygulama API'si, kayıt/sürüm/retention veya tarayıcı başarısı iddia etmez; bunlar ana 013 tesliminin ayrı koşumlarıdır.

   **YAN-ETKİ**

   M11 Adaptör/port, ilgili testler ve yerel nginx yol deseni değişti; yeni bağımlılık, ayar, Secret, chart veya model kurulumu yapılmadı. Testlere ait geçici konteynerler temizlendi.
