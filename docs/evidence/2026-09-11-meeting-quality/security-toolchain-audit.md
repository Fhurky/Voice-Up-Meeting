# Koşum raporu — 2026-09-11 · Güvenlik kapısı için mevcut çevrimdışı araçlar ve kabul kanıtı denetlendi.

1. Sonuç: Güvenlik taraması çalıştırılamadı; kapı eksik Gitleaks komutunda çıkış 2 ile durdu — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 3 güvenlik tarayıcısı; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut/kaynak | Gözlenen sonuç |
   |---|---|
   | Windows Git Bash, `scripts/security-gate.sh`; profil `kt-vibecoding-python-web-v2` | `required offline security tool is unavailable: gitleaks`; gerçek çıkış kodu 2 |
   | PowerShell `Get-Command` ve Git Bash `command -v` | Gitleaks, Semgrep ve Trivy için çalıştırılabilir komut bulunmadı |
   | Altı zorunlu scanner ortam girdisi için yalnız varlık denetimi | `INTERNAL_SCANNER_MATERIAL_DIR`, `INTERNAL_SCANNER_SHA256SUMS`, `INTERNAL_SCANNER_SHA256SUMS_SHA256`, `INTERNAL_SCANNER_ADMITTED_ON`, `INTERNAL_SEMGREP_RULESET`, `TRIVY_CACHE_DIR` tanımlı değil; değer veya `.env` içeriği okunmadı/yazdırılmadı |
   | Depo `scripts/`, `tools/boilerplate/packaging/`, yok sayılan `tools/` ve `outputs/`, bilinen kullanıcı önbellekleri | Scanner hazırlayıcısı, kapalı scanner paketi veya dışarıdan kabul kaydı bulunmadı; `outputs/local-tools/` yalnız Helm içeriyor |
   | `docker image inspect`, yerel imaj metadata okuması | Gitleaks 8.18.4, Semgrep 1.86.0, Trivy 0.55.0 mevcut; aşağıdaki içerik kimlikleri gözlendi, imajlar başlatılmadı |

   | Yerel önbellek imajı | Gözlenen imaj/RepoDigest SHA-256 |
   |---|---|
   | `zricethezav/gitleaks:v8.18.4` | `75bdb2b2f4db213cde0b8295f13a88d6b333091bbfbf3012a4e083d00d31caba` |
   | `semgrep/semgrep:1.86.0` | `a9ea2d5621c29d815d90c2a3b2f9571da8972ef4ff855c9e4902681730240e35` |
   | `aquasec/trivy:0.55.0` | `35e972d4c97895711cb2de6594cc1774b61e6b9dc7661ef73a76dd649f006c8d` |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 PATH'e bir komut eklemek tek başına kapıyı açmaz: [security-gate.sh](../../../scripts/security-gate.sh) kapalı, symlink içermeyen dosya envanteri, dışarıdan kabul edilmiş manifest özeti ve en fazla 7 günlük kabul tarihi ister.

   M2 Yerel imaj kimliği, resmi yayıncı dosya özeti veya yeni hesaplanmış `SHA256SUMS`, ayrı kabul kararının yerine geçmez; mevcut imajlar bu depo için kabul edilmiş scanner paketi olarak değerlendirilmedi.

   **GÖZLEM**

   M3 [Paketleme prosedürü](../../../tools/boilerplate/packaging/README.md) scanner ikilileri/veritabanlarını ayrı kabul edilmiş güvenlik paketi olarak tanımlar ve bunları paket betiğinin indirmediğini açıkça belirtir; mevcut prosedürle yeni scanner indirimi hazırlanmadı.

   M4 [Güvenlik iş akışı](../../../.github/workflows/security-scan.yml) araç ve kabul girdilerini hazır bir çevrimdışı çalıştırıcıdan bekler; [önceki başarısız koşum](second-gate-report.md) aynı eksik araç sonucunu korur.

   **AÇIK**

   M5 Tam kapı için çalıştırılabilir üç scanner, kapalı Semgrep kural dosyası/Trivy önbelleği, bunların `SHA256SUMS` envanteri ve ayrı kanaldan verilmiş manifest SHA-256 ile kabul tarihi eksik; kapının altı ortam girdisi bu gerçek pakete bağlanmalı.

   M6 Gitleaks, Semgrep ve Trivy taramaları çalışmadı; secret, kaynak güvenliği, bağımlılık açığı veya altyapı taraması için başarılı sonuç çıkarılamaz. Depo/kullanıcı önbelleği araması tüm bilgisayar disklerinin eksiksiz envanteri değildir.

   **YAN-ETKİ**

   M7 Yalnız bu rapor eklendi; güvenlik kapısı, pinler, kabul defteri, araç önbelleği, ortam ayarları, GPU ve çalışan servisler değiştirilmedi. Hiçbir tarayıcı indirimi, yeni paket kabulü veya kontrol atlatması yapılmadı.
