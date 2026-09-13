# Koşum raporu — 2026-09-13 · Son kaynakla tam profil kapısı

1. Sonuç: Son kodla 967 otomatik test ve tam kalite kapısı geçti; güvenlik taraması eksik araçta durdu — birim 692 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows PowerShell/Git Bash ve mevcut Docker Linux ortamı; profil `kt-vibecoding-python-web-v2`.

   | Komut / adım | Gözlenen |
   |---|---|
   | `scripts/quality-gate.sh all` | Çıkış 0; 780 backend testi, 195,90 saniye |
   | Backend dağılımı | 505 birim ve 275 gerçek PostgreSQL entegrasyonu |
   | Aynı kapı, frontend | 187 birim, lint, üretim build ve tip kontrolü başarılı |
   | Aynı kapı, sözleşmeler | OpenAPI ve üretilmiş frontend tipleri güncel |
   | Aynı kapı, altyapı | Ayar senkronizasyonu, benzersiz `_test` veritabanında migration/şema/drift, 93 yönetişim dosyası ve 4 etkin olmayan projeksiyon geçti |
   | Aynı kapı, Helm | 46 normal ve 47 toplantı kaynağı, ikişer overlay ile render edildi |
   | `scripts/security-gate.sh` tekrar | Çıkış 2: `required offline security tool is unavailable: gitleaks` |
   | Son `git diff --check` | Çıkış 0; yalnız mevcut Windows CRLF bildirimleri |
   | `scripts/setup-local-text-review.py --check` | Çıkış 0; özellik açık, `qwen3.5:27b` digest doğrulandı, yeniden başlatma gerekmiyor |
   | Kanıt/gereksinim bağlantıları ve işlevsel rapor karmaları | Eksik yerel bağlantı yok; üç bağlı raporun SHA-256 değeri eşleşti |

   Birim 692 = 505 backend + 187 frontend; 275 PostgreSQL testi eklendiğinde
   toplam 967'dir. Dar ve önceki koşumların testleri bu toplama tekrar eklenmez.
   Kaynak kayıtlar Git dışındaki `quality-gate-handoff.log` ve
   `security-gate-handoff.log`; [önceki kapı kaydı](quality-report.md) korunur.

3. Maddeler:

   **KUSUR**
   M1 Canlı akışta bulunan proxy ve StrictMode kusurları düzeltildikten sonra kapı tekrarlandı; iki yeni frontend regresyonu dahil 187 arayüz testi başarılı.

   **TUZAK**
   M2 Güvenlik kapısının başlatılması taramanın tamamlandığı anlamına gelmez; eksik araç sonuçları başarılı veya pytest atlaması olarak sayılmaz.

   **GÖZLEM**
   M3 Tam kapı yalnız kendisinin oluşturduğu `_test` veritabanına migration uyguladı ve sonunda düşürdü; uygulama veritabanına dokunmadı.

   **AÇIK**
   M4 `gitleaks` yok; kapı Semgrep/Trivy ve kabul edilmiş çevrimdışı tarama materyaline ulaşmadı. Tam güvenlik kabulü ve bütün gerekliliklerin tamamlandığına dair koşulsuz L1/L2 iddiası yok.
   M5 İşlevsel gerçek HTTP/tarayıcı gözlemleri ayrı raporlarda; Spark/Apple, canlı Kubernetes, eşzamanlı ağır ses işi ve L3 kullanıcı kabulü ölçülmedi.

   **YAN-ETKİ**
   M6 Bir geçici test veritabanı oluşturulup düşürüldü ve frontend build çıktısı üretildi. Paket, image veya sürüm kabulü değiştirilmedi.
