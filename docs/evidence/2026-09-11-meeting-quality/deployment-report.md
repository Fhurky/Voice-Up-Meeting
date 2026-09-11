# Koşum raporu — 2026-09-11 · Worker kaynak ayarı ve fixture dağıtım sözleşmesi doğrulandı; gerçek Kubernetes ortamları hazır değil.

1. Sonuç: Üç dar doğrulama başarılı, iki gerçek ortam hazırlık denetimi eksik bilgiler nedeniyle başarısız — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows Git Bash ve sabit scaffold Python ortamı, `scripts/render-charts.sh` | 46 kaynak × 2 fixture overlay başarılı |
   | Aynı ortam, `scripts/render-charts.sh --self-test` | Olumsuz chart sözleşme kontrolleri ve 46 kaynak × 2 fixture overlay başarılı; araç ayrı birim test sayısı yayımlamaz |
   | Windows Python 3.13, `scripts/check-config-sync.py` | 77 kaynak dosyası, 39 typed ayar, 36 Compose anahtarı, 37 örnek ortam ataması ve 1 Kubernetes Secret referansı tutarlı |
   | `scripts/render-charts.sh --environment-ready lab` | Çıkış 1: kayıtlı ortamda zorunlu registry/host/storage/Kubernetes/source revision/Secret/image digest bilgileri hâlâ `__REQUIRED_*` |
   | `scripts/render-charts.sh --environment-ready cluster` | Çıkış 1: aynı gerçek ortam bilgileri hazırlanmadı |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Fixture render, gerçek Kubernetes ortam hazırlığı veya dağıtım değildir; başarısız `--environment-ready` sonuçları varsayılan fixture geçişinden ayrı tutulur.

   **GÖZLEM**

   M2 Worker chart isteği `256Mi`, sınırı `512Mi`; Decision 14 ve `docs/MEETING_WORKFLOW.md` aynı değerleri ve 223,54 MiB ölçümünün veritabanı checkpoint'ini içermediğini kaydeder.

   M3 Worker sağlık komutu, backend hazırlık HTTP yolu ve inference pilot hazırlık probe'u mevcut şablonlarda korunur; yeni iş kabulü ayrıca özel model/tarif doğrulamasına bağlıdır.

   **AÇIK**

   M4 Gerçek `lab` ve `cluster` ortamlarının deployment metadata değerleri sağlanmadı; yerel geliştirme çalışması bunların yerine geçmez.

   M5 Bu koşumda `app-inference` chart'ı yalnız pilot mount/probe'unu taşıyordu. Seçilebilir toplantı chart'ı sonraki [Decision 17 renderer koşumunda](meeting-chart-renderer-report.md) eklendi/doğrulandı; gerçek Kubernetes/Spark aktivasyonu ayrı kalır.

   **YAN-ETKİ**

   M6 Bu incelemede chart/ortam kaynakları değiştirilmedi; render yardımcıları kendi geçici çıktılarıyla çalıştı ve yalnız bu kanıt raporu eklendi.
