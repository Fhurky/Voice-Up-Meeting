# Koşum raporu — 2026-09-11 · Gerçek tarayıcıda yüklenen dört toplantı kaydı ve kalıcı kişi hafızası

1. Sonuç: Gerçek model, PostgreSQL ve normal kullanıcıyla kayıtlı aktarım ve hafıza senaryoları geçti — birim 0 başarılı / tarayıcı 2 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows Node 22.23.2, Playwright 1.62.1, Chromium Headless Shell rev1234; 8081 ortak SPA/API kökü ve RTX 4060 Laptop GPU. `node e2e/speaker-identity/05-meeting-memory.mjs` ve `04-meeting-upload.mjs`; özel kimlik bilgileri ortamdan aktarıldı, gerçek giriş formu kullanıldı. İkisinde de çıkış 0; ham sonuçlar `outputs/2026-09-10-meeting-delivery/{04-meeting-upload,05-meeting-memory}-browser.txt`.
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Genel `scripts/e2e.sh` için kabul edilmiş platform eşleşen offline bundle yoktur; bu koşum önceki [tarayıcı araç hazırlığındaki](frontend-report.md) sabit, doğrulanmış yerel araçları kullandı ve resmi bundle kapısı sayılmaz.
   M2 Bu senaryo kişi sayılarını A/B/D/C için 5/5/6/6 olarak gerçek formdan girdi; ipucusuz ses ayrımı ayrı [API koşumunda](frozen-meeting-flow-report.md) doğrulandı.
   **GÖZLEM**
   M3 Boş test hafızasında A beş profil oluşturdu; adlar arayüzden verildi, sayfa yenilenince korundu. Türkçe ve İngilizce sonuç görünümü gözlendi.
   M4 Ayrı B kaydı aynı beş profil/adı tanıdı; D altıncı kişiyi hafızaya eklemeden `profile_pending` gösterdi; C yalnız bir yeni profil ekleyerek toplamı altıya çıkardı.
   M5 Zamanlı, kişiye bağlı ve boş olmayan metin gerçek sonuç ekranında görüldü; C tekrar isteği aynı toplantıyı ve altı profili korudu. Aktarım senaryosu iki dilde normal writer/reader izinleri, hashli devam, yanlış kaynak, iptal/temizleme ve 403/404 sınırlarını yeniden geçti; tarayıcı hatası ve dış ağ isteği olmadı.
   **AÇIK**
   M6 Kaynaklar İngilizce kontrollü kayıtlardır; Türkçe çok konuşmacılı doğal toplantı, 50 kişi, genel kelime/kimlik doğruluğu ve sahip kabulü bu tarayıcı senaryosuyla ölçülmedi.
   **YAN-ETKİ**
   M7 Hafıza senaryosu yalnız boş test tenantında kendi dört toplantısını ve altı profilini oluşturdu; iki senaryo `finally` içinde kendi kayıtlarını public API ile temizledi. Kimlik bilgileri, kaynak ses ve ham metin Git'e alınmadı.
