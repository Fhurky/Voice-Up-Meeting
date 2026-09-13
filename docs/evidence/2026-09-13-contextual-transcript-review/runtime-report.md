# Koşum raporu — 2026-09-13 · İsteğe bağlı yerel metin modeli bağlantısı ve dağıtım sınırları

1. Sonuç: Son doğrulama koşumlarında 162 test geçişi gözlendi (tekrarlar dahil); yerel model metadata bağlantısı canlı çalıştı — birim 162 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows PowerShell 5, yerel Python 3.12 test yürütücüsü, Docker Linux/Python 3.13 arka uç, kurulu nginx image ve Helm.

   | Komut / dosya | Gözlenen sonuç |
   |---|---|
   | `scripts/stack.sh exec -T backend python -m pytest tests/unit/test_text_review_config.py -q` | Önce 21 kırmızı, uygulama sonrası 21 başarılı. |
   | `pytest tests/test_text_review_runtime.py -q` ilk kırmızı | Yardımcı henüz yokken 10 kurulum hatası; ardından 10 başarılı. |
   | `pytest tests/test_text_review_chart.py -q` kırmızı | Helm PATH düzeltildikten sonra 1 başarılı, 7 kırmızı; uygulama sonrası 8 başarılı. |
   | `pytest tests/test_text_review_runtime.py tests/test_text_review_chart.py tests/test_text_review_proxy.py tests/test_text_review_startup.py tests/test_spark_startup.py tests/test_local_configuration.py -q` | 104 başarılı, 0 atlanan; mevcut başlatıcılar ve yeni sınırlar birlikte. |
   | `pytest tests/test_text_review_runtime.py -q` son tekrar | BOM koruma regresyonu eklendikten sonra 19 başarılı. |
   | `RUN_DOCKER_TRANSPORT=1 pytest tests/test_spark_transport_config.py -q -o addopts= --junitxml outputs/2026-09-13-contextual-transcript-review/runtime-spark-regression.xml` | 18 başarılı, 0 atlanan; 72,73 saniye; gerçek, geçici ve yalıtılmış Docker ağları. |
   | `python scripts/check-config-sync.py` | 43 tipli ayar, 40 Compose anahtarı, tek Secret sınırı; başarılı. |
   | `scripts/render-charts.sh` | Normal 46 kaynak × 2 fikstür; toplantı 47 kaynak × 2 fikstür; başarılı. |
   | `ruff check`, `ruff format --check` yeni yardımcı/test dosyaları; `black --check`, `isort --check-only` iki arka uç dosyası; `git diff --check` değişen kapsam | Başarılı; Windows satır sonu uyarıları çıktı, hata yok. |
   | `python scripts/setup-local-text-review.py --check`, ardından `--enable` | Kurulu `qwen3.5:27b` doğrulandı; yerel ayarlar sırlar yazdırılmadan etkinleştirildi. |
   | Arka uçtan `GET http://nginx:9081/api/tags` ve başlatıcı ile yeniden yükleme | Sabit model kimliği görüldü; etkin nginx yapılandırması doğrulandı ve yeniden yüklendi. |

3. Maddeler:

   **KUSUR**

   M1 Spark ile metin overlay'i aynı `security_opt` değerini birleştirerek Compose hatası üretti; aynı kontrolleri koruyan açık liste geçersiz kılma ile düzeltildi (`test_real_compose_preserves_closed_networks_and_optional_model_identity`).

   M2 Mevcut dotenv dosyasındaki UTF-8 BOM ilk ayarın tekrarlanmasına yol açabilirdi; BOM ve diğer satırlar korunarak düzeltildi (`test_configuration_preserves_bom_without_duplicate_selection`).

   **TUZAK**

   M3 İlk chart koşumunda Helm PATH üzerinde bulunamadı; kurulu `%USERPROFILE%\bin` eklendi. Yeni araç kurulmadı; sonraki gerçek Helm koşumları başarılı.

   M4 Compose fikstürü Windows uygulama veri yollarını gerektirir; dar çevre aktarımına bu platform yolları eklendi. Örnek sırlar dışında uygulama ayarı aktarılmadı.

   M5 Docker ortamındaki `VOICEUP_TEXT_REVIEW_*` değerleri varsayılan testini etkileyebilir; test kendi dört ayarını süreç çevresinden ayırır.

   **GÖZLEM**

   M6 Yerel ve Spark bileşiminde gerçek nginx yalnız izinli üç yol/yöntemi iletti; oluşturma/indirme/silme ve diğer yollar 404, yanlış yöntemler 405; Authorization/Cookie/Origin iletilmedi.

   M7 Yerel model SHA-256: `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`; canlı bağlantı kanıtı metadata erişimidir, metin doğruluğu kanıtı değildir.

   M8 Yerel, Spark, x86_64 CPU ve aarch64 CPU gerçek Compose modellerinde veri/iş servisleri yalnız iç ağda; 9081 yayımlanmıyor. Küme izni yalnız aynı namespace `voiceup/text-review` pod seçicisine TCP 11434.

   **AÇIK**

   M9 macOS/native Linux ve gerçek Kubernetes bağlantısı çalıştırılmadı; Compose/Helm yapısal doğrulaması cihaz veya dağıtım kanıtı değildir.

   M10 Modelin metin kalitesi, uygulama HTTP/tarayıcı akışı, tam kalite ve güvenlik kapısı ana teslim koşumuna aittir; bu rapor bunların geçtiğini iddia etmez.

   **YAN-ETKİ**

   M11 Git dışındaki `app/infra/.env` içinde dört `TEXT_REVIEW_*` ayarı ve `outputs/local-text-review-enabled.txt` etkin seçimi yazıldı; diğer yerel ayarlar korundu.

   M12 Yalnız nginx ve arka uç yeniden oluşturuldu/başlatıldı; Ollama bağlama adresi, güvenlik duvarı, modeller ve konuşmacı/ASR servisleri değiştirilmedi. Testlere ait geçici konteyner/ağlar kendi koşumlarında temizlendi.
