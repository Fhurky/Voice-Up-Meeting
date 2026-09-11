# Koşum raporu — 2026-09-11 · Doğruluk değişikliklerinin güvenlik kapısı giriş denetimi

1. Sonuç: Gerekli çevrimdışı araç bulunamadığından güvenlik taraması çalışmadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: Yerel Windows, `C:/Program Files/Git/bin/bash.exe scripts/security-gate.sh`; Python `subprocess.run` ile doğrulanan gerçek çıkış kodu 2, çıktı `required offline security tool is unavailable: gitleaks`.
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 PowerShell ilk çağrıyı dış süreç kodu 1 olarak sundu; bağımsız alt süreç kaydı kapının gerçek kodunun 2 olduğunu doğruladı.
   **GÖZLEM**
   M2 Bağımlılık ve model sürümü değiştirilmedi; mevcut kabul edilmiş çevrimdışı kurulum kullanılıyor.
   **AÇIK**
   M3 Gitleaks eksik olduğundan sonraki Semgrep/Trivy ve kabul edilmiş çevrimdışı tarama malzemesi denetimlerine ulaşılmadı; güvenlik geçişi iddiası yoktur.
   **YAN-ETKİ** — yok
