# Koşum raporu — 2026-09-10 · Yerel yönetici düğmesiyle giriş ve yayın hazırlığı

1. Sonuç: Tam kalite ve canlı giriş kontrolleri geçti — birim/entegrasyon 212
   başarılı / tarayıcı 2 başarılı / atlanan 0; ayrı ortam eksikleri aşağıdadır;
   karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows/Docker Linux, Python 3.13,
   PostgreSQL 17, React/Vite ve Brave üzerinden `http://localhost:8081`.

   | Kontrol | Gözlenen sonuç ve kanıt |
   | --- | --- |
   | `scripts/quality-gate.sh all` | Çıkış 0; [153 backend](quality-gate-backend.xml) ve [59 frontend](quality-gate-frontend.json); config, format/lint/tip, migration, OpenAPI/tip drift, governance ve chart geçti. [Son çıktı](quality-gate-final.txt). |
   | Backend red/green ve gerçek PostgreSQL | 33 yeni birim sınırı ve 16 PostgreSQL vakası tam kapıya dahil; [backend raporu](backend-report.md). |
   | Frontend red/green | 21 odaklı test; tüm frontend toplamına dahil. [Rapor](frontend-report.md). |
   | Yerel HTTP | Nginx üzerinden [12/12 geçti](live-http-final.json): iki origin, JWT ve `/me`, tenant zorunluluğu, yabancı Host/Origin ve cross-site retleri. |
   | Gerçek tarayıcı | [2 akış geçti](browser-live.json): TR/EN düğme, korunan ana sayfa, yenileme, çıkış; konsolda hata/uyarı yok. Token enjekte edilmedi. |
   | Compose/config | [15 başarılı, 1 ortam hatası](infra-run-report.md); sekiz yeni NVIDIA/Spark/CPU yapılandırma vakası geçti. Eski PowerShell 7 testi çalıştırıcı eksikliği nedeniyle çalışmadı. |
   | Yerel verinin korunması | [Önce](local-state-before.json)/[sonra](local-state-after.json): 11 kullanıcı, roller, üyelikler, tenant kayıtlarının hashleri ve 245 profil sayısı değişmedi; çalışma modu Spark kaldı. |
   | `scripts/security-gate.sh` | Çıkış 2: `required offline security tool is unavailable: gitleaks`; [çıktı](security-gate.txt). |
   | Yayın kapsamı | [33 kaynak/config/sözleşme/test hash bağı](source-manifest.json); Git'in LF biçimi esas alındı. Kaynak ve biçimli belge kontrolü geçti; ham test çıktılarının satır sonu boşlukları korunur. Bağımsız dar sır incelemesinde gerçek kimlik bilgisi bulunmadı. |
   | GitHub yayını | Özellik commit'i `aa11e17f461d135b6e368e54a54111c74bdde9ae` gönderildi; [uzak `main` eşitliği ve temiz çalışma ağacı doğrulandı](publication.json). |

3. Maddeler:

   **KUSUR**

   M1 İlk tam kapıda varsayılan kullanıcı adı testi yerel Compose seçicisini aldı;
   test ortamı yalıtıldı, son kapıda 153/153 geçti. [İlk koşum](quality-gate-first-backend.xml).

   **TUZAK**

   M2 Windows dosya bildirimi Vite'ın eski ekranını geçersiz kılmadı; yalnız frontend
   yeniden başlatılınca yeni düğme yüklendi. Ürün kaynaklarına ek çözüm eklenmedi.

   M3 İlk HTTP kontrolünün başlık sözlüğü büyük/küçük harfe duyarlıydı; standart
   harf duyarsız karşılaştırmayla düzeltildi. [İlk kayıt](live-http.json), son sonuç 12/12.

   M4 Mevcut dil davranışı yenilemede Türkçeye döner; yönetici oturumu korunur.
   Tek tıkla giriş yalnız açık yerel development ayarında çalışır.

   **GÖZLEM**

   M5 Normal parola girişi ve JWT/RBAC/tenant denetimleri korunur; giriş hesap,
   parola veya profil yazmaz. Yerel seçim mevcut `voiceup-admin` hesabına bağlandı.

   M6 Tam kapı kendine özel `_test` veritabanını oluşturdu, migration uyguladı
   ve kaldırdı; uygulama veritabanına test migration'ı uygulanmadı.

   **AÇIK**

   M7 Gitleaks ve PowerShell 7 bulunamadı; güvenlik taraması ve eski bir başlangıç
   testi tamamlanmadı. Bu sonuçlar başarılı sayılmadı.

   M8 Fiziksel MacBook ve bağımsız Playwright çalıştırıcısı kullanılmadı; kalıcı
   senaryo mevcut, canlı kanıt CUA ile iki akışa aittir. Tam ortam kabulü iddia edilmez.

   **YAN-ETKİ**

   M9 Auth API/config, arayüz/TR/EN, testler, sözleşmeler, Compose ve rehberler
   güncellendi; yeni şema, model veya bağımlılık eklenmedi.

   M10 Git dışındaki yerel ayara yalnız yönetici seçicisi eklendi; backend yeniden
   oluşturuldu, frontend yeniden başlatıldı ve Nginx yapılandırması yeniden yüklendi.
   Spark model servisi ve başka Docker projeleri değiştirilmedi.

   M11 Özellik ve kanıtları GitHub'a gönderildi; bu yayın kaydı doğrulanmış özellik
   commit'ini izleyen belge güncellemesidir. Kimlik bilgileri Git'e yazılmadı.
