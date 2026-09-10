# Koşum raporu — 2026-09-09 · Güvenlik kapısı ortam kontrolü

1. Sonuç: Güvenlik kapısı gerekli çevrimdışı tarayıcı bulunamadığı için çalışamadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 1 ortam kapısı; karar bekleyen: yok.
2. Koşulan: Windows / Git Bash, `scripts/security-gate.sh`, çıkış 2; [ham çıktı](security-gate.txt), [komut ve süre](security-gate-result.json).
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 İlk kontrol `required offline security tool is unavailable: gitleaks` sonucunu verdi; Semgrep/Trivy taramaları da bu kapıda çalışmadı.

   **GÖZLEM** — yok

   **AÇIK**
   M2 Bu koşum güvenlik taraması başarısı veya tüm ürün kapılarının tamamlanması değildir; onaylı çevrimdışı tarayıcı ortamı eksiktir.

   **YAN-ETKİ**
   M3 Yalnız komut çıktısı ve bu kanıt raporu eklendi; bağımlılık veya tarayıcı kurulmadı.
