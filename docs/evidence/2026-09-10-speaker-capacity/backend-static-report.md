# Koşum raporu — 2026-09-10 · Backend biçim, tip ve üretilen sözleşme kontrolleri.

1. Sonuç: Altı statik ve sözleşme kontrolü geçti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Docker/Git Bash, `kt-vibecoding-python-web-v2`; mevcut kalite kapısının `backend_static`, `openapi_contract`, `frontend_types_contract` işlevleri. Ruff, Black, isort, mypy, OpenAPI farkı ve frontend tip farkı başarılı; Black 67 dosya, mypy 54 kaynak dosyası denetledi. [Ham çıktı](backend-static.txt), [komut kaydı](backend-provenance.json).
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Windows bağlama izinleri için kapının mevcut geçici kopya yöntemi kullanıldı; gerçek dosya izinleri değiştirilmedi. PowerShell'in stderr sarmalaması araç başarısızlığı değildir; süreç çıkış kodu 0'dır.
   **GÖZLEM**
   M2 `max_profiles` zorunlu pozitif tamsayı olarak kaynaktan üretildi; kontrol yeniden üretimin aynı sözleşmeyi verdiğini doğruladı.
   **AÇIK** — yok
   **YAN-ETKİ**
   M3 `scripts/export-openapi.sh` ve `scripts/generate-types.sh`, ilgili iki kayıtlı sözleşmeyi yeniden üretti; Black iki değişen Python dosyasını biçimlendirdi. Şema, migrasyon, ayar ve bağımlılık eklenmedi.
